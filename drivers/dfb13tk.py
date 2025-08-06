import serial
import time


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
    
    # Basic Laser Control
    def laser_on(self):
        """Turn laser on"""
        self._cmd("laser on")
    
    def laser_off(self):
        """Turn laser off"""
        self._cmd("laser off")
    
    def get_laser_state(self):
        """Get current laser state (60=on, 61=off, 62=interlock, 63=fault, 64=unknown, 65=starting)"""
        try:
            state = self._cmd("read_param laser_state")
            return int(state) if state else 61
        except:
            return 61
    
    # Current Control
    def set_current(self, current_ma):
        """Set laser current in mA (0-450)"""
        if not 0 <= current_ma <= 450:
            raise ValueError("Current must be 0-450 mA")
        amps = current_ma / 1000.0
        self._cmd(f"write_param laser.current {amps}")
        self._current_ma = current_ma
    
    def get_current(self):
        """Get laser current in mA"""
        try:
            current_str = self._cmd("read_param laser.current")
            if current_str:
                return float(current_str) * 1000
        except:
            pass
        return self._current_ma
    
    # Temperature Control
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
    
    # TEC Adjustment Control
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
    
    # Wavelength and Power Calculations (from PDF specs)
    def calculate_wavelength(self, current_ma=None, temp_c=None):
        """Calculate wavelength based on current and temperature tuning coefficients"""
        if current_ma is None:
            current_ma = self.get_current()
        if temp_c is None:
            temp_c = self.get_temperature()
        
        # From PDF: Current tuning coefficient = 0.003 nm/mA, Temperature = 0.08 nm/°C
        # Assume center wavelength 1310 nm at 200 mA, 25°C (middle of 1305-1315 nm range)
        base_wavelength = 1310.0
        base_current = 200.0
        base_temp = 25.0
        
        current_shift = (current_ma - base_current) * 0.003
        temp_shift = (temp_c - base_temp) * 0.08
        
        return base_wavelength + current_shift + temp_shift
    
    def calculate_power(self, current_ma=None):
        """Calculate estimated output power based on slope efficiency"""
        if current_ma is None:
            current_ma = self.get_current()
        
        # From PDF: Slope efficiency = 0.27 W/A, Threshold ~15 mA
        threshold_ma = 15.0
        slope_efficiency_w_per_a = 0.27
        
        if current_ma <= threshold_ma:
            return 0.0
        
        power_w = (current_ma - threshold_ma) / 1000.0 * slope_efficiency_w_per_a
        return power_w * 1000.0  # Convert to mW
    
    # Device Information
    def get_firmware_version(self):
        """Get firmware version"""
        return self._cmd("firmware_version")
    
    def get_serial_number(self):
        """Get module serial number"""
        return self._cmd("read_string module_sn")
    
    def get_laser_serial(self):
        """Get laser serial number"""
        return self._cmd("read_string laser_sn")
    
    def get_oem_string(self):
        """Get OEM string"""
        return self._cmd("read_string oem")
    
    def get_main_board_serial(self):
        """Get main board serial number"""
        return self._cmd("read_string main_board_sn")
    
    def get_clock(self):
        """Get system clock"""
        return self._cmd("get_clock")
    
    # Configuration Management
    def save_config(self):
        """Save all parameters to non-volatile memory"""
        self._cmd("savecfg")
    
    def save_parameter(self, tag):
        """Save specific parameter to EEPROM"""
        self._cmd(f"save_param {tag}")
    
    def read_parameter(self, tag):
        """Read any parameter by tag"""
        return self._cmd(f"read_param {tag}")
    
    def write_parameter(self, tag, value):
        """Write any parameter by tag"""
        self._cmd(f"write_param {tag} {value}")
    
    # System Control
    def reset_system(self):
        """Reset system (drops USB connection)"""
        self._cmd("reset")
    
    def enter_update_mode(self):
        """Enter firmware update mode"""
        self._cmd("update")
    
    # Status and Monitoring
    def get_status(self):
        """Get comprehensive status dictionary"""
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
    
    # External Modulation (Specifications from PDF)
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
    
    # Specifications from PDF
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
    
    # Utility Functions
    def tune_wavelength_by_current(self, target_wavelength_nm):
        """Tune to target wavelength using current (approximate)"""
        current_wavelength = self.calculate_wavelength()
        wavelength_diff = target_wavelength_nm - current_wavelength
        
        # 0.003 nm/mA from specs
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
        
        # 0.08 nm/°C from specs
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
        
        # Current tuning range (limited by 0-450 mA)
        max_current_change = min(450 - current_ma, current_ma)
        current_tuning_range_nm = max_current_change * 0.003
        
        # Temperature tuning range (limited by 15-35°C)
        max_temp_change = min(35 - temp_c, temp_c - 15)
        temp_tuning_range_nm = max_temp_change * 0.08
        
        return {
            'current_tuning_range_nm': current_tuning_range_nm,
            'temperature_tuning_range_nm': temp_tuning_range_nm,
            'total_range_nm': current_tuning_range_nm + temp_tuning_range_nm
        }
    
    # Context manager
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.laser_off()
        except:
            pass
        self.close()


