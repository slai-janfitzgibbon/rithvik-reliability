import pyvisa
import time
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass, asdict
import logging

@dataclass
class PSUChannelMeasurement:
    timestamp: str
    channel: int
    set_voltage: float
    set_current_limit: float
    measured_voltage: float
    measured_current: float
    measured_power: float
    output_enabled: bool
    in_cv_mode: bool
    in_cc_mode: bool
    over_voltage_protection: bool
    over_current_protection: bool
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class PSUSweepConfig:
    channel: int
    start_voltage: float
    stop_voltage: float
    steps: int
    current_limit: float
    step_delay: float = 0.1
    measure_settling_time: float = 0.05
    log_scale: bool = False
    auto_range: bool = True

class TTi_QL355TP:
    def __init__(self, resource_address: str, unit_id: str = "PSU1"):
        self.resource_address = resource_address
        self.unit_id = unit_id
        self.rm = pyvisa.ResourceManager()
        self.instrument = self.rm.open_resource(resource_address)
        self.instrument.read_termination = '\n'
        self.instrument.write_termination = '\n'
        self.instrument.timeout = 5000  # 5 second timeout
        
        self.channel_states = {1: {'enabled': False, 'voltage': 0.0, 'current_limit': 0.0},
                              2: {'enabled': False, 'voltage': 0.0, 'current_limit': 0.0}}
        self.measurement_history: List[PSUChannelMeasurement] = []
        self.last_measurements = {1: None, 2: None}
        
        self.device_info = self._get_device_info()
        
        self.reset()

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
        self.enable_output(1, False)
        self.enable_output(2, False)
        time.sleep(0.1)
        
        # Reset instrument
        self.instrument.write("*RST")
        time.sleep(0.5)
        
        # Update state tracking
        for channel in [1, 2]:
            self.channel_states[channel] = {'enabled': False, 'voltage': 0.0, 'current_limit': 0.0}

    def get_errors(self) -> List[str]:
        """Get any system errors"""
        errors = []
        try:
            # Try to get error queue (if supported)
            while True:
                try:
                    error = self.instrument.query("SYST:ERR?").strip()
                    if "No error" in error or error.startswith("0,"):
                        break
                    errors.append(error)
                except:
                    break
        except:
            pass
        return errors

    def _validate_channel(self, channel: int):
        """Validate channel number"""
        if channel not in [1, 2]:
            raise ValueError(f"Channel must be 1 or 2, got {channel}")

    # Voltage Control
    def set_voltage(self, channel: int, voltage: float):
        """Set channel voltage"""
        self._validate_channel(channel)
        self.instrument.write(f"V{channel} {voltage:.4f}")
        self.channel_states[channel]['voltage'] = voltage
        time.sleep(0.01)  # Brief settling

    def get_set_voltage(self, channel: int) -> float:
        """Get voltage setting for channel"""
        self._validate_channel(channel)
        try:
            response = self.instrument.query(f"V{channel}?")
            voltage = float(response)
            self.channel_states[channel]['voltage'] = voltage
            return voltage
        except:
            return self.channel_states[channel]['voltage']

    def get_output_voltage(self, channel: int) -> float:
        """Get actual output voltage"""
        self._validate_channel(channel)
        response = self.instrument.query(f"V{channel}O?")
        return float(response)

    # Current Control
    def set_current_limit(self, channel: int, current: float):
        """Set channel current limit"""
        self._validate_channel(channel)
        self.instrument.write(f"I{channel} {current:.4f}")
        self.channel_states[channel]['current_limit'] = current
        time.sleep(0.01)

    def get_set_current_limit(self, channel: int) -> float:
        """Get current limit setting"""
        self._validate_channel(channel)
        try:
            response = self.instrument.query(f"I{channel}?")
            current = float(response)
            self.channel_states[channel]['current_limit'] = current
            return current
        except:
            return self.channel_states[channel]['current_limit']

    def get_output_current(self, channel: int) -> float:
        """Get actual output current"""
        self._validate_channel(channel)
        response = self.instrument.query(f"I{channel}O?")
        return float(response)

    # Output Control
    def enable_output(self, channel: int, enable: bool):
        """Enable/disable channel output"""
        self._validate_channel(channel)
        state = 1 if enable else 0
        self.instrument.write(f"OP{channel} {state}")
        self.channel_states[channel]['enabled'] = enable
        time.sleep(0.1)  # Allow settling

    def get_output_state(self, channel: int) -> bool:
        """Get output enable state"""
        self._validate_channel(channel)
        try:
            response = self.instrument.query(f"OP{channel}?")
            enabled = int(response) == 1
            self.channel_states[channel]['enabled'] = enabled
            return enabled
        except:
            return self.channel_states[channel]['enabled']

    def enable_all_outputs(self, enable: bool):
        """Enable/disable all outputs"""
        for channel in [1, 2]:
            self.enable_output(channel, enable)

    # Advanced Measurement Functions
    def measure_power(self, channel: int) -> float:
        """Measure channel power (V * I)"""
        voltage = self.get_output_voltage(channel)
        current = self.get_output_current(channel)
        return voltage * current

    def get_channel_mode(self, channel: int) -> Dict[str, bool]:
        """Get channel operating mode (CV/CC)"""
        self._validate_channel(channel)
        # This would need actual instrument queries for real implementation
        # For now, estimate based on measurements
        voltage = self.get_output_voltage(channel)
        current = self.get_output_current(channel)
        set_voltage = self.get_set_voltage(channel)
        current_limit = self.get_set_current_limit(channel)
        
        # Simple heuristic - if current is at limit, likely in CC mode
        in_cc_mode = abs(current - current_limit) < 0.01
        in_cv_mode = not in_cc_mode
        
        return {
            'cv_mode': in_cv_mode,
            'cc_mode': in_cc_mode,
            'voltage_regulation': in_cv_mode,
            'current_regulation': in_cc_mode
        }

    def measure_channel_all(self, channel: int) -> PSUChannelMeasurement:
        """Take comprehensive measurement for one channel"""
        self._validate_channel(channel)
        timestamp = datetime.now().isoformat()
        
        # Get settings
        set_voltage = self.get_set_voltage(channel)
        set_current_limit = self.get_set_current_limit(channel)
        
        # Get measurements
        measured_voltage = self.get_output_voltage(channel)
        measured_current = self.get_output_current(channel)
        measured_power = measured_voltage * measured_current
        
        # Get states
        output_enabled = self.get_output_state(channel)
        channel_mode = self.get_channel_mode(channel)
        
        # Create measurement
        measurement = PSUChannelMeasurement(
            timestamp=timestamp,
            channel=channel,
            set_voltage=set_voltage,
            set_current_limit=set_current_limit,
            measured_voltage=measured_voltage,
            measured_current=measured_current,
            measured_power=measured_power,
            output_enabled=output_enabled,
            in_cv_mode=channel_mode['cv_mode'],
            in_cc_mode=channel_mode['cc_mode'],
            over_voltage_protection=False,  # Would need instrument query
            over_current_protection=False   # Would need instrument query
        )
        
        self.last_measurements[channel] = measurement
        self.measurement_history.append(measurement)
        
        return measurement

    def measure_all_channels(self) -> Dict[int, PSUChannelMeasurement]:
        """Take measurements for all channels"""
        measurements = {}
        for channel in [1, 2]:
            measurements[channel] = self.measure_channel_all(channel)
        return measurements

    # Sweep Operations
    def voltage_sweep(self, config: PSUSweepConfig) -> pd.DataFrame:
        """
        Perform voltage sweep on specified channel
        
        Returns:
            DataFrame ready for recorder.record_complete_dataset()
        """
        print(f"Starting voltage sweep on {self.unit_id} CH{config.channel}: {config.start_voltage}V to {config.stop_voltage}V, {config.steps} steps")
        
        self._validate_channel(config.channel)
        
        # Set current limit
        self.set_current_limit(config.channel, config.current_limit)
        
        # Generate sweep points
        if config.log_scale:
            if config.start_voltage <= 0 or config.stop_voltage <= 0:
                raise ValueError("Log scale requires positive start and stop voltages")
            sweep_points = np.logspace(np.log10(config.start_voltage), np.log10(config.stop_voltage), config.steps)
        else:
            sweep_points = np.linspace(config.start_voltage, config.stop_voltage, config.steps)
        
        measurements = []
        self.enable_output(config.channel, True)
        
        try:
            for i, voltage in enumerate(sweep_points):
                self.set_voltage(config.channel, voltage)
                time.sleep(config.step_delay)
                
                # Allow extra settling for measurement
                if config.measure_settling_time > 0:
                    time.sleep(config.measure_settling_time)
                
                measurement = self.measure_channel_all(config.channel)
                measurements.append(measurement)
                
                print(f"Step {i+1}/{config.steps}: V={voltage:.4f}V -> I={measurement.measured_current*1000:.3f}mA, P={measurement.measured_power*1000:.3f}mW")
                
        finally:
            self.enable_output(config.channel, False)
        
        # Convert to DataFrame
        df = pd.DataFrame([m.to_dict() for m in measurements])
        df['unit_id'] = self.unit_id
        df['sweep_type'] = 'voltage'
        df['step_number'] = range(1, len(df) + 1)
        
        return df

    def load_regulation_test(self, channel: int, voltage: float, 
                           current_steps: List[float], 
                           step_delay: float = 0.2) -> pd.DataFrame:
        """
        Test load regulation by varying current draw
        
        Args:
            channel: PSU channel to test
            voltage: Fixed voltage to maintain
            current_steps: List of current limits to test
            step_delay: Delay between steps
            
        Returns:
            DataFrame ready for recorder
        """
        print(f"Starting load regulation test on {self.unit_id} CH{channel} at {voltage}V")
        
        self._validate_channel(channel)
        self.set_voltage(channel, voltage)
        
        measurements = []
        self.enable_output(channel, True)
        
        try:
            for i, current_limit in enumerate(current_steps):
                self.set_current_limit(channel, current_limit)
                time.sleep(step_delay)
                
                measurement = self.measure_channel_all(channel)
                measurements.append(measurement)
                
                print(f"Step {i+1}/{len(current_steps)}: Ilim={current_limit*1000:.1f}mA -> V={measurement.measured_voltage:.4f}V, I={measurement.measured_current*1000:.3f}mA")
                
        finally:
            self.enable_output(channel, False)
        
        # Convert to DataFrame
        df = pd.DataFrame([m.to_dict() for m in measurements])
        df['unit_id'] = self.unit_id
        df['test_type'] = 'load_regulation'
        df['step_number'] = range(1, len(df) + 1)
        
        return df

    def dual_channel_tracking_test(self, voltage_steps: List[float],
                                  current_limit: float = 1.0,
                                  step_delay: float = 0.2) -> pd.DataFrame:
        """
        Test dual channel tracking by setting both channels to same voltage
        
        Returns:
            DataFrame with measurements from both channels
        """
        print(f"Starting dual channel tracking test on {self.unit_id}")
        
        measurements = []
        
        # Set current limits for both channels
        for channel in [1, 2]:
            self.set_current_limit(channel, current_limit)
        
        # Enable both outputs
        self.enable_all_outputs(True)
        
        try:
            for i, voltage in enumerate(voltage_steps):
                # Set both channels to same voltage
                self.set_voltage(1, voltage)
                self.set_voltage(2, voltage)
                time.sleep(step_delay)
                
                # Measure both channels
                ch1_measurement = self.measure_channel_all(1)
                ch2_measurement = self.measure_channel_all(2)
                
                measurements.extend([ch1_measurement, ch2_measurement])
                
                print(f"Step {i+1}/{len(voltage_steps)}: V={voltage:.3f}V -> CH1: {ch1_measurement.measured_voltage:.4f}V, CH2: {ch2_measurement.measured_voltage:.4f}V")
                
        finally:
            self.enable_all_outputs(False)
        
        # Convert to DataFrame
        df = pd.DataFrame([m.to_dict() for m in measurements])
        df['unit_id'] = self.unit_id
        df['test_type'] = 'dual_channel_tracking'
        df['step_number'] = [i//2 + 1 for i in range(len(df))]  # Each step has 2 measurements
        
        return df

    def get_recorder_ready_data(self, measurements: List[PSUChannelMeasurement] = None) -> pd.DataFrame:
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
        
        # Add derived columns useful for analysis
        df['power_mw'] = df['measured_power'] * 1000
        df['current_ma'] = df['measured_current'] * 1000
        df['voltage_error_mv'] = (df['measured_voltage'] - df['set_voltage']) * 1000
        df['load_resistance_ohm'] = np.where(df['measured_current'] > 1e-6, 
                                           df['measured_voltage'] / df['measured_current'], 
                                           np.inf)
        
        # Add time-based indexing
        df['measurement_index'] = range(len(df))
        
        return df

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive PSU status"""
        try:
            errors = self.get_errors()
            
            # Get status for both channels
            channels_status = {}
            for channel in [1, 2]:
                measurement = self.measure_channel_all(channel)
                channels_status[f'channel_{channel}'] = {
                    'set_voltage_v': measurement.set_voltage,
                    'set_current_limit_a': measurement.set_current_limit,
                    'measured_voltage_v': measurement.measured_voltage,
                    'measured_current_a': measurement.measured_current,
                    'measured_power_w': measurement.measured_power,
                    'output_enabled': measurement.output_enabled,
                    'cv_mode': measurement.in_cv_mode,
                    'cc_mode': measurement.in_cc_mode
                }
            
            return {
                'unit_id': self.unit_id,
                'device_info': self.device_info,
                'channels': channels_status,
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
        self.last_measurements = {1: None, 2: None}

    def disconnect(self):
        """Safely disconnect PSU"""
        try:
            # Disable all outputs for safety
            self.enable_all_outputs(False)
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

TTi_QL355T = TTi_QL355TP