import pyvisa

class Thorlabs_PMxxx:
    def __init__(self, resource_address: str):
        self.rm = pyvisa.ResourceManager()
        self.instrument = self.rm.open_resource(resource_address)
        self.instrument.read_termination = '\n'
        self.instrument.write_termination = '\n'
        print(f"Connected to: {self.get_idn()}")

    def get_idn(self) -> str:
        return self.instrument.query("SYST:SENS:IDN?")
        
    def set_wavelength(self, wavelength_nm: int):
        self.instrument.write(f"SENS:CORR:WAV {wavelength_nm}")

    def set_power_unit(self, unit: str = "W"):
        if unit.upper() not in ["W", "DBM"]:
            raise ValueError("Unit must be 'W' or 'DBM'")
        self.instrument.write(f"SENS:POW:UNIT {unit.upper()}")

    def set_auto_range(self, enable: bool):
        state = "ON" if enable else "OFF"
        self.instrument.write(f"SENS:POW:RANG:AUTO {state}")

    def read_power(self) -> float:
        return float(self.instrument.query("MEAS:POW?"))
        
    def disconnect(self):
        self.instrument.close()
        self.rm.close()
        print("Thorlabs Power Meter disconnected.")