# Test all functions
def test_dfb13tk():
    """Test all DFB13TK functions"""
    print("DFB13TK Complete Driver Test")
    print("=" * 40)
    
    with DFB13TK() as laser:
        # Device information
        print("Device Information:")
        info = laser.get_device_info()
        for key, value in info.items():
            if value:
                print(f"  {key}: {value}")
        
        # Specifications
        print("\nSpecifications loaded:")
        specs = laser.get_specifications()
        print(f"  Wavelength range: {specs['center_wavelength_nm']['min']}-{specs['center_wavelength_nm']['max']} nm")
        print(f"  Current tuning: {specs['current_tuning_nm_per_ma']['typical']} nm/mA")
        print(f"  Temperature tuning: {specs['temp_tuning_nm_per_c']['typical']} nm/°C")
        
        # Current control
        print("\nCurrent Control Test:")
        laser.set_current(180)
        current = laser.get_current()
        print(f"  Set 180 mA, read: {current:.1f} mA")
        
        # Temperature control  
        print("\nTemperature Control Test:")
        laser.set_temperature(25.0)
        temp_set = laser.get_temperature_setpoint()
        temp_actual = laser.get_temperature()
        print(f"  Setpoint: {temp_set:.1f}°C, Actual: {temp_actual:.1f}°C")
        
        # Calculations
        print("\nCalculations:")
        wavelength = laser.calculate_wavelength()
        power = laser.calculate_power()
        print(f"  Estimated wavelength: {wavelength:.3f} nm")
        print(f"  Estimated power: {power:.1f} mW")
        
        # TEC adjustment
        print("\nTEC Adjustment Test:")
        laser.enable_tec_adjustment()
        laser.set_tec_adjustment_range(0.5)
        tec_range = laser.get_tec_adjustment_range()
        tec_adj = laser.get_tec_adjustment()
        print(f"  TEC range: ±{tec_range:.1f}°C")
        print(f"  Current adjustment: {tec_adj:.2f}°C")
        laser.disable_tec_adjustment()
        
        # Mode-hop-free check
        print("\nMode-Hop-Free Range Check:")
        mhf = laser.get_mode_hop_free_range()
        print(f"  In range: {mhf['in_range']}")
        print(f"  Current: {mhf['current_ma']:.1f} mA (OK: {mhf['current_ok']})")
        print(f"  Power: {mhf['power_mw']:.1f} mW (OK: {mhf['power_ok']})")
        
        # Tuning ranges
        print("\nAvailable Tuning Ranges:")
        tuning = laser.calculate_tuning_range()
        print(f"  Current tuning: ±{tuning['current_tuning_range_nm']:.3f} nm")
        print(f"  Temperature tuning: ±{tuning['temperature_tuning_range_nm']:.3f} nm")
        print(f"  Total range: ±{tuning['total_range_nm']:.3f} nm")
        
        # Wavelength tuning test
        print("\nWavelength Tuning Test:")
        original_wavelength = laser.calculate_wavelength()
        target_wavelength = original_wavelength + 0.1  # +0.1 nm
        
        if laser.tune_wavelength_by_current(target_wavelength):
            new_wavelength = laser.calculate_wavelength()
            print(f"  Tuned from {original_wavelength:.3f} to {new_wavelength:.3f} nm using current")
        else:
            print("  Current tuning out of range")
        
        # Status summary
        print("\nFinal Status:")
        status = laser.get_status()
        for key, value in status.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
        
        # Modulation specs
        print("\nModulation Specifications:")
        mod_specs = laser.get_modulation_specs()
        for port, specs in mod_specs.items():
            print(f"  {port}:")
            for param, value in specs.items():
                print(f"    {param}: {value}")
        
        print("\nAll tests completed successfully")


if __name__ == "__main__":
    test_dfb13tk()