
import logging
from typing import Dict, Any
from drivers import MultiInstrumentManager
from utils.recorder import UniversalRecorder

class ProductionTestFlow:
    def __init__(self):
        self.manager = MultiInstrumentManager()
        self.recorder = UniversalRecorder('./production_data')
        self.instruments = {}
        
    def connect_instruments(self) -> bool:
        connections = {
            'SMU1': ('smu', 'TCPIP::10.11.83.58::INSTR'),
            'SMU2': ('smu', 'TCPIP::10.11.83.60::INSTR'),
            'PSU1': ('psu', 'TCPIP::10.11.83.57::INSTR'),
            'PSU2': ('psu', 'TCPIP::10.11.83.52::INSTR'),
            'PM1': ('thorlabs_pm', 'USB0::0x1313::0x8076::M01250277::0::INSTR'),
            'PM2': ('thorlabs_pm', 'USB0::0x1313::0x8076::M01250278::0::INSTR'),
            'LASER': ('dfb13tk', 'COM3')
        }
        
        for unit_id, (driver_type, address) in connections.items():
            if self.manager.add_instrument(unit_id, driver_type, address):
                self.instruments[unit_id] = self.manager.get_instrument(unit_id)
        
        return len(self.instruments) >= 4
    
    def fau_alignment_iv_sweep(self, device_count: int) -> bool:
        if device_count >= 4:
            return True
            
        smu = self.instruments.get('SMU1')
        if not smu:
            return False
            
        smu.set_mode_source_voltage()
        smu.set_current_limit(0.01)
        smu.enable_output(True)
        
        measurements = []
        for voltage in [v * 0.1 for v in range(51)]:  # 0 to 5V, 0.1V steps
            smu.set_source_voltage(voltage)
            measurement = smu.measure_all()
            measurements.append(measurement)
        
        smu.enable_output(False)
        return len(measurements) > 0
    
    def laser_power_sweep(self, start_current_ma: float = 15.0, max_current_ma: float = 35.0) -> Dict[str, Any]:
        laser = self.instruments.get('LASER')
        pm1 = self.instruments.get('PM1')
        pm2 = self.instruments.get('PM2')
        
        if not all([laser, pm1, pm2]):
            return {}
        
        laser.set_temperature(25.0)
        laser.wait_temperature_stable(timeout=30)
        laser.laser_on()
        
        pm1.set_wavelength(1310)
        pm1.set_power_unit("W")
        pm1.set_auto_range(True)
        
        pm2.set_wavelength(1310)
        pm2.set_power_unit("W")
        pm2.set_auto_range(True)
        
        measurements = []
        current_ma = start_current_ma
        
        while current_ma <= max_current_ma:
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
            current_ma += 0.2
        
        laser.laser_off()
        return {'measurements': measurements, 'success': True}
    
    def execute_test_sequence(self, device_count: int, test_info: Dict, env_info: Dict) -> bool:
        self.recorder.test_run_start(
            workstation=test_info.get('workstation', 'Station1'),
            dut_family=test_info.get('dut_family', 'FAU'),
            dut_batch=test_info.get('dut_batch', 'B001'),
            dut_lot=test_info.get('dut_lot', 'L001'),
            dut_wafer=test_info.get('dut_wafer', 'W001'),
            dut_id=test_info.get('dut_id', 'DUT001'),
            run_set_id=test_info.get('run_set_id', 1),
            run_id=test_info.get('run_id', 1)
        )
        
        if device_count < 4:
            self.recorder.phase_start(1, "FAU_Alignment")
            alignment_success = self.fau_alignment_iv_sweep(device_count)
            self.recorder.phase_end()
            
            if not alignment_success:
                self.recorder.run_end()
                return False
        
        self.recorder.phase_start(2, "Laser_Power_Sweep")
        sweep_results = self.laser_power_sweep()
        
        if sweep_results.get('success'):
            import pandas as pd
            df = pd.DataFrame(sweep_results['measurements'])
            
            result = self.recorder.record_complete_dataset(
                name='laser_power_characterization',
                data=df,
                test_info=test_info,
                environment_info=env_info,
                testing_variable="current_ma",
                dependent_variables=["channel3_power_mw", "channel4_power_mw", "laser_wavelength_nm"],
                equipment_ids="LASER, PM1, PM2"
            )
            
            self.recorder.phase_end()
            self.recorder.run_end()
            return result is not None
        
        self.recorder.phase_end()
        self.recorder.run_end()
        return False
    
    def disconnect_all(self):
        self.manager.disconnect_all()

def run_customer_test():
    test_flow = ProductionTestFlow()
    
    if not test_flow.connect_instruments():
        logging.error("Failed to connect required instruments")
        return False
    
    test_info = {
        "test_name": "FAU_Production_Test",
        "test_location": "Production_Line",
        "test_user": "Operator",
        "workstation": "TestStation_1",
        "dut_family": "FAU_Device",
        "dut_batch": "PROD_BATCH_001",
        "dut_lot": "LOT_001",
        "dut_wafer": "W001",
        "dut_id": "FAU_001"
    }
    
    env_info = {
        "environment_temp": 22.0,
        "environment_humidity": 45.0
    }
    
    device_count = 2  # Set based on actual device configuration
    
    try:
        success = test_flow.execute_test_sequence(device_count, test_info, env_info)
        return success
    finally:
        test_flow.disconnect_all()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = run_customer_test()
    exit(0 if success else 1)