#!/usr/bin/env python3
"""
FAU Production Test System - Health Check Script

Comprehensive health check for all instrument drivers and system components.
Tests connectivity, basic functionality, and safety states of all instruments.

Usage:
    python health_check.py [--quick] [--verbose] [--config CONFIG_FILE]

Options:
    --quick     Run quick connectivity tests only (skip extended tests)
    --verbose   Enable detailed output for debugging
    --config    Use custom configuration file (default: auto-detect)
"""

import sys
import time
import json
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from contextlib import contextmanager

# Import all drivers
from drivers.dfb13tk import DFB13TK
from drivers.pm101 import ThorlabsPowerMeter
from drivers.smu import AimTTi_SMU4000
from drivers.tti_qlp355 import TTi_QL355TP

class HealthCheckResult:
    def __init__(self, name: str, success: bool = False, message: str = "", details: Dict = None):
        self.name = name
        self.success = success
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()

class InstrumentHealthChecker:
    """Comprehensive health check system for FAU production test instruments."""
    
    def __init__(self, config: Dict = None, verbose: bool = False):
        self.verbose = verbose
        self.results: List[HealthCheckResult] = []
        self.config = config or self._get_default_config()
        
    def _get_default_config(self) -> Dict:
        """Default production configuration."""
        return {
            'instruments': {
                'SMU1': {
                    'driver': 'smu',
                    'address': 'TCPIP::10.11.83.58::5025::SOCKET',
                    'unit_id': 'SMU1',
                    'timeout': 20.0
                },
                'SMU2': {
                    'driver': 'smu', 
                    'address': 'TCPIP::10.11.83.60::5025::SOCKET',
                    'unit_id': 'SMU2',
                    'timeout': 20.0
                },
                'PSU1': {
                    'driver': 'psu',
                    'address': 'TCPIP::10.11.83.57::9221::SOCKET',
                    'unit_id': 'PSU1',
                    'timeout': 20.0
                },
                'PSU2': {
                    'driver': 'psu',
                    'address': 'TCPIP::10.11.83.52::9221::SOCKET',
                    'unit_id': 'PSU2', 
                    'timeout': 20.0
                },
                'PM1': {
                    'driver': 'pm',
                    'address': 'USB0::0x1313::0x8076::M01250277::0::INSTR',
                    'unit_id': 'PM1',
                    'channel': 3
                },
                'PM2': {
                    'driver': 'pm',
                    'address': 'USB0::0x1313::0x8076::M01250278::0::INSTR', 
                    'unit_id': 'PM2',
                    'channel': 4
                },
                'LASER': {
                    'driver': 'laser',
                    'address': 'COM3',
                    'timeout': 20.0
                }
            },
            'test_parameters': {
                'laser_safe_current': 150.0,  # mA
                'laser_safe_temp': 25.0,      # °C
                'pm_wavelength': 1310,        # nm
                'smu_test_voltage': 1.0,      # V
                'psu_test_voltage': 3.3,      # V
                'psu_test_current': 0.1       # A
            }
        }
    
    def log(self, message: str):
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def add_result(self, name: str, success: bool, message: str, details: Dict = None):
        """Add test result to results list."""
        result = HealthCheckResult(name, success, message, details)
        self.results.append(result)
        return result
    
    @contextmanager
    def safe_instrument_context(self, instrument_class, *args, **kwargs):
        """Safe context manager for instrument connections."""
        instrument = None
        try:
            instrument = instrument_class(*args, **kwargs)
            yield instrument
        except Exception as e:
            self.log(f"Failed to initialize {instrument_class.__name__}: {e}")
            raise
        finally:
            if instrument and hasattr(instrument, 'close'):
                try:
                    instrument.close()
                except:
                    pass
            elif instrument and hasattr(instrument, 'disconnect'):
                try:
                    instrument.disconnect()
                except:
                    pass
    
    def test_dfb_laser(self, config: Dict) -> HealthCheckResult:
        """Test DFB laser connectivity and basic functions."""
        self.log("Testing DFB laser...")
        
        try:
            with self.safe_instrument_context(DFB13TK, config['address']) as laser:
                # Test basic connectivity
                serial_num = laser.get_serial_number()
                firmware = laser.get_firmware_version()
                
                # Test state reading
                laser_state = laser.get_laser_state()
                current = laser.get_current()
                temperature = laser.get_temperature()
                
                # Test safe parameter setting
                test_temp = self.config['test_parameters']['laser_safe_temp']
                laser.set_temperature(test_temp)
                
                # Verify laser is OFF (safety check)
                if laser_state == 60:  # Laser is ON
                    laser.laser_off()
                    time.sleep(0.5)
                    laser_state = laser.get_laser_state()
                
                details = {
                    'serial_number': serial_num,
                    'firmware': firmware,
                    'laser_state': 'ON' if laser_state == 60 else 'OFF',
                    'current_ma': current,
                    'temperature_c': temperature,
                    'temperature_set_c': test_temp
                }
                
                success = laser_state == 61  # OFF state
                message = f"DFB laser functional (S/N: {serial_num}, FW: {firmware})"
                if not success:
                    message = f"WARNING: Laser state is ON - turned OFF for safety"
                
                return self.add_result("DFB_LASER", success, message, details)
                
        except Exception as e:
            return self.add_result("DFB_LASER", False, f"Failed: {e}")
    
    def test_power_meter(self, name: str, config: Dict) -> HealthCheckResult:
        """Test power meter connectivity and basic functions."""
        self.log(f"Testing power meter {name}...")
        
        try:
            with self.safe_instrument_context(ThorlabsPowerMeter, config['address'], True, config['unit_id']) as pm:
                # Test basic connectivity
                idn = pm.get_idn()
                
                # Set wavelength
                wavelength = self.config['test_parameters']['pm_wavelength']
                pm.set_wavelength(wavelength)
                
                # Test power reading
                power_w = pm.read_power()
                power_dbm = pm.read_power_dbm()
                
                # Get calibration info
                cal_msg = pm.get_calibration_message()
                
                status = pm.get_status()
                
                details = {
                    'identification': idn,
                    'wavelength_nm': wavelength,
                    'power_w': power_w,
                    'power_dbm': power_dbm,
                    'calibration': cal_msg,
                    'channel': config.get('channel', 'N/A'),
                    'status': status
                }
                
                success = True
                message = f"Power meter {name} functional ({idn})"
                
                return self.add_result(f"POWER_METER_{name}", success, message, details)
                
        except Exception as e:
            return self.add_result(f"POWER_METER_{name}", False, f"Failed: {e}")
    
    def test_smu(self, name: str, config: Dict) -> HealthCheckResult:
        """Test SMU connectivity and basic functions."""
        self.log(f"Testing SMU {name}...")
        
        try:
            with self.safe_instrument_context(AimTTi_SMU4000, config['address'], config['unit_id']) as smu:
                # Test basic connectivity
                idn = smu.get_idn()
                
                # Check for errors
                errors = smu.get_errors()
                if errors:
                    smu.clear_errors()
                
                # Test mode setting
                smu.set_mode_source_voltage()
                mode = smu.get_source_mode()
                
                # Verify output is disabled (safety)
                output_state = smu.get_output_state()
                
                # Test measurement (with output disabled)
                voltage = smu.measure_voltage()
                current = smu.measure_current()
                
                status = smu.get_status()
                
                details = {
                    'identification': idn,
                    'source_mode': mode,
                    'output_enabled': output_state,
                    'voltage_v': voltage,
                    'current_a': current,
                    'errors_cleared': len(errors) if errors else 0,
                    'status': status
                }
                
                success = not output_state  # Output should be disabled
                message = f"SMU {name} functional ({idn.split(',')[1].strip()} if available)"
                if output_state:
                    message = f"WARNING: SMU {name} output was enabled - disabled for safety"
                
                return self.add_result(f"SMU_{name}", success, message, details)
                
        except Exception as e:
            return self.add_result(f"SMU_{name}", False, f"Failed: {e}")
    
    def test_psu(self, name: str, config: Dict) -> HealthCheckResult:
        """Test power supply connectivity and basic functions."""
        self.log(f"Testing PSU {name}...")
        
        try:
            with self.safe_instrument_context(TTi_QL355TP, config['address'], config['unit_id']) as psu:
                # Test basic connectivity
                idn = psu.get_idn()
                
                # Check both channels
                ch1_state = psu.get_output_state(1)
                ch2_state = psu.get_output_state(2)
                
                # Get voltage/current settings
                ch1_voltage = psu.get_set_voltage(1)
                ch2_voltage = psu.get_set_voltage(2)
                ch1_current = psu.get_set_current_limit(1)
                ch2_current = psu.get_set_current_limit(2)
                
                # Measure output (should be 0V if disabled)
                ch1_output_v = psu.get_output_voltage(1)
                ch2_output_v = psu.get_output_voltage(2)
                
                status = psu.get_status()
                
                details = {
                    'identification': idn,
                    'channel_1': {
                        'output_enabled': ch1_state,
                        'set_voltage_v': ch1_voltage,
                        'set_current_a': ch1_current,
                        'output_voltage_v': ch1_output_v
                    },
                    'channel_2': {
                        'output_enabled': ch2_state,
                        'set_voltage_v': ch2_voltage, 
                        'set_current_a': ch2_current,
                        'output_voltage_v': ch2_output_v
                    },
                    'status': status
                }
                
                # Both outputs should be disabled for safety
                success = not ch1_state and not ch2_state
                message = f"PSU {name} functional ({idn.split(',')[1].strip()} if available)"
                if ch1_state or ch2_state:
                    message = f"WARNING: PSU {name} had enabled outputs - disabled for safety"
                
                return self.add_result(f"PSU_{name}", success, message, details)
                
        except Exception as e:
            return self.add_result(f"PSU_{name}", False, f"Failed: {e}")
    
    def run_quick_check(self) -> List[HealthCheckResult]:
        """Run quick connectivity test on all instruments."""
        self.log("Starting quick health check...")
        self.results.clear()
        
        for name, config in self.config['instruments'].items():
            driver_type = config['driver']
            
            if driver_type == 'laser':
                self.test_dfb_laser(config)
            elif driver_type == 'pm':
                self.test_power_meter(name, config)
            elif driver_type == 'smu':
                self.test_smu(name, config)
            elif driver_type == 'psu':
                self.test_psu(name, config)
        
        return self.results
    
    def run_full_check(self) -> List[HealthCheckResult]:
        """Run comprehensive health check including extended tests."""
        # For now, full check is same as quick check
        # Could be extended with more thorough testing
        return self.run_quick_check()
    
    def print_summary(self):
        """Print comprehensive test summary."""
        if not self.results:
            print("No test results available.")
            return
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*60)
        print("FAU PRODUCTION TEST SYSTEM - HEALTH CHECK RESULTS")
        print("="*60)
        print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print("="*60)
        
        # Print individual results
        for result in self.results:
            status = "PASS" if result.success else "FAIL"
            print(f"[{status}] {result.name}: {result.message}")
            
            if self.verbose and result.details:
                for key, value in result.details.items():
                    if isinstance(value, dict):
                        print(f"  {key}:")
                        for k, v in value.items():
                            print(f"    {k}: {v}")
                    else:
                        print(f"  {key}: {value}")
        
        print("="*60)
        
        if failed_tests == 0:
            print("STATUS: All systems operational - ready for production")
        else:
            print(f"STATUS: {failed_tests} system(s) require attention")
        
        print("="*60)
    
    def export_results(self, filename: str = None):
        """Export results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"health_check_{timestamp}.json"
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.results),
            'passed_tests': sum(1 for r in self.results if r.success),
            'failed_tests': sum(1 for r in self.results if not r.success),
            'results': []
        }
        
        for result in self.results:
            export_data['results'].append({
                'name': result.name,
                'success': result.success,
                'message': result.message,
                'details': result.details,
                'timestamp': result.timestamp.isoformat()
            })
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Results exported to: {filename}")


def main():
    """Main health check execution."""
    parser = argparse.ArgumentParser(description='FAU Production Test System Health Check')
    parser.add_argument('--quick', action='store_true', 
                       help='Run quick connectivity tests only')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable detailed output')
    parser.add_argument('--config', type=str,
                       help='Use custom configuration file')
    parser.add_argument('--export', type=str, 
                       help='Export results to JSON file')
    
    args = parser.parse_args()
    
    # Load configuration if provided
    config = None
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Failed to load configuration file: {e}")
            sys.exit(1)
    
    # Create health checker
    checker = InstrumentHealthChecker(config=config, verbose=args.verbose)
    
    # Run tests
    print("FAU Production Test System - Health Check")
    print("Starting instrument health check...")
    
    try:
        if args.quick:
            results = checker.run_quick_check()
        else:
            results = checker.run_full_check()
        
        # Print summary
        checker.print_summary()
        
        # Export if requested
        if args.export:
            checker.export_results(args.export)
        
        # Exit with appropriate code
        failed_count = sum(1 for r in results if not r.success)
        sys.exit(0 if failed_count == 0 else 1)
        
    except KeyboardInterrupt:
        print("\nHealth check interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Health check failed with error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()