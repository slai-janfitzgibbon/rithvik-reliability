import pyvisa
import time

class AimTTi_SMU4000:
    def __init__(self, resource_address: str):
        self.rm = pyvisa.ResourceManager()
        self.instrument = self.rm.open_resource(resource_address)
        self.instrument.read_termination = '\n'
        self.instrument.write_termination = '\n'
        print(f"Connected to: {self.get_idn()}")

    def get_idn(self) -> str:
        return self.instrument.query("*IDN?")

    def reset(self):
        self.instrument.write("*RST")

    def set_mode_source_current(self):
        self.instrument.write("SYST:FUNC:MODE SOURCECURR")

    def set_mode_source_voltage(self):
        self.instrument.write("SYST:FUNC:MODE SOURCEVOLT")

    def set_source_current(self, current: float):
        self.instrument.write(f"SOUR:CURR:LEV {current:.6f}")
        
    def set_voltage_limit(self, voltage_limit: float):
        self.instrument.write(f"SOUR:CURR:VOLT:LIM {voltage_limit:.4f}")

    def enable_output(self, enable: bool):
        state = "ON" if enable else "OFF"
        self.instrument.write(f"OUTP:STAT {state}")

    def measure_voltage(self) -> float:
        return float(self.instrument.query("MEAS:VOLT?"))
        
    def measure_current(self) -> float:
        return float(self.instrument.query("MEAS:CURR?"))
        
    def disconnect(self):
        self.instrument.close()
        self.rm.close()
        print("Aim-TTi SMU4000 disconnected.")