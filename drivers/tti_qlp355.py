import pyvisa
import time

class TTi_QL355TP:
    def __init__(self, resource_address: str):
        self.rm = pyvisa.ResourceManager()
        self.instrument = self.rm.open_resource(resource_address)
        self.instrument.read_termination = '\n'
        self.instrument.write_termination = '\n'
        print(f"Connected to: {self.get_idn()}")

    def get_idn(self) -> str:
        return self.instrument.query("*IDN?")

    def set_voltage(self, channel: int, voltage: float):
        if channel not in [1, 2]:
            raise ValueError("Channel must be 1 or 2.")
        self.instrument.write(f"V{channel} {voltage:.4f}")

    def set_current_limit(self, channel: int, current: float):
        if channel not in [1, 2]:
            raise ValueError("Channel must be 1 or 2.")
        self.instrument.write(f"I{channel} {current:.4f}")

    def enable_output(self, channel: int, enable: bool):
        if channel not in [1, 2]:
            raise ValueError("Channel must be 1 or 2.")
        state = 1 if enable else 0
        self.instrument.write(f"OP{channel} {state}")

    def get_output_voltage(self, channel: int) -> float:
        if channel not in [1, 2]:
            raise ValueError("Channel must be 1 or 2.")
        response = self.instrument.query(f"V{channel}O?")
        return float(response)

    def get_output_current(self, channel: int) -> float:
        if channel not in [1, 2]:
            raise ValueError("Channel must be 1 or 2.")
        response = self.instrument.query(f"I{channel}O?")
        return float(response)
        
    def disconnect(self):
        self.instrument.close()
        self.rm.close()
        print("TTi QL355TP disconnected.")