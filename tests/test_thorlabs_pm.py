#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
# The TLPMX library is assumed to be in the system's path or the same directory.
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
            # Initialize the TLPMX driver wrapper
            self.instrument_handle = TLPMX()
            
            # Convert the Python string to a byte string for the c-style function
            resource_name_c = self.visa_id.encode('ascii')

            # Open the device connection
            # The booleans are for ID Query (True) and Reset Device (True)
            self.instrument_handle.open(resource_name_c, c_bool(True), c_bool(True))
            self.is_open = True
            
            # Set default power unit to Watts (0 = W, 1 = dBm)
            self.instrument_handle.setPowerUnit(c_int16(0), TLPM_DEFAULT_CHANNEL)
            
            # Set autoranging on
            self.instrument_handle.setPowerAutoRange(c_int16(1), TLPM_DEFAULT_CHANNEL)
            
            # Get the last calibration message from the sensor
            cmsg = create_string_buffer(128) # Increased buffer size for safety
            self.instrument_handle.getCalibrationMsg(cmsg, TLPM_DEFAULT_CHANNEL)
            self.last_cal_msg = cmsg.value.decode('utf-8')

        except Exception as e:
            # If any part of the initialization fails, ensure the device is closed.
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
            # Create buffers to hold the information returned by the driver
            model_name = create_string_buffer(128)
            serial_number = create_string_buffer(128)
            manufacturer = create_string_buffer(128)
            
            # These booleans are dummy values; they are not used by the function
            dummy_bool = c_bool(False)

            # Call the driver function to get device info
            self.instrument_handle.getDevInfo(model_name, serial_number, manufacturer, byref(dummy_bool))
            
            # Decode the byte strings into regular Python strings and format them
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
            # The driver function expects a c_double type for the wavelength
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
            # Create a c_double variable to pass by reference to the driver function
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
            # Standard formula for converting Watts to dBm
            return 10 * np.log10(power_w * 1000)
        else:
            # Return a value indicating below measurable range
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
    # --- CONFIGURATION ---
    # Find your device's VISA resource string using the Thorlabs PowerMeter software
    # or NI MAX. It will look similar to this.
    POWER_METER_VISA_ID = "USB0::0x1313::0x8076::M01230612::0::INSTR"
    WAVELENGTH_NM = 1310
    # ---------------------

    pm = None
    try:
        # Initialize and connect to the power meter
        pm = ThorlabsPowerMeter(POWER_METER_VISA_ID)
        print(f"Successfully connected to device.")
        print(f"ID: {pm.get_id()}")
        print(f"Sensor Cal Message: {pm.last_cal_msg}")
        
        # Configure the wavelength
        pm.configure(WAVELENGTH_NM)

        print("\nContinuously reading power. Press Ctrl+C to exit.")
        while True:
            # Read power in both Watts and dBm
            power_w = pm.read_power_w()
            power_dbm = 10 * np.log10(power_w * 1000) if power_w > 0 else -999.0
            
            # Print the values on a single, updating line
            # The '\r' carriage return moves the cursor to the start of the line
            print(f"Power: {power_w:.4e} W  ({power_dbm:.2f} dBm)   \r", end="")
            
            # Wait before the next reading
            time.sleep(0.5)

    except ConnectionError as e:
        print(f"Connection Failed: {e}")
        print("Please ensure the VISA ID is correct and the device is connected.")
    except KeyboardInterrupt:
        # This block runs when the user presses Ctrl+C
        print("\nStopping power reading.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        # This block runs no matter what, ensuring the connection is closed
        if pm:
            pm.disconnect()

if __name__ == "__main__":
    main()
