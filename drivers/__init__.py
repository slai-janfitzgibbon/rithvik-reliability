"""
Driver Module for Test and Measurement Equipment

This module provides a unified interface to all test equipment drivers.
All drivers follow consistent patterns and provide comprehensive functionality.
Supports multiple instances of the same instrument type with unique IDs.
"""

# Import all available drivers
from .dfb13tk import DFB13TK, DFBMeasurement, DFBSweepConfig
from .pm101 import ThorlabsPowerMeter, Thorlabs_PMxxx, PowerMeterMeasurement, PowerMeterMonitorConfig
from .smu import AimTTi_SMU4000, SMUSweepConfig, SMUMeasurement
from .tti_qlp355 import TTi_QL355TP, PSUSweepConfig, PSUChannelMeasurement
from typing import Dict, List, Any, Optional

# Driver registry for easy access
AVAILABLE_DRIVERS = {
    'dfb13tk': {
        'class': DFB13TK,
        'name': 'DFB13TK Laser',
        'interface': 'Serial',
        'description': 'DFB13TK 1310nm DFB Laser with comprehensive control',
        'supports_multiple': False,
        'connection_args': ['port'],
        'example_addresses': ['COM3', '/dev/ttyUSB0']
    },
    'thorlabs_pm': {
        'class': ThorlabsPowerMeter,
        'name': 'Thorlabs Power Meter',
        'interface': 'TLPMX/VISA',
        'description': 'Thorlabs Power Meter with TLPMX driver support',
        'supports_multiple': True,
        'connection_args': ['resource_address', 'unit_id'],
        'example_addresses': ['USB0::0x1313::0x8076::M01230612::0::INSTR']
    },
    'smu': {
        'class': AimTTi_SMU4000,
        'name': 'Aim-TTi SMU4000',
        'interface': 'VISA',
        'description': 'Source Measure Unit with sweep and I-V characterization',
        'supports_multiple': True,
        'connection_args': ['resource_address', 'unit_id'],
        'example_addresses': ['USB0::0x103E::0x4002::...::INSTR']
    },
    'psu': {
        'class': TTi_QL355TP,
        'name': 'TTi QL355TP Power Supply',
        'interface': 'VISA',
        'description': 'Dual channel power supply with load regulation testing',
        'supports_multiple': True,
        'connection_args': ['resource_address', 'unit_id'],
        'example_addresses': ['USB0::0x103E::0x0109::...::INSTR']
    }
}

class MultiInstrumentManager:
    """
    Manager for multiple instances of instruments
    Handles connection, coordination, and data collection from multiple units
    """
    
    def __init__(self):
        self.instruments: Dict[str, Any] = {}
        self.instrument_types: Dict[str, str] = {}
        
    def add_instrument(self, unit_id: str, driver_type: str, *args, **kwargs) -> bool:
        """
        Add an instrument instance to the manager
        
        Args:
            unit_id: Unique identifier for this instrument
            driver_type: Type of driver (key from AVAILABLE_DRIVERS)
            *args, **kwargs: Arguments to pass to driver constructor
            
        Returns:
            True if successful, False otherwise
        """
        if driver_type.lower() not in AVAILABLE_DRIVERS:
            print(f"Unknown driver type: {driver_type}")
            return False
            
        if unit_id in self.instruments:
            print(f"Unit ID '{unit_id}' already exists")
            return False
            
        driver_info = AVAILABLE_DRIVERS[driver_type.lower()]
        driver_class = driver_info['class']
        
        try:
            # For drivers that support unit_id, pass it
            if driver_info['supports_multiple'] and 'unit_id' not in kwargs:
                kwargs['unit_id'] = unit_id
                
            instrument = driver_class(*args, **kwargs)
            self.instruments[unit_id] = instrument
            self.instrument_types[unit_id] = driver_type.lower()
            print(f"Successfully added {unit_id} ({driver_info['name']})")
            return True
            
        except Exception as e:
            print(f"Failed to add {unit_id}: {e}")
            return False
    
    def get_instrument(self, unit_id: str):
        """Get an instrument by unit ID"""
        return self.instruments.get(unit_id)
    
    def get_instruments_by_type(self, driver_type: str) -> Dict[str, Any]:
        """Get all instruments of a specific type"""
        return {uid: inst for uid, inst in self.instruments.items() 
                if self.instrument_types[uid] == driver_type.lower()}
    
    def list_instruments(self):
        """List all connected instruments"""
        print("Connected Instruments:")
        print("=" * 50)
        for unit_id, instrument in self.instruments.items():
            driver_type = self.instrument_types[unit_id]
            driver_info = AVAILABLE_DRIVERS[driver_type]
            print(f"{unit_id}: {driver_info['name']}")
            if hasattr(instrument, 'device_info'):
                model = instrument.device_info.get('model', 'Unknown')
                print(f"  Model: {model}")
            print()
    
    def disconnect_all(self):
        """Safely disconnect all instruments"""
        for unit_id, instrument in self.instruments.items():
            try:
                if hasattr(instrument, 'disconnect'):
                    instrument.disconnect()
                elif hasattr(instrument, 'close'):
                    instrument.close()
                print(f"Disconnected {unit_id}")
            except Exception as e:
                print(f"Error disconnecting {unit_id}: {e}")
        
        self.instruments.clear()
        self.instrument_types.clear()
    
    def get_all_status(self) -> Dict[str, Dict]:
        """Get status from all instruments"""
        status = {}
        for unit_id, instrument in self.instruments.items():
            try:
                if hasattr(instrument, 'get_status'):
                    status[unit_id] = instrument.get_status()
                else:
                    status[unit_id] = {'error': 'No status method available'}
            except Exception as e:
                status[unit_id] = {'error': str(e)}
        return status

