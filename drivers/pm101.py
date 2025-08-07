import os
import sys
import time
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from ctypes import cdll, byref, create_string_buffer, c_bool, c_int16, c_double, c_char_p

@dataclass
class PowerMeterMeasurement:
    """Single power meter measurement data point"""
    timestamp: str
    power_w: float
    power_mw: float
    power_dbm: float
    wavelength_nm: float
    unit_id: str
    calibration_msg: str
    connection_method: str
    auto_range_enabled: bool
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class PowerMeterMonitorConfig:
    """Configuration for power meter monitoring operations"""
    duration_s: float
    sample_rate_hz: float = 10.0
    wavelength_nm: float = 1310.0
    power_unit: str = "W"
    auto_range: bool = True
    statistical_analysis: bool = True

sys.path.insert(0, os.path.dirname(__file__))

try:
    from TLPMX import TLPMX, TLPM_DEFAULT_CHANNEL
    TLPMX_AVAILABLE = True
except ImportError:
    TLPMX_AVAILABLE = False

try:
    import pyvisa
    PYVISA_AVAILABLE = True
except ImportError:
    PYVISA_AVAILABLE = False

class ThorlabsPowerMeter:
    def __init__(self, resource_address: str, use_tlpmx: bool = True, unit_id: str = 'PM1'):
        self.unit_id = unit_id
        self.resource_address = resource_address
        self.is_open = False
        self.last_cal_msg = ""
        self.wavelength = 1310.0
        self.use_tlpmx = use_tlpmx and TLPMX_AVAILABLE
        
        if self.use_tlpmx:
            self._init_tlpmx()
        elif PYVISA_AVAILABLE:
            self._init_pyvisa()
        else:
            raise RuntimeError("Neither TLPMX nor PyVISA is available")

    def _init_tlpmx(self):
        try:
            self.instrument_handle = TLPMX()
            resource_name_c = self.resource_address.encode('ascii')
            
            self.instrument_handle.open(resource_name_c, c_bool(True), c_bool(True))
            self.is_open = True
            
            self.instrument_handle.setPowerUnit(c_int16(0), TLPM_DEFAULT_CHANNEL)
            self.instrument_handle.setPowerAutoRange(c_int16(1), TLPM_DEFAULT_CHANNEL)
            
            cmsg = create_string_buffer(256)
            self.instrument_handle.getCalibrationMsg(cmsg, TLPM_DEFAULT_CHANNEL)
            self.last_cal_msg = cmsg.value.decode('utf-8')
            
        except Exception as e:
            if self.is_open:
                self.disconnect()
            raise ConnectionError(f"Could not connect via TLPMX: {e}")

    def _init_pyvisa(self):
        try:
            self.rm = pyvisa.ResourceManager()
            self.instrument = self.rm.open_resource(self.resource_address)
            self.instrument.read_termination = '\n'
            self.instrument.write_termination = '\n'
            self.is_open = True
            
        except Exception as e:
            raise ConnectionError(f"Could not connect via PyVISA: {e}")

    def get_idn(self) -> str:
        if not self.is_open:
            return "Device not connected"
            
        try:
            if self.use_tlpmx:
                model_name = create_string_buffer(256)
                serial_number = create_string_buffer(256)
                manufacturer = create_string_buffer(256)
                dummy_bool = c_bool(False)
                
                self.instrument_handle.getDevInfo(model_name, serial_number, manufacturer, byref(dummy_bool))
                
                return (f"Manufacturer: {manufacturer.value.decode('utf-8')}, "
                       f"Model: {model_name.value.decode('utf-8')}, "
                       f"S/N: {serial_number.value.decode('utf-8')}")
            else:
                return self.instrument.query("SYST:SENS:IDN?")
                
        except Exception as e:
            return f"Error retrieving ID: {e}"

    def set_wavelength(self, wavelength_nm: float):
        if not self.is_open:
            return
            
        try:
            self.wavelength = float(wavelength_nm)
            
            if self.use_tlpmx:
                self.instrument_handle.setWavelength(c_double(self.wavelength), TLPM_DEFAULT_CHANNEL)
            else:
                self.instrument.write(f"SENS:CORR:WAV {wavelength_nm}")
            
        except Exception as e:
            pass

    def set_power_unit(self, unit: str = "W"):
        if not self.is_open:
            return
            
        unit = unit.upper()
        if unit not in ["W", "DBM"]:
            raise ValueError("Unit must be 'W' or 'DBM'")
            
        try:
            if self.use_tlpmx:
                unit_code = 0 if unit == "W" else 1
                self.instrument_handle.setPowerUnit(c_int16(unit_code), TLPM_DEFAULT_CHANNEL)
            else:
                self.instrument.write(f"SENS:POW:UNIT {unit}")
                
        except Exception as e:
            pass

    def set_auto_range(self, enable: bool):
        if not self.is_open:
            return
            
        try:
            if self.use_tlpmx:
                self.instrument_handle.setPowerAutoRange(c_int16(1 if enable else 0), TLPM_DEFAULT_CHANNEL)
            else:
                state = "ON" if enable else "OFF"
                self.instrument.write(f"SENS:POW:RANG:AUTO {state}")
                
        except Exception as e:
            pass

    def read_power(self) -> float:
        if not self.is_open:
            return 0.0
            
        try:
            if self.use_tlpmx:
                power_c = c_double()
                self.instrument_handle.measPower(byref(power_c), TLPM_DEFAULT_CHANNEL)
                return power_c.value
            else:
                return float(self.instrument.query("MEAS:POW?"))
                
        except Exception as e:
            return 0.0

    def read_power_dbm(self) -> float:
        power_w = self.read_power()
        if power_w > 0:
            return 10 * np.log10(power_w * 1000)
        else:
            return -999.0

    def get_calibration_message(self) -> str:
        if self.use_tlpmx:
            return self.last_cal_msg
        else:
            try:
                return self.instrument.query("SYST:SENS:CAL:MESS?")
            except:
                return "Calibration message not available"

    def get_status(self) -> dict:
        power_w = self.read_power()
        return {
            'power_w': power_w,
            'power_mw': power_w * 1000,
            'power_dbm': self.read_power_dbm(),
            'wavelength_nm': self.wavelength,
            'calibration_msg': self.get_calibration_message(),
            'connection_method': 'TLPMX' if self.use_tlpmx else 'PyVISA',
            'resource_address': self.resource_address
        }

    def disconnect(self):
        if self.is_open:
            try:
                if self.use_tlpmx:
                    self.instrument_handle.close()
                else:
                    self.instrument.close()
                    self.rm.close()
                self.is_open = False
                
            except Exception as e:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def measure_all(self, unit_id: str = None) -> PowerMeterMeasurement:
        if unit_id is None:
            unit_id = getattr(self, 'unit_id', 'PM1')
            
        timestamp = datetime.now().isoformat()
        
        power_w = self.read_power()
        power_mw = power_w * 1000
        power_dbm = self.read_power_dbm()
        
        measurement = PowerMeterMeasurement(
            timestamp=timestamp,
            power_w=power_w,
            power_mw=power_mw,
            power_dbm=power_dbm,
            wavelength_nm=self.wavelength,
            unit_id=unit_id,
            calibration_msg=self.get_calibration_message(),
            connection_method='TLPMX' if self.use_tlpmx else 'PyVISA',
            auto_range_enabled=True
        )
        
        return measurement

    def continuous_monitoring(self, config: PowerMeterMonitorConfig, unit_id: str = None) -> pd.DataFrame:
        if unit_id is None:
            unit_id = getattr(self, 'unit_id', 'PM1')
        
        self.set_wavelength(config.wavelength_nm)
        self.set_power_unit(config.power_unit)
        self.set_auto_range(config.auto_range)
        
        measurements = []
        sample_interval = 1.0 / config.sample_rate_hz
        num_samples = int(config.duration_s * config.sample_rate_hz)
        
        start_time = time.time()
        
        try:
            for i in range(num_samples):
                target_time = start_time + i * sample_interval
                sleep_time = target_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
                measurement = self.measure_all(unit_id)
                measurements.append(measurement)
                
        except KeyboardInterrupt:
            pass
        
        df = pd.DataFrame([m.to_dict() for m in measurements])
        df['sample_number'] = range(1, len(df) + 1)
        
        if len(df) > 1:
            df['elapsed_time_s'] = (pd.to_datetime(df['timestamp']) - pd.to_datetime(df['timestamp'].iloc[0])).dt.total_seconds()
        else:
            df['elapsed_time_s'] = 0.0
        
        if config.statistical_analysis and len(df) > 1:
            window_size = min(10, len(df))
            df['power_w_rolling_mean'] = df['power_w'].rolling(window=window_size, center=True).mean()
            df['power_w_rolling_std'] = df['power_w'].rolling(window=window_size, center=True).std()
            df['power_stability_percent'] = (df['power_w_rolling_std'] / df['power_w_rolling_mean']) * 100
        
        df['monitoring_type'] = 'continuous'
        
        return df

    def wavelength_response_measurement(self, wavelengths: List[float], 
                                       measurements_per_wavelength: int = 10,
                                       unit_id: str = None) -> pd.DataFrame:
        if unit_id is None:
            unit_id = getattr(self, 'unit_id', 'PM1')
        
        measurements = []
        
        for wavelength in wavelengths:
            self.set_wavelength(wavelength)
            time.sleep(0.5)
            
            for i in range(measurements_per_wavelength):
                measurement = self.measure_all(unit_id)
                measurements.append(measurement)
                time.sleep(0.1)
        
        df = pd.DataFrame([m.to_dict() for m in measurements])
        df['measurement_index'] = range(len(df))
        df['test_type'] = 'wavelength_response'
        
        df['wavelength_group'] = pd.cut(df['wavelength_nm'], bins=len(wavelengths), 
                                       labels=[f"WL_{wl}nm" for wl in wavelengths])
        
        return df

    def power_stability_test(self, duration_minutes: float = 10.0, 
                           sample_rate_hz: float = 1.0,
                           unit_id: str = None) -> pd.DataFrame:
        if unit_id is None:
            unit_id = getattr(self, 'unit_id', 'PM1')
            
        config = PowerMeterMonitorConfig(
            duration_s=duration_minutes * 60,
            sample_rate_hz=sample_rate_hz,
            statistical_analysis=True
        )
        
        stability_data = self.continuous_monitoring(config, unit_id)
        stability_data['test_type'] = 'power_stability'
        
        if len(stability_data) > 10:
            power_mean = stability_data['power_w'].mean()
            power_std = stability_data['power_w'].std()
            stability_percent = (power_std / power_mean) * 100
            
            stability_data['overall_power_mean_w'] = power_mean
            stability_data['overall_power_std_w'] = power_std
            stability_data['overall_stability_percent'] = stability_percent
        
        return stability_data

    def multi_wavelength_monitoring(self, wavelengths: List[float],
                                   duration_per_wavelength_s: float = 30.0,
                                   sample_rate_hz: float = 5.0,
                                   unit_id: str = None) -> pd.DataFrame:
        if unit_id is None:
            unit_id = getattr(self, 'unit_id', 'PM1')
        
        all_measurements = []
        
        for wl in wavelengths:
            config = PowerMeterMonitorConfig(
                duration_s=duration_per_wavelength_s,
                sample_rate_hz=sample_rate_hz,
                wavelength_nm=wl,
                statistical_analysis=True
            )
            
            wl_data = self.continuous_monitoring(config, unit_id)
            wl_data['wavelength_sequence'] = wl
            all_measurements.append(wl_data)
            
            time.sleep(1.0)
        
        combined_df = pd.concat(all_measurements, ignore_index=True)
        combined_df['test_type'] = 'multi_wavelength_monitoring'
        combined_df['global_sample_number'] = range(len(combined_df))
        
        return combined_df

    def get_recorder_ready_data(self, measurements: List[PowerMeterMeasurement] = None,
                               unit_id: str = None) -> pd.DataFrame:
        if measurements is None:
            if unit_id is None:
                unit_id = getattr(self, 'unit_id', 'PM1')
            measurement = self.measure_all(unit_id)
            measurements = [measurement]
            
        df = pd.DataFrame([m.to_dict() for m in measurements])
        
        df['power_uw'] = df['power_w'] * 1e6
        df['power_nw'] = df['power_w'] * 1e9
        df['measurement_index'] = range(len(df))
        
        power_ranges = ['<1nW', '1nW-1uW', '1uW-1mW', '1mW-10mW', '10mW-100mW', '>100mW']
        power_w = df['power_w']
        df['power_range'] = pd.cut(power_w, 
                                  bins=[0, 1e-9, 1e-6, 1e-3, 10e-3, 100e-3, float('inf')],
                                  labels=power_ranges,
                                  right=False)
        
        return df

Thorlabs_PMxxx = ThorlabsPowerMeter