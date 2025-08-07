# FAU Production Test System

Professional automated test system for FAU (Fiber Array Unit) device characterization and production testing.

## Quick Start

```bash
python run_test.py
```

## System Components

### Main Scripts

#### `run_test.py` - System Launcher
Main entry point for all test operations. Provides menu-driven interface to access different test modes.

**Usage:**
```bash
python run_test.py
```

**Options:**
1. Interactive Test System (Recommended for operators)
2. Direct Customer Test Flow (Preset parameters)
3. Exit

#### `interactive_test_system.py` - Interactive Test Interface
Comprehensive test interface with guided setup and session management.

**Features:**
- Step-by-step test configuration
- Device ID and operator tracking
- Configurable data saving preferences
- Test history and session persistence
- Real-time test monitoring
- Automatic instrument connection management

**Key Functions:**
- `setup_session()` - Configure test session parameters
- `setup_instruments()` - Connect and verify all instruments
- `run_test_sequence()` - Execute complete test flow
- `display_results()` - Show test results and analysis

#### `customer_test_flow.py` - Direct Test Implementation
Direct API for programmatic test execution with preset parameters.

**Usage:**
```python
from customer_test_flow import ProductionTestFlow

test_flow = ProductionTestFlow()
test_flow.connect_instruments()

# Configure test parameters
test_info = {
    "device_id": "FAU_001",
    "operator": "ProductionUser",
    "test_date": "2024-01-01"
}

env_info = {
    "environment_temp": 22.0,
    "environment_humidity": 45.0
}

# Execute test
success = test_flow.execute_test_sequence(
    device_count=2,
    test_info=test_info,
    env_info=env_info
)
```

**Key Methods:**
- `connect_instruments()` - Initialize all hardware connections
- `execute_test_sequence()` - Run complete test procedure
- `cleanup()` - Safe shutdown and resource cleanup

#### `health_check.py` - System Health Validation
Comprehensive health check for all instruments and system components.

**Usage:**
```bash
# Quick connectivity test
python health_check.py --quick

# Full system validation with detailed output
python health_check.py --verbose

# Export results to file
python health_check.py --export health_report.json

# Use custom configuration
python health_check.py --config custom_config.json
```

**Test Coverage:**
- DFB laser connectivity and safety state
- Power meter communication and calibration
- SMU output safety and measurement capability
- Power supply channel states and safety
- All instrument identification and error states

**Output Formats:**
- Console summary with pass/fail status
- JSON export for automated monitoring
- Detailed verbose logging for troubleshooting

### Utility Modules

#### `data_manager.py` - Data Management Utilities
Simple data saving and organization system.

**Key Classes:**
- `DataSavingPreferences` - Basic configuration for data export
- `DataManager` - Main data management interface

**Features:**
- Core data always saved (CSV measurements, JSON parameters, TXT logs)
- Optional PNG plots and additional JSON exports
- Date-based directory organization
- Simple preset system (minimal, standard)

**Usage:**
```python
from data_manager import DataManager, DataSavingPreferences

manager = DataManager()
preferences = manager.select_preset()  # Interactive setup
paths = manager.create_data_structure("DEVICE_001")
```

### Hardware Drivers

#### `drivers/dfb13tk.py` - DFB Laser Control
Controls DFB13TK 1310nm laser with temperature and current regulation.

**Connection:** Serial RS-232 (COM3, 9600 baud)
**Key Methods:**
- `laser_on()/laser_off()` - Laser output control
- `set_current(mA)/get_current()` - Current control (0-450mA)
- `set_temperature(°C)/get_temperature()` - Temperature control (15-35°C)
- `get_status()` - Complete instrument status

#### `drivers/pm101.py` - Thorlabs Power Meters
Universal driver for Thorlabs optical power meters with dual driver support.

**Connection:** USB via VISA or native TLPMX
**Key Methods:**
- `read_power()/read_power_dbm()` - Power measurements
- `set_wavelength(nm)` - Measurement wavelength
- `set_auto_range()` - Auto-ranging control
- `get_calibration_message()` - Calibration information

#### `drivers/smu.py` - Source Measure Units
Controls Aim-TTi SMU4000 series for precision source-measure operations.

**Connection:** USB/Ethernet VISA
**Key Methods:**
- `set_mode_source_voltage()/set_mode_source_current()` - Operating mode
- `enable_output()/get_output_state()` - Output control
- `measure_voltage()/measure_current()` - Measurements
- `get_errors()/clear_errors()` - Error management

#### `drivers/tti_qlp355.py` - Power Supplies
Controls TTi QL355TP dual-channel precision power supplies.