def list_drivers():
    """List all available drivers with their information"""
    print("Available Drivers:")
    print("=" * 80)
    for key, info in AVAILABLE_DRIVERS.items():
        print(f"{key.upper()}:")
        print(f"  Name: {info['name']}")
        print(f"  Interface: {info['interface']}")
        print(f"  Description: {info['description']}")
        print(f"  Supports Multiple: {info['supports_multiple']}")
        print(f"  Connection Args: {', '.join(info['connection_args'])}")
        print(f"  Example Addresses: {info['example_addresses']}")
        print()

def get_driver(driver_name: str):
    """Get a driver class by name"""
    if driver_name.lower() in AVAILABLE_DRIVERS:
        return AVAILABLE_DRIVERS[driver_name.lower()]['class']
    else:
        available = ', '.join(AVAILABLE_DRIVERS.keys())
        raise ValueError(f"Driver '{driver_name}' not found. Available: {available}")

def create_production_setup() -> MultiInstrumentManager:
    """
    Create production multi-instrument setup with actual hardware addresses
    """
    manager = MultiInstrumentManager()
    
    # Production hardware addresses
    production_config = {
        'SMU1': ('smu', 'TCPIP::10.11.83.58::INSTR'),
        'SMU2': ('smu', 'TCPIP::10.11.83.60::INSTR'),
        'PSU1': ('psu', 'TCPIP::10.11.83.57::INSTR'),
        'PSU2': ('psu', 'TCPIP::10.11.83.52::INSTR'),
        'PM1': ('thorlabs_pm', 'USB0::0x1313::0x8076::M01250277::0::INSTR'),
        'PM2': ('thorlabs_pm', 'USB0::0x1313::0x8076::M01250278::0::INSTR'),
        'LASER': ('dfb13tk', 'COM3')
    }
    
    print("PRODUCTION Multi-Instrument Setup:")
    print("Ready for actual hardware connection")
    print("=" * 60)
    
    for unit_id, (driver_type, address) in production_config.items():
        print(f"{unit_id}: {AVAILABLE_DRIVERS[driver_type]['name']}")
        print(f"  Address: {address}")
    
    return manager

def create_example_setup() -> MultiInstrumentManager:
    """
    Create an example multi-instrument setup for reference
    """
    manager = MultiInstrumentManager()
    
    # Example addresses for reference
    example_config = {
        'SMU1': ('smu', 'TCPIP::10.11.83.58::INSTR'),
        'SMU2': ('smu', 'TCPIP::10.11.83.60::INSTR'),
        'PSU1': ('psu', 'TCPIP::10.11.83.57::INSTR'),
        'PSU2': ('psu', 'TCPIP::10.11.83.52::INSTR'),
        'PM1': ('thorlabs_pm', 'USB0::0x1313::0x8076::M01250277::0::INSTR'),
        'PM2': ('thorlabs_pm', 'USB0::0x1313::0x8076::M01250278::0::INSTR'),
        'LASER': ('dfb13tk', 'COM3')
    }
    
    print("Multi-Instrument Setup (Production Addresses):")
    print("=" * 60)
    
    for unit_id, (driver_type, address) in example_config.items():
        print(f"{unit_id}: {AVAILABLE_DRIVERS[driver_type]['name']}")
        print(f"  Address: {address}")
    
    return manager

__all__ = [
    'DFB13TK',
    'DFBMeasurement',
    'DFBSweepConfig',
    'ThorlabsPowerMeter', 
    'Thorlabs_PMxxx',
    'PowerMeterMeasurement',
    'PowerMeterMonitorConfig',
    'AimTTi_SMU4000',
    'TTi_QL355TP',
    'SMUSweepConfig',
    'SMUMeasurement', 
    'PSUSweepConfig',
    'PSUChannelMeasurement',
    'MultiInstrumentManager',
    'AVAILABLE_DRIVERS',
    'list_drivers',
    'get_driver',
    'create_example_setup',
    'create_production_setup'
]