
"""
This script combines two approaches for controlling a Thorlabs Power Meter.

It uses the Thorlabs-provided TLPMX driver library via Python's ctypes module
for direct instrument communication (as seen in the first user-provided script).
This direct method can be more reliable than generic VISA commands.

The script is structured into a user-friendly class, `ThorlabsPowerMeter`,
with methods for configuration and continuous power reading (inspired by the
second user-provided pyvisa script).

This provides the robust connection of the first script with the cleaner
structure and functionality of the second.
"""

import time
import numpy as np
from ctypes import cdll, byref, create_string_buffer, c_bool, c_int16, c_double, c_char_p
from TLPMX import TLPMX
from TLPMX import TLPM_DEFAULT_CHANNEL

class ThorlabsPowerMeter:
    """
    A class to control Thorlabs power meters using the TLPMX driver.
    """
    def __init__(self, visa_id: str):
        """
        Initializes the power meter and establishes a connection.

        Args:
            visa_id (str): The VISA resource string for the instrument.
                           e.g., "USB0::0x1313::0x8076::M01230612::0::INSTR"
        """
        self.visa_id = visa_id
        self.instrument_handle = None
        self.is_open = False
        self.last_cal_msg = ""
        self.wavelength = 0.0

        try:
            self.instrument_handle = TLPMX()
            
            resource_name_c = self.visa_id.encode('ascii')

            self.instrument_handle.open(resource_name_c, c_bool(True), c_bool(True))
            self.is_open = True
            
            self.instrument_handle.setPowerUnit(c_int16(0), TLPM_DEFAULT_CHANNEL)
            
            self.instrument_handle.setPowerAutoRange(c_int16(1), TLPM_DEFAULT_CHANNEL)
            
            cmsg = create_string_buffer(128) # Increased buffer size for safety
            self.instrument_handle.getCalibrationMsg(cmsg, TLPM_DEFAULT_CHANNEL)
            self.last_cal_msg = cmsg.value.decode('utf-8')

        except Exception as e:
            if self.is_open:
                self.disconnect()
            raise ConnectionError(f"Could not connect to or configure Power Meter: {e}")

    def get_id(self) -> str:
        """
        Retrieves identifying information from the power meter.

        Returns:
            str: A string containing the manufacturer, model, and serial number.
        """
        if not self.is_open:
            return "Device not connected."
            
        try:
            model_name = create_string_buffer(128)
            serial_number = create_string_buffer(128)
            manufacturer = create_string_buffer(128)
            
            dummy_bool = c_bool(False)

            self.instrument_handle.getDevInfo(model_name, serial_number, manufacturer, byref(dummy_bool))
            
            return (f"Manufacturer: {manufacturer.value.decode('utf-8')}, "
                    f"Model: {model_name.value.decode('utf-8')}, "
                    f"S/N: {serial_number.value.decode('utf-8')}")
        except Exception as e:
            return f"Error retrieving ID: {e}"

    def configure(self, wavelength: int):
        """
        Configures the power meter for a specific wavelength.

        Args:
            wavelength (int): The wavelength to measure in nanometers (e.g., 1310).
        """
        if not self.is_open:
            print("Cannot configure, device not connected.")
            return

        try:
            self.wavelength = float(wavelength)
            self.instrument_handle.setWavelength(c_double(self.wavelength), TLPM_DEFAULT_CHANNEL)
            print(f"Configured for {wavelength} nm.")
        except Exception as e:
            print(f"Error setting wavelength: {e}")

    def read_power_w(self) -> float:
        """
        Measures and returns the current power reading in Watts.

        Returns:
            float: The power reading in Watts. Returns 0.0 on error.
        """
        if not self.is_open:
            return 0.0
            
        try:
            power_c = c_double()
            self.instrument_handle.measPower(byref(power_c), TLPM_DEFAULT_CHANNEL)
            return power_c.value
        except Exception as e:
            print(f"Error reading power: {e}")
            return 0.0

    def read_power_dbm(self) -> float:
        """
        Measures power in Watts and converts it to dBm.

        Returns:
            float: The power reading in dBm. Returns a very low number on error or zero power.
        """
        power_w = self.read_power_w()
        if power_w > 0:
            return 10 * np.log10(power_w * 1000)
        else:
            return -999.0

    def disconnect(self):
        """
        Closes the connection to the power meter.
        """
        if self.is_open and self.instrument_handle:
            try:
                self.instrument_handle.close()
                self.is_open = False
                print("\nDisconnected from Power Meter.")
            except Exception as e:
                print(f"Error during disconnection: {e}")


def main():
    """
    Main function to run the power meter reading loop.
    """
    POWER_METER_VISA_ID = "USB0::0x1313::0x8076::M01230612::0::INSTR"
    WAVELENGTH_NM = 1310

    pm = None
    try:
        pm = ThorlabsPowerMeter(POWER_METER_VISA_ID)
        print(f"Successfully connected to device.")
        print(f"ID: {pm.get_id()}")
        print(f"Sensor Cal Message: {pm.last_cal_msg}")
        
        pm.configure(WAVELENGTH_NM)

        print("\nContinuously reading power. Press Ctrl+C to exit.")
        while True:
            power_w = pm.read_power_w()
            power_dbm = 10 * np.log10(power_w * 1000) if power_w > 0 else -999.0
            
            print(f"Power: {power_w:.4e} W  ({power_dbm:.2f} dBm)   \r", end="")
            
            time.sleep(0.5)

    except ConnectionError as e:
        print(f"Connection Failed: {e}")
        print("Please ensure the VISA ID is correct and the device is connected.")
    except KeyboardInterrupt:
        print("\nStopping power reading.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        if pm:
            pm.disconnect()

if __name__ == "__main__":
    main()
