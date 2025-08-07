import pyvisa
import time
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
import logging

@dataclass
class SMUMeasurement:
    """Single SMU measurement data point"""
    timestamp: str
    set_voltage: float
    set_current: float
    measured_voltage: float
    measured_current: float
    measured_power: float
    measured_resistance: float
    compliance_voltage: bool
    compliance_current: bool
    output_enabled: bool
    source_mode: str
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class SMUSweepConfig:
    """Configuration for SMU sweep operations"""
    start_value: float
    stop_value: float
    steps: int
    step_delay: float = 0.01
    compliance_limit: float = 10.0
    auto_range: bool = True
    measure_both: bool = True
    log_scale: bool = False

class AimTTi_SMU4000:
    def __init__(self, resource_address: str, unit_id: str = "SMU1"):
        self.resource_address = resource_address
        self.unit_id = unit_id
        self.rm = pyvisa.ResourceManager()
        self.instrument = self.rm.open_resource(resource_address)
        self.instrument.read_termination = '\n'
        self.instrument.write_termination = '\n'
        self.instrument.timeout = 10000  # 10 second timeout
        
        self.current_mode = "UNKNOWN"
        self.output_enabled = False
        self.last_measurement = None
        self.measurement_history: List[SMUMeasurement] = []
        
        self.device_info = self._get_device_info()
        
        self.reset()
        self.enable_output(False)

    def _get_device_info(self) -> Dict[str, str]:
        try:
            idn_parts = self.get_idn().split(',')
            return {
                'manufacturer': idn_parts[0].strip() if len(idn_parts) > 0 else 'Unknown',
                'model': idn_parts[1].strip() if len(idn_parts) > 1 else 'Unknown',
                'serial': idn_parts[2].strip() if len(idn_parts) > 2 else 'Unknown',
                'firmware': idn_parts[3].strip() if len(idn_parts) > 3 else 'Unknown',
                'resource_address': self.resource_address,
                'unit_id': self.unit_id
            }
        except Exception as e:
            return {'unit_id': self.unit_id, 'error': str(e)}

    def get_idn(self) -> str:
        return self.instrument.query("*IDN?")

    def reset(self):
        self.instrument.write("*RST")
        time.sleep(0.5)
        self.current_mode = "UNKNOWN"
        self.output_enabled = False

    def get_errors(self) -> List[str]:
        errors = []
        try:
            while True:
                error = self.instrument.query("SYST:ERR?").strip()
                if "No error" in error or error.startswith("0,"):
                    break
                errors.append(error)
        except:
            pass
        return errors

    def clear_errors(self):
        self.instrument.write("*CLS")

    def set_mode_source_current(self):
        self.instrument.write("SYST:FUNC:MODE SOURCECURR")
        self.current_mode = "CURRENT"
        time.sleep(0.1)

    def set_mode_source_voltage(self):
        self.instrument.write("SYST:FUNC:MODE SOURCEVOLT")
        self.current_mode = "VOLTAGE" 
        time.sleep(0.1)

    def get_source_mode(self) -> str:
        try:
            mode = self.instrument.query("SYST:FUNC:MODE?").strip()
            self.current_mode = mode
            return mode
        except:
            return self.current_mode

    def set_source_current(self, current: float):
        self.instrument.write(f"SOUR:CURR:LEV {current:.6f}")
        
    def get_source_current(self) -> float:
        return float(self.instrument.query("SOUR:CURR:LEV?"))
        
    def set_current_range(self, range_value: float):
        self.instrument.write(f"SOUR:CURR:RANG {range_value:.6f}")
        
    def set_current_auto_range(self, enable: bool):
        state = "ON" if enable else "OFF"
        self.instrument.write(f"SOUR:CURR:RANG:AUTO {state}")

    def set_source_voltage(self, voltage: float):
        self.instrument.write(f"SOUR:VOLT:LEV {voltage:.6f}")
        
    def get_source_voltage(self) -> float:
        return float(self.instrument.query("SOUR:VOLT:LEV?"))
        
    def set_voltage_range(self, range_value: float):
        self.instrument.write(f"SOUR:VOLT:RANG {range_value:.6f}")
        
    def set_voltage_auto_range(self, enable: bool):
        state = "ON" if enable else "OFF"
        self.instrument.write(f"SOUR:VOLT:RANG:AUTO {state}")

    def set_voltage_limit(self, voltage_limit: float):
        self.instrument.write(f"SOUR:CURR:VOLT:LIM {voltage_limit:.4f}")

    def get_voltage_limit(self) -> float:
        return float(self.instrument.query("SOUR:CURR:VOLT:LIM?"))
        
    def set_current_limit(self, current_limit: float):
        self.instrument.write(f"SOUR:VOLT:CURR:LIM {current_limit:.6f}")

    def get_current_limit(self) -> float:
        return float(self.instrument.query("SOUR:VOLT:CURR:LIM?"))

    def enable_output(self, enable: bool):
        state = "ON" if enable else "OFF"
        self.instrument.write(f"OUTP:STAT {state}")
        self.output_enabled = enable
        time.sleep(0.1)  # Allow settling

    def get_output_state(self) -> bool:
        """Get output enable state"""
        try:
            state = self.instrument.query("OUTP:STAT?").strip()
            self.output_enabled = state == "1" or state.upper() == "ON"
            return self.output_enabled
        except:
            return self.output_enabled

    def measure_voltage(self) -> float:
        """Measure voltage"""
        return float(self.instrument.query("MEAS:VOLT?"))
        
    def measure_current(self) -> float:
        """Measure current"""
        return float(self.instrument.query("MEAS:CURR?"))

    def measure_power(self) -> float:
        """Measure power (V * I)"""
        voltage = self.measure_voltage()
        current = self.measure_current()
        return voltage * current

    def measure_resistance(self) -> float:
        """Measure resistance (V / I)"""
        voltage = self.measure_voltage()
        current = self.measure_current()
        if abs(current) < 1e-12:  # Avoid division by zero
            return float('inf')
        return voltage / current

    def measure_all(self) -> SMUMeasurement:
        """Take comprehensive measurement"""
        timestamp = datetime.now().isoformat()
        
        if self.current_mode == "CURRENT":
            set_current = self.get_source_current()
            set_voltage = 0.0
        elif self.current_mode == "VOLTAGE":
            set_voltage = self.get_source_voltage()
            set_current = 0.0
        else:
            set_voltage = set_current = 0.0

        measured_voltage = self.measure_voltage()
        measured_current = self.measure_current()
        measured_power = measured_voltage * measured_current
        
        if abs(measured_current) < 1e-12:
            measured_resistance = float('inf')
        else:
            measured_resistance = measured_voltage / measured_current

        compliance_voltage = False
        compliance_current = False
        measurement = SMUMeasurement(
            timestamp=timestamp,
            set_voltage=set_voltage,
            set_current=set_current,
            measured_voltage=measured_voltage,
            measured_current=measured_current,
            measured_power=measured_power,
            measured_resistance=measured_resistance,
            compliance_voltage=compliance_voltage,
            compliance_current=compliance_current,
            output_enabled=self.get_output_state(),
            source_mode=self.get_source_mode()
        )
        
        self.last_measurement = measurement
        self.measurement_history.append(measurement)
        
        return measurement

    def voltage_sweep(self, config: SMUSweepConfig) -> pd.DataFrame:
        
        self.set_mode_source_voltage()
        self.set_current_limit(config.compliance_limit)
        
        if config.log_scale:
            if config.start_value <= 0 or config.stop_value <= 0:
                raise ValueError("Log scale requires positive start and stop values")
            sweep_points = np.logspace(np.log10(config.start_value), np.log10(config.stop_value), config.steps)
        else:
            sweep_points = np.linspace(config.start_value, config.stop_value, config.steps)
        
        measurements = []
        self.enable_output(True)
        
        try:
            for i, voltage in enumerate(sweep_points):
                self.set_source_voltage(voltage)
                time.sleep(config.step_delay)
                
                measurement = self.measure_all()
                measurements.append(measurement)
                
        finally:
            self.enable_output(False)
        
        df = pd.DataFrame([m.to_dict() for m in measurements])
        df['unit_id'] = self.unit_id
        df['sweep_type'] = 'voltage'
        df['step_number'] = range(1, len(df) + 1)
        
        return df

    def current_sweep(self, config: SMUSweepConfig) -> pd.DataFrame:
        
        self.set_mode_source_current()
        self.set_voltage_limit(config.compliance_limit)
        
        if config.log_scale:
            if config.start_value <= 0 or config.stop_value <= 0:
                raise ValueError("Log scale requires positive start and stop values")
            sweep_points = np.logspace(np.log10(config.start_value), np.log10(config.stop_value), config.steps)
        else:
            sweep_points = np.linspace(config.start_value, config.stop_value, config.steps)
        
        measurements = []
        self.enable_output(True)
        
        try:
            for i, current in enumerate(sweep_points):
                self.set_source_current(current)
                time.sleep(config.step_delay)
                
                measurement = self.measure_all()
                measurements.append(measurement)
                
        finally:
            self.enable_output(False)
        
        df = pd.DataFrame([m.to_dict() for m in measurements])
        df['unit_id'] = self.unit_id
        df['sweep_type'] = 'current'
        df['step_number'] = range(1, len(df) + 1)
        
        return df

    def iv_characterization(self, voltage_range: Tuple[float, float], voltage_steps: int, 
                           current_range: Tuple[float, float], current_steps: int,
                           step_delay: float = 0.02) -> pd.DataFrame:
        
        v_config = SMUSweepConfig(
            start_value=voltage_range[0],
            stop_value=voltage_range[1], 
            steps=voltage_steps,
            step_delay=step_delay,
            compliance_limit=max(abs(current_range[0]), abs(current_range[1]))
        )
        
        i_config = SMUSweepConfig(
            start_value=current_range[0],
            stop_value=current_range[1],
            steps=current_steps,
            step_delay=step_delay,
            compliance_limit=max(abs(voltage_range[0]), abs(voltage_range[1]))
        )
        
        v_sweep_data = self.voltage_sweep(v_config)
        time.sleep(1.0)  # Brief pause between sweeps
        i_sweep_data = self.current_sweep(i_config)
        
        combined_df = pd.concat([v_sweep_data, i_sweep_data], ignore_index=True)
        combined_df['characterization_type'] = 'iv_complete'
        
        return combined_df

    def get_recorder_ready_data(self, measurements: List[SMUMeasurement] = None) -> pd.DataFrame:
        """
        Convert measurements to recorder-ready DataFrame format
        
        Args:
            measurements: Optional list of measurements, uses history if None
            
        Returns:
            DataFrame formatted for recorder.record_complete_dataset()
        """
        if measurements is None:
            measurements = self.measurement_history
            
        if not measurements:
            return pd.DataFrame()
        
        df = pd.DataFrame([m.to_dict() for m in measurements])
        df['unit_id'] = self.unit_id
        
        df['power_mw'] = df['measured_power'] * 1000
        df['current_ma'] = df['measured_current'] * 1000
        df['resistance_kohm'] = df['measured_resistance'] / 1000
        
        df['measurement_index'] = range(len(df))
        
        return df

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive SMU status"""
        try:
            errors = self.get_errors()
            return {
                'unit_id': self.unit_id,
                'device_info': self.device_info,
                'output_enabled': self.get_output_state(),
                'source_mode': self.get_source_mode(),
                'source_voltage_v': self.get_source_voltage() if self.current_mode == "VOLTAGE" else None,
                'source_current_a': self.get_source_current() if self.current_mode == "CURRENT" else None,
                'voltage_limit_v': self.get_voltage_limit() if self.current_mode == "CURRENT" else None,
                'current_limit_a': self.get_current_limit() if self.current_mode == "VOLTAGE" else None,
                'last_measurement': self.last_measurement.to_dict() if self.last_measurement else None,
                'total_measurements': len(self.measurement_history),
                'errors': errors,
                'connected': True
            }
        except Exception as e:
            return {
                'unit_id': self.unit_id,
                'error': str(e),
                'connected': False
            }

    def clear_measurement_history(self):
        """Clear measurement history"""
        self.measurement_history.clear()
        self.last_measurement = None

    def disconnect(self):
        """Safely disconnect SMU"""
        try:
            self.enable_output(False)
            time.sleep(0.1)
            self.instrument.close()
            self.rm.close()
            print(f"{self.unit_id} disconnected safely")
        except Exception as e:
            print(f"Error disconnecting {self.unit_id}: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