**Connection:** USB/Ethernet VISA
**Key Methods:**
- `set_voltage(channel, V)/set_current_limit(channel, A)` - Channel control
- `enable_output(channel)/get_output_state(channel)` - Output management
- `get_output_voltage(channel)/get_output_current(channel)` - Measurements
- `measure_channel_all(channel)` - Complete channel status

## Test Procedures

### FAU Alignment Test (< 4 Elements)
1. Sample placement and probe contact
2. IV sweep characterization (SMU1: 0-5V, 0.1V steps)
3. Laser power sweep (15-35mA, 0.2mA steps)
4. Dual channel power monitoring (PM1/PM2)
5. Data analysis and reporting

### Laser Characterization Test (≥ 4 Elements)
1. Sample placement and probe contact
2. Direct laser power sweep (skip IV alignment)
3. Dual channel power monitoring
4. Data analysis and reporting

## Hardware Configuration

### Production Instrument Addresses
```python
INSTRUMENTS = {
    'SMU1': 'TCPIP::10.11.83.58::INSTR',
    'SMU2': 'TCPIP::10.11.83.60::INSTR',
    'PSU1': 'TCPIP::10.11.83.57::INSTR',
    'PSU2': 'TCPIP::10.11.83.52::INSTR',
    'PM1': 'USB0::0x1313::0x8076::M01250277::0::INSTR',
    'PM2': 'USB0::0x1313::0x8076::M01250278::0::INSTR',
    'LASER': 'COM3'
}
```

## Data Management

### Default Data Structure
```
test_data/
├── {date}/                    # Optional date folders (YYYY-MM-DD)
│   └── {device_id}/
│       ├── raw_measurements.csv
│       ├── test_parameters.json
│       ├── session_log.txt
│       └── plots/             # Optional plots folder
│           ├── iv_sweep.png
│           └── power_sweep.png
```

### Data Export Formats
- **CSV**: Raw measurement data (always saved)
- **JSON**: Test parameters and results (always saved)
- **TXT**: Session logs (always saved)
- **PNG**: Analysis plots (optional)

## Safety Features

### Automatic Safety Systems
- Laser automatically disabled after each test
- SMU compliance limits enforced (10mA default)
- Power supply outputs disabled on startup/shutdown
- Error handling with safe instrument shutdown
- Connection monitoring with timeout protection

### Manual Safety Controls
- Emergency stop capability in all test modes
- Manual instrument disable commands
- Real-time status monitoring
- Error state detection and reporting

## System Requirements

### Dependencies
- Python 3.7+
- PyVISA (for VISA instrument communication)
- NumPy (for data processing)
- Matplotlib (for plotting)
- Serial communication libraries

### Hardware Requirements
- Windows/Linux system with USB and serial ports
- VISA-compatible instrument drivers
- Network access for Ethernet instruments

## Troubleshooting

### Common Issues
1. **Instrument Connection Failures**
   - Run health check: `python health_check.py --verbose`
   - Verify instrument addresses in configuration
   - Check USB/network connections

2. **VISA Driver Issues**
   - Install National Instruments VISA Runtime
   - Verify instrument appears in NI MAX (Windows)

3. **Laser Communication**
   - Verify COM port assignment (Windows Device Manager)
   - Check serial cable connections
   - Ensure proper baud rate (9600)

4. **Data Saving Issues**
   - Check directory permissions
   - Verify disk space availability
   - Review data manager configuration

### Diagnostic Tools
- `health_check.py` - Complete system validation
- Session logs in `./session_data.json`
- Individual driver test functions
- VISA instrument identification tools

## API Documentation

### ProductionTestFlow Class
Main test execution interface for programmatic control.

**Methods:**
- `connect_instruments()` - Initialize all hardware
- `execute_test_sequence(device_count, test_info, env_info)` - Run tests
- `get_test_results()` - Retrieve measurement data
- `cleanup()` - Safe system shutdown

### DataManager Class
Configurable data management system.

**Methods:**
- `select_preset()` - Interactive configuration (minimal/standard)
- `create_data_structure(device_id)` - Setup directories
- `get_save_summary(paths)` - Generate save plan
- `save_preferences(filename)` - Store configuration

## Support

For technical assistance:
1. Run system health check first
2. Review instrument connections and addresses  
3. Check session logs and error messages
4. Contact system administrator for hardware issues

## Version Information

**System Status:** Production Ready
- All drivers cleaned and validated
- Safety systems implemented and tested
- Complete documentation and API
- Health monitoring and diagnostics
- Comprehensive error handling