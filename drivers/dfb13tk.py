import serial
import time
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class DFBMeasurement:
    timestamp: str
    current_ma: float
    temperature_actual_c: float
    temperature_setpoint_c: float
    wavelength_nm: float
    estimated_power_mw: float
    laser_state: int
    tec_adjustment_c: float
    laser_on: bool
    temperature_stable: bool
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass 
class DFBSweepConfig:
    parameter: str
    start_value: float
    stop_value: float
    steps: int
    step_delay: float = 1.0
    stabilization_timeout: float = 30.0
    stabilization_tolerance: float = 0.1

class DFB13TK:
    
    def __init__(self, port="COM3", baudrate=9600):
        self.port = port
        self.ser = serial.Serial(port, baudrate, timeout=1.0)
        self._current_ma = 150.0
        self._temp_setpoint = 25.0
        
    def close(self):
        if self.ser.is_open:
            self.ser.close()
    
    def _cmd(self, command):
        self.ser.reset_input_buffer()
        self.ser.write(f"{command}\r".encode())
        response = self.ser.readline().decode('utf-8').strip()
        
        if ':' in response:
            code, msg = response.split(':', 1)
            if code != "000":
                raise RuntimeError(f"Device error {code}: {msg}")
            return msg
        return response
    
    def laser_on(self):
        self._cmd("laser on")
    
    def laser_off(self):
        self._cmd("laser off")
    
    def get_laser_state(self):
        try:
            state = self._cmd("read_param laser_state")
            return int(state) if state else 61
        except:
            return 61
    
    def set_current(self, current_ma):
        if not 0 <= current_ma <= 450:
            raise ValueError("Current must be 0-450 mA")
        amps = current_ma / 1000.0
        self._cmd(f"write_param laser.current {amps}")
        self._current_ma = current_ma
    
    def get_current(self):
        try:
            current_str = self._cmd("read_param laser.current")
            if current_str:
                return float(current_str) * 1000
        except:
            pass
        return self._current_ma
    
    def set_temperature(self, temp_c):
        if not 15 <= temp_c <= 35:
            raise ValueError("Temperature must be 15-35°C")
        self._cmd(f"write_param laser_tec_ctrl.setpoint {temp_c}")
        self._temp_setpoint = temp_c
    
    def get_temperature_setpoint(self):
        """Get temperature setpoint in °C"""
        try:
            temp_str = self._cmd("read_param laser_tec_ctrl.setpoint")
            if temp_str:
                return float(temp_str)
        except:
            pass
        return self._temp_setpoint
    
    def get_temperature(self):
        """Get actual temperature reading in °C"""
        try:
            temp_str = self._cmd("read_param laser_tec_ctrl.temperature")
            if temp_str:
                return float(temp_str)
        except:
            pass
        return self._temp_setpoint
    
    def wait_temperature_stable(self, tolerance=0.1, timeout=60):
        """Wait for temperature to stabilize within tolerance"""
        start_time = time.time()
        setpoint = self.get_temperature_setpoint()
        
        while time.time() - start_time < timeout:
            if abs(self.get_temperature() - setpoint) <= tolerance:
                return True
            time.sleep(1)
        return False
    
    def enable_tec_adjustment(self):
        """Enable TEC adjustment for laser (121=Laser TEC, 120=None)"""
        self._cmd("write_param tec_adj.select 121")
    
    def disable_tec_adjustment(self):
        """Disable TEC adjustment"""
        self._cmd("write_param tec_adj.select 120")
    
    def set_tec_adjustment_range(self, range_c):
        """Set TEC adjustment range +/- in °C"""
        self._cmd(f"write_param tec_adj.range {range_c}")
    
    def get_tec_adjustment_range(self):
        """Get TEC adjustment range"""
        try:
            range_str = self._cmd("read_param tec_adj.range")
            return float(range_str) if range_str else 1.0
        except:
            return 1.0
    
    def get_tec_adjustment(self):
        """Get active TEC adjustment in °C"""
        try:
            adj_str = self._cmd("read_param tec_adj")
            return float(adj_str) if adj_str else 0.0
        except:
            return 0.0
    
    def calculate_wavelength(self, current_ma=None, temp_c=None):
        if current_ma is None:
            current_ma = self.get_current()
        if temp_c is None:
            temp_c = self.get_temperature()
        
        base_wavelength = 1310.0
        base_current = 200.0
        base_temp = 25.0
        
        current_shift = (current_ma - base_current) * 0.003
        temp_shift = (temp_c - base_temp) * 0.08
        
        return base_wavelength + current_shift + temp_shift
    
    def calculate_power(self, current_ma=None):
        if current_ma is None:
            current_ma = self.get_current()
        
        threshold_ma = 15.0
        slope_efficiency_w_per_a = 0.27
        
        if current_ma <= threshold_ma:
            return 0.0
        
        power_w = (current_ma - threshold_ma) / 1000.0 * slope_efficiency_w_per_a
        return power_w * 1000.0
    
    def get_firmware_version(self):
        return self._cmd("firmware_version")
    
    def get_serial_number(self):
        return self._cmd("read_string module_sn")
    
    def get_laser_serial(self):
        return self._cmd("read_string laser_sn")
    
    def get_oem_string(self):
        return self._cmd("read_string oem")
    
    def get_main_board_serial(self):
        return self._cmd("read_string main_board_sn")
    
    def get_clock(self):
        return self._cmd("get_clock")
    
    def save_config(self):
        self._cmd("savecfg")
    
    def save_parameter(self, tag):
        self._cmd(f"save_param {tag}")
    
    def read_parameter(self, tag):
        return self._cmd(f"read_param {tag}")
    
    def write_parameter(self, tag, value):
        self._cmd(f"write_param {tag} {value}")
    
    def reset_system(self):
        self._cmd("reset")
    
    def enter_update_mode(self):
        self._cmd("update")
    
    def get_status(self):
        current_ma = self.get_current()
        temp_actual = self.get_temperature()
        temp_setpoint = self.get_temperature_setpoint()
        
        return {
            'current_ma': current_ma,
            'temperature_actual_c': temp_actual,
            'temperature_setpoint_c': temp_setpoint,
            'wavelength_nm': self.calculate_wavelength(current_ma, temp_actual),
            'estimated_power_mw': self.calculate_power(current_ma),
            'laser_state': self.get_laser_state(),
            'tec_adjustment_c': self.get_tec_adjustment(),
            'tec_adjustment_range_c': self.get_tec_adjustment_range()
        }
    
    def get_device_info(self):
        """Get device information dictionary"""
        try:
            return {
                'firmware_version': self.get_firmware_version(),
                'module_serial': self.get_serial_number(),
                'laser_serial': self.get_laser_serial(),
                'main_board_serial': self.get_main_board_serial(),
                'oem_string': self.get_oem_string(),
                'system_clock': self.get_clock(),
                'port': self.port
            }
        except:
            return {'port': self.port}
    
    def get_modulation_specs(self):
        """Get external modulation specifications"""
        return {
            'ac_modulation': {
                'voltage_to_current': '10 mA/V',
                'wavelength_range': '±0.15 nm',
                'power_range': '±10 mW',
                'frequency_range': '2 kHz to 20 MHz',
                'input_voltage': '-5 V to 5 V',
                'input_impedance': '1 kΩ'
            },
            'dc_modulation': {
                'voltage_to_current': '2 mA/V', 
                'wavelength_range': '±0.03 nm',
                'power_range': '±1 mW',
                'frequency_range': 'DC to 5 MHz',
                'input_voltage': '-5 V to 5 V',
                'input_impedance': '1 kΩ'
            },
            'temperature_modulation': {
                'voltage_to_temperature': '0.2 °C/V (default)',
                'frequency_range': 'DC to 1 Hz',
                'input_voltage': '-5 V to 5 V',
                'input_impedance': '1 kΩ'
            }
        }
    
    def get_specifications(self):
        """Get laser specifications from manual"""
        return {
            'center_wavelength_nm': {'min': 1305, 'max': 1315},
            'output_power_mw': {'min': 100},
            'linewidth_khz': {'typical': 100, 'max': 200},
            'mode_hop_free_current_ma': {'min': 50, 'max': 500},
            'mode_hop_free_power_mw': {'min': 15, 'max': 100},
            'smsr_db': {'min': 35, 'typical': 50},
            'threshold_current_ma': {'typical': 15},
            'slope_efficiency_w_per_a': {'typical': 0.27},
            'current_tuning_nm_per_ma': {'typical': 0.003},
            'temp_tuning_nm_per_c': {'typical': 0.08},
            'temp_range_c': {'min': 15, 'max': 35},
            'temp_tuning_range_nm': {'typical': 1.6},
            'rin_dbc_per_hz': {'typical': -150},
            'per_db': {'typical': 25},
            'isolation_db': {'typical': 25}
        }
    
    def tune_wavelength_by_current(self, target_wavelength_nm):
        """Tune to target wavelength using current (approximate)"""
        current_wavelength = self.calculate_wavelength()
        wavelength_diff = target_wavelength_nm - current_wavelength
        
        current_change_ma = wavelength_diff / 0.003
        new_current = self.get_current() + current_change_ma
        
        if 0 <= new_current <= 450:
            self.set_current(new_current)
            return True
        return False
    
    def tune_wavelength_by_temperature(self, target_wavelength_nm):
        """Tune to target wavelength using temperature (approximate)"""
        current_wavelength = self.calculate_wavelength()
        wavelength_diff = target_wavelength_nm - current_wavelength
        
        temp_change_c = wavelength_diff / 0.08
        new_temp = self.get_temperature_setpoint() + temp_change_c
        
        if 15 <= new_temp <= 35:
            self.set_temperature(new_temp)
            return True
        return False
    
    def get_mode_hop_free_range(self):
        """Check if current operation is in mode-hop-free range"""
        current_ma = self.get_current()
        power_mw = self.calculate_power(current_ma)
        
        specs = self.get_specifications()
        current_ok = specs['mode_hop_free_current_ma']['min'] <= current_ma <= specs['mode_hop_free_current_ma']['max']
        power_ok = specs['mode_hop_free_power_mw']['min'] <= power_mw <= specs['mode_hop_free_power_mw']['max']
        
        return {
            'in_range': current_ok and power_ok,
            'current_ok': current_ok,
            'power_ok': power_ok,
            'current_ma': current_ma,
            'power_mw': power_mw
        }
    
    def calculate_tuning_range(self):
        """Calculate available tuning ranges"""
        current_ma = self.get_current()
        temp_c = self.get_temperature_setpoint()
        
        max_current_change = min(450 - current_ma, current_ma)
        current_tuning_range_nm = max_current_change * 0.003
        
        max_temp_change = min(35 - temp_c, temp_c - 15)
        temp_tuning_range_nm = max_temp_change * 0.08
        
        return {
            'current_tuning_range_nm': current_tuning_range_nm,
            'temperature_tuning_range_nm': temp_tuning_range_nm,
            'total_range_nm': current_tuning_range_nm + temp_tuning_range_nm
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.laser_off()
        except:
            pass
        self.close()

    def measure_all(self) -> DFBMeasurement:
        """Take comprehensive measurement of all laser parameters"""
        timestamp = datetime.now().isoformat()
        
        current_ma = self.get_current()
        temp_actual = self.get_temperature()
        temp_setpoint = self.get_temperature_setpoint()
        wavelength_nm = self.calculate_wavelength(current_ma, temp_actual)
        power_mw = self.calculate_power(current_ma)
        laser_state = self.get_laser_state()
        tec_adj = self.get_tec_adjustment()
        laser_on = laser_state == 60  # 60 = laser on state
        
        temp_stable = abs(temp_actual - temp_setpoint) <= 0.1
        
        measurement = DFBMeasurement(
            timestamp=timestamp,
            current_ma=current_ma,
            temperature_actual_c=temp_actual,
            temperature_setpoint_c=temp_setpoint,
            wavelength_nm=wavelength_nm,
            estimated_power_mw=power_mw,
            laser_state=laser_state,
            tec_adjustment_c=tec_adj,
            laser_on=laser_on,
            temperature_stable=temp_stable
        )
        
        return measurement

    def current_sweep(self, config: DFBSweepConfig) -> pd.DataFrame:
        """
        Perform current sweep with comprehensive data collection
        
        Returns:
            DataFrame ready for recorder.record_complete_dataset()
        """
        if config.parameter != 'current':
            raise ValueError("Use current_sweep for current parameter sweeps")
            
        print(f"Starting DFB current sweep: {config.start_value}mA to {config.stop_value}mA, {config.steps} steps")
        
        if not config.start_value <= config.stop_value:
            raise ValueError("Start value must be <= stop value")
        if not 0 <= config.start_value <= 450 or not 0 <= config.stop_value <= 450:
            raise ValueError("Current must be 0-450 mA")
        
        current_points = np.linspace(config.start_value, config.stop_value, config.steps)
        measurements = []
        
        self.laser_on()
        time.sleep(1.0)
        
        try:
            for i, current_ma in enumerate(current_points):
                self.set_current(current_ma)
                time.sleep(config.step_delay)
                
                start_time = time.time()
                while time.time() - start_time < config.stabilization_timeout:
                    measurement = self.measure_all()
                    if measurement.temperature_stable:
                        break
                    time.sleep(0.5)
                else:
                    measurement = self.measure_all()
                
                measurements.append(measurement)
                print(f"Step {i+1}/{config.steps}: I={current_ma:.1f}mA -> λ={measurement.wavelength_nm:.3f}nm, P={measurement.estimated_power_mw:.2f}mW")
                
        finally:
            self.set_current(150.0)  # Safe operating current
        
        df = pd.DataFrame([m.to_dict() for m in measurements])
        df['unit_id'] = 'DFB_LASER'
        df['sweep_type'] = 'current'
        df['step_number'] = range(1, len(df) + 1)
        
        df['wavelength_shift_nm'] = df['wavelength_nm'] - df['wavelength_nm'].iloc[0]
        df['power_efficiency_mw_per_ma'] = df['estimated_power_mw'] / df['current_ma']
        df['temp_error_c'] = df['temperature_actual_c'] - df['temperature_setpoint_c']
        
        return df

    def temperature_sweep(self, config: DFBSweepConfig) -> pd.DataFrame:
        """
        Perform temperature sweep with comprehensive data collection
        
        Returns:
            DataFrame ready for recorder.record_complete_dataset()
        """
        if config.parameter != 'temperature':
            raise ValueError("Use temperature_sweep for temperature parameter sweeps")
            
        print(f"Starting DFB temperature sweep: {config.start_value}°C to {config.stop_value}°C, {config.steps} steps")
        
        if not 15 <= config.start_value <= 35 or not 15 <= config.stop_value <= 35:
            raise ValueError("Temperature must be 15-35°C")
        
        temp_points = np.linspace(config.start_value, config.stop_value, config.steps)
        measurements = []
        
        self.laser_on()
        time.sleep(1.0)
        
        try:
            for i, temp_c in enumerate(temp_points):
                self.set_temperature(temp_c)
                print(f"Step {i+1}/{config.steps}: Setting T={temp_c:.2f}°C, waiting for stabilization...")
                
                if not self.wait_temperature_stable(
                    tolerance=config.stabilization_tolerance,
                    timeout=config.stabilization_timeout
                ):
                    print(f"  Warning: Temperature may not be fully stable")
                
                time.sleep(config.step_delay)
                measurement = self.measure_all()
                measurements.append(measurement)
                
                print(f"  Result: T={measurement.temperature_actual_c:.2f}°C -> λ={measurement.wavelength_nm:.3f}nm, P={measurement.estimated_power_mw:.2f}mW")
                
        finally:
            self.set_temperature(25.0)  # Safe operating temperature
        
        df = pd.DataFrame([m.to_dict() for m in measurements])
        df['unit_id'] = 'DFB_LASER'
        df['sweep_type'] = 'temperature'
        df['step_number'] = range(1, len(df) + 1)
        
        df['wavelength_shift_nm'] = df['wavelength_nm'] - df['wavelength_nm'].iloc[0]
        df['temp_tuning_nm_per_c'] = np.gradient(df['wavelength_nm']) / np.gradient(df['temperature_actual_c'])
        df['temp_error_c'] = df['temperature_actual_c'] - df['temperature_setpoint_c']
        
        return df

    def wavelength_characterization(self, current_range=(100, 400), current_steps=20,
                                   temp_range=(20, 30), temp_steps=6) -> pd.DataFrame:
        """
        Complete wavelength characterization across current and temperature
        
        Returns:
            Combined DataFrame ready for recorder
        """
        print("Starting complete DFB wavelength characterization")
        
        current_config = DFBSweepConfig(
            parameter='current',
            start_value=current_range[0],
            stop_value=current_range[1],
            steps=current_steps,
            step_delay=0.5,
            stabilization_timeout=10.0
        )
        
        self.set_temperature(25.0)  # Middle of range
        self.wait_temperature_stable(timeout=30)
        
        current_sweep_data = self.current_sweep(current_config)
        time.sleep(2.0)  # Brief pause between sweeps
        
        temp_config = DFBSweepConfig(
            parameter='temperature',
            start_value=temp_range[0],
            stop_value=temp_range[1],
            steps=temp_steps,
            step_delay=2.0,
            stabilization_timeout=45.0,
            stabilization_tolerance=0.1
        )
        
        self.set_current(200.0)  # Middle of range
        time.sleep(1.0)
        
        temp_sweep_data = self.temperature_sweep(temp_config)
        
        combined_df = pd.concat([current_sweep_data, temp_sweep_data], ignore_index=True)
        combined_df['characterization_type'] = 'wavelength_complete'
        
        return combined_df

    def power_vs_current_characterization(self, current_range=(50, 450), steps=25) -> pd.DataFrame:
        """
        Characterize power vs current relationship
        
        Returns:
            DataFrame ready for recorder
        """
        print("Starting DFB power vs current characterization")
        
        config = DFBSweepConfig(
            parameter='current',
            start_value=current_range[0],
            stop_value=current_range[1],
            steps=steps,
            step_delay=0.5,
            stabilization_timeout=10.0
        )
        
        self.set_temperature(25.0)
        self.wait_temperature_stable(timeout=30)
        
        power_data = self.current_sweep(config)
        power_data['characterization_type'] = 'power_vs_current'
        
        threshold_current = 15.0  # From specs
        above_threshold = power_data['current_ma'] > threshold_current
        
        if above_threshold.any():
            linear_region = power_data[above_threshold]
            if len(linear_region) > 3:
                slope_eff = np.polyfit(linear_region['current_ma'], linear_region['estimated_power_mw'], 1)[0]
                power_data['calculated_slope_efficiency_mw_per_ma'] = slope_eff
        
        return power_data

    def get_recorder_ready_data(self, measurements: List[DFBMeasurement] = None) -> pd.DataFrame:
        """
        Convert measurements to recorder-ready DataFrame format
        
        Args:
            measurements: Optional list of measurements
            
        Returns:
            DataFrame formatted for recorder.record_complete_dataset()
        """
        if measurements is None:
            measurement = self.measure_all()
            measurements = [measurement]
            
        df = pd.DataFrame([m.to_dict() for m in measurements])
        df['unit_id'] = 'DFB_LASER'
        
        df['wavelength_shift_nm'] = df['wavelength_nm'] - df['wavelength_nm'].iloc[0]
        df['power_efficiency_mw_per_ma'] = df['estimated_power_mw'] / df['current_ma']
        df['temp_error_c'] = df['temperature_actual_c'] - df['temperature_setpoint_c']
        df['measurement_index'] = range(len(df))
        
        return df


