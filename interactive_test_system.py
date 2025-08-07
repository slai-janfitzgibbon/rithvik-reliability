#!/usr/bin/env python3

import os
import sys
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from drivers import MultiInstrumentManager
from utils.recorder import UniversalRecorder
from data_manager import DataManager, DataSavingPreferences

class InteractiveTestSystem:
    def __init__(self):
        self.manager = MultiInstrumentManager()
        self.recorder = None
        self.instruments = {}
        self.current_session = {}
        self.test_history = []
        self.data_manager = DataManager()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s: %(message)s'
        )
        
        # Load previous session data and preferences
        self.load_session_data()
        self.data_manager.load_preferences()
    
    def load_session_data(self):
        """Load previous session data"""
        session_file = './session_data.json'
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                    self.test_history = data.get('test_history', [])
                    print(f"Loaded {len(self.test_history)} previous test records")
            except Exception as e:
                print(f"Could not load session data: {e}")
    
    def save_session_data(self):
        """Save current session data"""
        session_file = './session_data.json'
        try:
            data = {
                'test_history': self.test_history,
                'last_session': self.current_session
            }
            with open(session_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Could not save session data: {e}")
    
    def print_welcome(self):
        """Print welcome message and system status"""
        print("\n" + "="*80)
        print("              PRODUCTION FAU TEST SYSTEM")
        print("="*80)
        print("Welcome to the automated FAU testing system!")
        print(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.test_history:
            print(f"Previous tests in database: {len(self.test_history)}")
            last_test = max(self.test_history, key=lambda x: x['timestamp'])
            print(f"Last test: {last_test['device_id']} on {last_test['timestamp'][:10]}")
        
        print("\nSystem Status:")
        print("- Instruments: Not connected")
        print("- Recorder: Not initialized")
        print("- Ready for setup")
        print()
    
    def get_user_input(self, prompt: str, default: str = None, choices: List[str] = None) -> str:
        """Get user input with validation"""
        while True:
            if default:
                display_prompt = f"{prompt} [{default}]: "
            else:
                display_prompt = f"{prompt}: "
            
            if choices:
                print(f"Options: {', '.join(choices)}")
            
            response = input(display_prompt).strip()
            
            if not response and default:
                return default
            
            if choices and response.lower() not in [c.lower() for c in choices]:
                print(f"Please select from: {', '.join(choices)}")
                continue
            
            if response:
                return response
            
            print("Please provide a response.")
    
    def get_yes_no(self, prompt: str, default: str = "n") -> bool:
        """Get yes/no response from user"""
        response = self.get_user_input(f"{prompt} (y/n)", default, ["y", "n", "yes", "no"])
        return response.lower() in ["y", "yes"]
    
    def connect_instruments(self) -> bool:
        """Interactive instrument connection"""
        print("\n" + "="*60)
        print("INSTRUMENT CONNECTION SETUP")
        print("="*60)
        
        print("Connecting to production instruments...")
        print("Hardware addresses:")
        print("  SMU1: 10.11.83.58")
        print("  SMU2: 10.11.83.60") 
        print("  PSU1: 10.11.83.57")
        print("  PSU2: 10.11.83.52")
        print("  PM1:  M01250277")
        print("  PM2:  M01250278")
        print("  DFB:  COM3")
        
        if not self.get_yes_no("\nProceed with instrument connection?", "y"):
            return False
        
        connections = {
            'SMU1': ('smu', 'TCPIP::10.11.83.58::INSTR'),
            'SMU2': ('smu', 'TCPIP::10.11.83.60::INSTR'),
            'PSU1': ('psu', 'TCPIP::10.11.83.57::INSTR'),
            'PSU2': ('psu', 'TCPIP::10.11.83.52::INSTR'),
            'PM1': ('thorlabs_pm', 'USB0::0x1313::0x8076::M01250277::0::INSTR'),
            'PM2': ('thorlabs_pm', 'USB0::0x1313::0x8076::M01250278::0::INSTR'),
            'LASER': ('dfb13tk', 'COM3')
        }
        
        success_count = 0
        for unit_id, (driver_type, address) in connections.items():
            print(f"Connecting {unit_id}... ", end="", flush=True)
            if self.manager.add_instrument(unit_id, driver_type, address):
                self.instruments[unit_id] = self.manager.get_instrument(unit_id)
                success_count += 1
                print("✓ Connected")
            else:
                print("✗ Failed")
        
        print(f"\nConnection Results: {success_count}/7 instruments connected")
        
        if success_count < 4:
            print("WARNING: Less than 4 instruments connected")
            if not self.get_yes_no("Continue with limited instruments?", "n"):
                return False
        
        print("✓ Instrument setup complete")
        return True
    
    def setup_test_session(self) -> Dict[str, Any]:
        """Interactive test session setup"""
        print("\n" + "="*60)
        print("TEST SESSION SETUP")
        print("="*60)
        
        # Check if this is a rerun
        is_rerun = False
        if self.test_history:
            print("Previous test records found.")
            if self.get_yes_no("Is this a rerun of a previous test?"):
                is_rerun = True
                self.show_previous_tests()
                rerun_id = self.get_user_input("Enter device ID to rerun")
                previous_test = next((t for t in self.test_history if t['device_id'] == rerun_id), None)
                if previous_test:
                    print(f"Found previous test: {previous_test['device_id']}")
                    print(f"Previous result: {previous_test.get('result', 'Unknown')}")
        
        # Get test information
        session_info = {}
        
        if is_rerun and previous_test:
            session_info.update(previous_test)
            session_info['run_type'] = 'rerun'
            session_info['original_timestamp'] = previous_test['timestamp']
            session_info['rerun_count'] = previous_test.get('rerun_count', 0) + 1
        else:
            session_info['run_type'] = 'new'
            session_info['rerun_count'] = 0
        
        # Device information
        print("\nDevice Information:")
        session_info['device_id'] = self.get_user_input(
            "Device ID", 
            session_info.get('device_id', f"FAU_{datetime.now().strftime('%Y%m%d_%H%M')}")
        )
        
        session_info['operator'] = self.get_user_input("Operator name", "Production_User")
        session_info['workstation'] = self.get_user_input("Workstation ID", "TestStation_1")
        
        # Batch information
        print("\nBatch Information:")
        session_info['dut_family'] = self.get_user_input("DUT Family", session_info.get('dut_family', "FAU_Device"))
        session_info['dut_batch'] = self.get_user_input("Batch ID", session_info.get('dut_batch', f"BATCH_{datetime.now().strftime('%Y%m%d')}"))
        session_info['dut_lot'] = self.get_user_input("Lot ID", session_info.get('dut_lot', "LOT_001"))
        session_info['dut_wafer'] = self.get_user_input("Wafer ID", session_info.get('dut_wafer', "W001"))
        
        # Test parameters
        print("\nTest Parameters:")
        device_count = int(self.get_user_input("Number of devices on sample", "2"))
        session_info['device_count'] = device_count
        
        if device_count < 4:
            print("ℹ️  With <4 devices, FAU alignment will be performed via IV sweep")
        
        # Environment information
        print("\nEnvironment Information:")
        session_info['environment'] = {
            'temperature': float(self.get_user_input("Environment temperature (°C)", "22.0")),
            'humidity': float(self.get_user_input("Environment humidity (%)", "45.0")),
            'location': self.get_user_input("Test location", "Production_Lab")
        }
        
        # Data saving preferences
        print("\nData Saving Setup:")
        session_info['log_data'] = self.get_yes_no("Save test data?", "y")
        
        if session_info['log_data']:
            # Configure data saving preferences
            if self.get_yes_no("Configure data saving options?", "y"):
                configure_choice = self.get_user_input(
                    "Choose configuration method", "preset", 
                    ["preset", "custom", "previous"]
                )
                
                if configure_choice == "custom":
                    session_info['data_preferences'] = self.data_manager.get_user_preferences()
                elif configure_choice == "previous":
                    print("Using previously saved preferences")
                    session_info['data_preferences'] = self.data_manager.preferences
                else:  # preset
                    session_info['data_preferences'] = self.data_manager.select_preset()
                
                # Save preferences for future use
                if self.get_yes_no("Save these preferences for future tests?", "y"):
                    self.data_manager.save_preferences()
            else:
                # Use current preferences without modification
                session_info['data_preferences'] = self.data_manager.preferences
            
            # Generate directory structure
            session_info['data_paths'] = self.data_manager.create_data_structure(
                session_info['device_id'], 
                session_info['operator'],
                session_info['timestamp']
            )
            
            # Show what will be saved
            save_summary = self.data_manager.get_save_summary(session_info['data_paths'])
            print(f"\n{save_summary}")
        else:
            print("WARNING: Data will NOT be saved (measurements will still be displayed)")
            session_info['data_preferences'] = None
            session_info['data_paths'] = None
        
        # Multiple runs
        print("\nRun Configuration:")
        if self.get_yes_no("Plan multiple test runs?"):
            session_info['planned_runs'] = int(self.get_user_input("Number of planned runs", "1"))
            session_info['run_interval'] = self.get_user_input("Time between runs (minutes)", "0")
        else:
            session_info['planned_runs'] = 1
            session_info['run_interval'] = "0"
        
        session_info['timestamp'] = datetime.now().isoformat()
        
        return session_info
    
    def show_previous_tests(self):
        """Show previous test history"""
        print("\nPrevious Tests:")
        print("-" * 80)
        print(f"{'Device ID':<20} {'Date':<12} {'Result':<10} {'Operator':<15}")
        print("-" * 80)
        
        recent_tests = sorted(self.test_history, key=lambda x: x['timestamp'], reverse=True)[:10]
        for test in recent_tests:
            date = test['timestamp'][:10]
            result = test.get('result', 'Unknown')
            operator = test.get('operator', 'Unknown')
            print(f"{test['device_id']:<20} {date:<12} {result:<10} {operator:<15}")
        
        if len(self.test_history) > 10:
            print(f"... and {len(self.test_history) - 10} more tests")
        print()
    
    def confirm_test_setup(self, session_info: Dict[str, Any]) -> bool:
        """Show test setup summary and get confirmation"""
        print("\n" + "="*60)
        print("TEST SETUP CONFIRMATION")
        print("="*60)
        
        print(f"Device ID: {session_info['device_id']}")
        print(f"Operator: {session_info['operator']}")
        print(f"Run Type: {session_info['run_type'].upper()}")
        if session_info['run_type'] == 'rerun':
            print(f"Rerun Count: {session_info['rerun_count']}")
        
        print(f"Device Count: {session_info['device_count']}")
        print(f"Environment: {session_info['environment']['temperature']}°C, {session_info['environment']['humidity']}%")
        
        print(f"\nData Saving: {'Enabled' if session_info['log_data'] else 'Disabled'}")
        if session_info['log_data']:
            base_dir = session_info['data_paths']['base']
            print(f"Data Directory: {base_dir}")
            
            prefs = session_info['data_preferences']
            enabled_features = []
            if prefs.save_analysis_plots: enabled_features.append("Analysis Plots")
            if prefs.export_excel: enabled_features.append("Excel")
            if prefs.export_json: enabled_features.append("JSON")
            if prefs.backup_enabled: enabled_features.append("Backup")
            
            if enabled_features:
                print(f"Features: {', '.join(enabled_features)}")
            else:
                print("Features: Core data only")
        
        print(f"Planned Runs: {session_info['planned_runs']}")
        
        print("\nTest Sequence:")
        if session_info['device_count'] < 4:
            print("1. FAU Alignment (IV Sweep)")
            print("2. Laser Power Sweep (15-35mA)")
        else:
            print("1. Laser Power Sweep (15-35mA)")
        print("3. Data Recording & Analysis")
        
        return self.get_yes_no("\nConfirm test setup and begin testing?", "y")
    
    def run_test_sequence(self, session_info: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the test sequence"""
        print("\n" + "="*60)
        print("EXECUTING TEST SEQUENCE")
        print("="*60)
        
        # Initialize recorder if logging enabled
        if session_info['log_data']:
            data_dir = session_info['data_paths']['base']
            self.recorder = UniversalRecorder(data_dir)
            self.recorder.test_run_start(
                workstation=session_info['workstation'],
                dut_family=session_info['dut_family'],
                dut_batch=session_info['dut_batch'],
                dut_lot=session_info['dut_lot'],
                dut_wafer=session_info['dut_wafer'],
                dut_id=session_info['device_id'],
                run_set_id=session_info.get('run_set_id', 1),
                run_id=session_info.get('rerun_count', 0) + 1
            )
        
        test_results = {}
        
        # Step 1: Sample placement reminder
        print("\n📋 STEP 1: Sample Placement")
        print("Please ensure:")
        print("- Sample is placed on chuck")
        print("- Probe card touchdown is complete")
        print("- All connections are secure")
        
        input("Press Enter when sample placement is complete...")
        
        # Step 2: FAU Alignment (if needed)
        if session_info['device_count'] < 4:
            print(f"\n📋 STEP 2: FAU Alignment (Device count: {session_info['device_count']})")
            print("Performing IV sweep for FAU alignment...")
            
            if session_info['log_data']:
                self.recorder.phase_start(1, "FAU_Alignment")
            
            alignment_result = self.perform_fau_alignment()
            test_results['fau_alignment'] = alignment_result
            
            if session_info['log_data']:
                self.recorder.phase_end()
            
            if not alignment_result['success']:
                print("FAILED: FAU alignment failed!")
                return {'success': False, 'error': 'FAU alignment failed'}
            else:
                print("✅ FAU alignment complete")
        
        # Step 3: Laser Power Sweep
        step_num = 3 if session_info['device_count'] < 4 else 2
        print(f"\n📋 STEP {step_num}: Laser Power Sweep")
        print("Performing laser power characterization...")
        print("- Turning laser ON")
        print("- Sweeping current 15-35mA in 0.2mA steps") 
        print("- Measuring power on channels 3&4")
        
        if session_info['log_data']:
            self.recorder.phase_start(step_num, "Laser_Power_Sweep")
        
        sweep_result = self.perform_laser_sweep()
        test_results['laser_sweep'] = sweep_result
        
        if session_info['log_data'] and sweep_result['success']:
            # Record data
            import pandas as pd
            df = pd.DataFrame(sweep_result['measurements'])
            
            self.recorder.record_complete_dataset(
                name='laser_power_characterization',
                data=df,
                test_info={
                    'test_name': 'FAU_Production_Test',
                    'test_location': session_info['environment']['location'],
                    'test_user': session_info['operator'],
                    'device_count': session_info['device_count']
                },
                environment_info=session_info['environment'],
                testing_variable="current_ma",
                dependent_variables=["channel3_power_mw", "channel4_power_mw", "laser_wavelength_nm"],
                equipment_ids="LASER, PM1, PM2"
            )
            
            self.recorder.phase_end()
        
        if not sweep_result['success']:
            print("FAILED: Laser power sweep failed!")
            return {'success': False, 'error': 'Laser power sweep failed'}
        else:
            print("✅ Laser power sweep complete")
        
        # Finalize test
        if session_info['log_data']:
            self.recorder.run_end()
        
        test_results['success'] = True
        test_results['timestamp'] = datetime.now().isoformat()
        
        return test_results
    
    def perform_fau_alignment(self) -> Dict[str, Any]:
        """Perform FAU alignment via IV sweep"""
        smu = self.instruments.get('SMU1')
        if not smu:
            return {'success': False, 'error': 'SMU1 not available'}
        
        try:
            smu.set_mode_source_voltage()
            smu.set_current_limit(0.01)
            smu.enable_output(True)
            
            measurements = []
            for voltage in [v * 0.1 for v in range(51)]:  # 0 to 5V, 0.1V steps
                smu.set_source_voltage(voltage)
                measurement = smu.measure_all()
                measurements.append(measurement)
                
                # Simple progress indication
                if int(voltage * 10) % 10 == 0:
                    print(f"  Voltage: {voltage:.1f}V, Current: {measurement.measured_current*1000:.3f}mA")
            
            smu.enable_output(False)
            
            return {
                'success': True,
                'measurement_count': len(measurements),
                'voltage_range': '0-5V',
                'measurements': [m.to_dict() for m in measurements]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def perform_laser_sweep(self) -> Dict[str, Any]:
        """Perform laser power sweep with dual power meters"""
        laser = self.instruments.get('LASER')
        pm1 = self.instruments.get('PM1') 
        pm2 = self.instruments.get('PM2')
        
        if not all([laser, pm1, pm2]):
            missing = []
            if not laser: missing.append('LASER')
            if not pm1: missing.append('PM1')
            if not pm2: missing.append('PM2')
            return {'success': False, 'error': f'Missing instruments: {", ".join(missing)}'}
        
        try:
            # Setup laser
            laser.set_temperature(25.0)
            laser.wait_temperature_stable(timeout=30)
            laser.laser_on()
            
            # Setup power meters
            pm1.set_wavelength(1310)
            pm1.set_power_unit("W")
            pm1.set_auto_range(True)
            
            pm2.set_wavelength(1310)
            pm2.set_power_unit("W")
            pm2.set_auto_range(True)
            
            measurements = []
            current_ma = 15.0
            
            print("  Progress:")
            while current_ma <= 35.0:
                laser.set_current(current_ma)
                
                laser_measurement = laser.measure_all()
                pm1_measurement = pm1.measure_all('PM1')
                pm2_measurement = pm2.measure_all('PM2')
                
                combined_data = {
                    'current_ma': current_ma,
                    'laser_wavelength_nm': laser_measurement.wavelength_nm,
                    'laser_power_mw': laser_measurement.estimated_power_mw,
                    'channel3_power_w': pm1_measurement.power_w,
                    'channel3_power_mw': pm1_measurement.power_mw,
                    'channel4_power_w': pm2_measurement.power_w,
                    'channel4_power_mw': pm2_measurement.power_mw,
                    'timestamp': laser_measurement.timestamp
                }
                
                measurements.append(combined_data)
                
                # Progress indication
                if int((current_ma - 15) * 10) % 10 == 0:
                    print(f"    {current_ma:.1f}mA: CH3={pm1_measurement.power_mw:.3f}mW, CH4={pm2_measurement.power_mw:.3f}mW")
                
                current_ma += 0.2
            
            laser.laser_off()
            
            return {
                'success': True,
                'measurement_count': len(measurements),
                'current_range': '15.0-35.0mA',
                'measurements': measurements
            }
            
        except Exception as e:
            if 'laser' in locals():
                laser.laser_off()  # Safety
            return {'success': False, 'error': str(e)}
    
    def show_test_results(self, session_info: Dict[str, Any], test_results: Dict[str, Any]):
        """Display test results summary"""
        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)
        
        print(f"Device ID: {session_info['device_id']}")
        print(f"Test Status: {'PASSED' if test_results['success'] else 'FAILED'}")
        print(f"Completion Time: {test_results.get('timestamp', 'Unknown')}")
        
        if 'fau_alignment' in test_results:
            align_result = test_results['fau_alignment']
            print(f"FAU Alignment: {'Success' if align_result['success'] else 'Failed'}")
            if align_result['success']:
                print(f"  - Measurements: {align_result['measurement_count']}")
        
        if 'laser_sweep' in test_results:
            sweep_result = test_results['laser_sweep']
            print(f"Laser Sweep: {'Success' if sweep_result['success'] else 'Failed'}")
            if sweep_result['success']:
                print(f"  - Measurements: {sweep_result['measurement_count']}")
                print(f"  - Current Range: {sweep_result['current_range']}")
        
        if session_info['log_data'] and test_results['success']:
            data_dir = session_info['data_paths']['base']
            print(f"Data Location: {data_dir}")
            
            prefs = session_info['data_preferences']
            saved_items = ["CSV data", "Test parameters", "Session log"]
            
            if prefs.save_analysis_plots: saved_items.append("Analysis plots")
            if prefs.save_summary_plots: saved_items.append("Summary plots")
            if prefs.export_excel: saved_items.append("Excel files")
            if prefs.export_json: saved_items.append("JSON data")
            if prefs.backup_enabled: saved_items.append("Backup copy")
            
            print(f"Saved: {', '.join(saved_items)}")
        
        # Add to test history
        history_record = {
            'device_id': session_info['device_id'],
            'timestamp': test_results.get('timestamp'),
            'result': 'PASSED' if test_results['success'] else 'FAILED',
            'operator': session_info['operator'],
            'run_type': session_info['run_type'],
            'rerun_count': session_info.get('rerun_count', 0)
        }
        
        if test_results.get('error'):
            history_record['error'] = test_results['error']
        
        self.test_history.append(history_record)
        self.save_session_data()
    
    def ask_next_action(self, session_info: Dict[str, Any]) -> str:
        """Ask user what to do next"""
        print("\n" + "="*60)
        print("NEXT ACTION")
        print("="*60)
        
        actions = ["new", "rerun", "exit"]
        
        if session_info.get('planned_runs', 1) > 1:
            actions.insert(0, "continue")
            print("Options:")
            print("  continue - Continue with next planned run")
            print("  new      - Start new test with different device")
            print("  rerun    - Repeat current test")
            print("  exit     - Exit system")
        else:
            print("Options:")
            print("  new   - Start new test with different device") 
            print("  rerun - Repeat current test")
            print("  exit  - Exit system")
        
        return self.get_user_input("Select next action", "exit", actions)
    
    def cleanup(self):
        """Cleanup system resources"""
        print("\n📋 System Cleanup")
        print("Disconnecting instruments...")
        self.manager.disconnect_all()
        
        if self.recorder:
            print("Finalizing data recording...")
            self.recorder.run_end()
        
        self.save_session_data()
        print("✅ Cleanup complete")
    
    def run(self):
        """Main interactive system loop"""
        try:
            self.print_welcome()
            
            # Connect instruments
            if not self.connect_instruments():
                print("ERROR: Cannot proceed without instruments")
                return
            
            while True:
                # Setup test session
                session_info = self.setup_test_session()
                self.current_session = session_info
                
                # Confirm setup
                if not self.confirm_test_setup(session_info):
                    print("Test cancelled by user")
                    continue
                
                # Run test sequence
                print(f"\nStarting test for device: {session_info['device_id']}")
                test_results = self.run_test_sequence(session_info)
                
                # Show results
                self.show_test_results(session_info, test_results)
                
                # Ask what to do next
                next_action = self.ask_next_action(session_info)
                
                if next_action == "exit":
                    break
                elif next_action == "rerun":
                    print("Preparing for rerun...")
                    continue
                elif next_action == "new":
                    print("Preparing for new test...")
                    continue
                elif next_action == "continue":
                    print("Continuing with planned runs...")
                    # Update session for next run
                    session_info['rerun_count'] += 1
                    continue
        
        except KeyboardInterrupt:
            print("\n\nWARNING: Test interrupted by user")
        except Exception as e:
            print(f"\nERROR: System error: {e}")
            logging.error(f"System error: {e}", exc_info=True)
        finally:
            self.cleanup()

if __name__ == "__main__":
    system = InteractiveTestSystem()
    system.run()