# FAU Production Test System

Automated test system for FAU (Fiber Array Unit) devices.

## Quick Start

```bash
python run_test.py
```

## System Features

### Interactive Test System (Recommended)
- **Guided Setup**: Step-by-step prompts for test configuration
- **Device Management**: Track device IDs, operators, and test history  
- **Rerun Support**: Easy rerun of failed or repeated tests
- **Multiple Run Planning**: Support for batch testing
- **Data Logging**: Automatic data recording with configurable options
- **Session Management**: Persistent test history and session data

### Test Capabilities
- **FAU Alignment**: IV sweep for devices with <4 elements
- **Laser Characterization**: Power sweep from 15-35mA in 0.2mA steps
- **Dual Power Monitoring**: Simultaneous measurement on channels 3&4
- **Environmental Logging**: Temperature and humidity tracking

## Hardware Configuration

### Instruments
- **SMU1**: 10.11.83.58 (Source Measure Unit #1)
- **SMU2**: 10.11.83.60 (Source Measure Unit #2)  
- **PSU1**: 10.11.83.57 (Power Supply #1)
- **PSU2**: 10.11.83.52 (Power Supply #2)
- **PM1**: M01250277 (Power Meter #1 - Channel 3)
- **PM2**: M01250278 (Power Meter #2 - Channel 4)
- **DFB**: COM3 (DFB Laser)

## Test Procedure

### For Devices with <4 Elements:
1. **Sample Placement**: Place sample on chuck, touchdown probe card
2. **FAU Alignment**: Automated IV sweep using SMU1 (0-5V, 0.1V steps)
3. **Laser Characterization**: Power sweep with dual power meter monitoring
4. **Data Recording**: Automatic logging and analysis

### For Devices with ≥4 Elements:
1. **Sample Placement**: Place sample on chuck, touchdown probe card  
2. **Laser Characterization**: Direct power sweep (skip alignment)
3. **Data Recording**: Automatic logging and analysis

## Data Management

### Automatic Logging
- Test parameters and environmental conditions
- Complete measurement datasets with timestamps
- Analysis plots and statistical summaries
- Test history database with operator tracking

### Data Location
- Default: `./test_data/{device_id}/`
- Configurable per test session
- CSV exports for external analysis
- PNG plots for documentation

## Usage Examples

### Interactive Mode
```bash
python run_test.py
# Select option 1 (Interactive Test System)
# Follow prompts for device setup
```

### Direct Mode  
```bash
python run_test.py  
# Select option 2 (Direct Customer Test Flow)
# Uses preset parameters
```

### Programming Mode
```python
from customer_test_flow import ProductionTestFlow

test_flow = ProductionTestFlow()
test_flow.connect_instruments()

# Configure test
test_info = {"device_id": "FAU_001", "operator": "User"}
env_info = {"environment_temp": 22.0, "environment_humidity": 45.0}

# Execute test
success = test_flow.execute_test_sequence(
    device_count=2,
    test_info=test_info, 
    env_info=env_info
)
```
## Files Structure

```
├── run_test.py                 # Main launcher
├── interactive_test_system.py  # Interactive test interface
├── customer_test_flow.py       # Direct test flow implementation
├── drivers/                    # Clean production drivers
│   ├── __init__.py            # Driver registry and management
│   ├── dfb13tk.py             # DFB laser driver
│   ├── pm101.py               # Thorlabs power meter driver  
│   ├── smu.py                 # SMU driver
│   └── tti_qlp355.py          # PSU driver
└── utils/
    └── recorder.py            # Data recording utilities
```

## Safety Notes

- System automatically turns laser OFF after each test
- SMU compliance limits enforced (10mA default)
- All outputs disabled on system exit
- Error handling with safe shutdown procedures

## Support

For technical support or issues:
1. Check instrument connections and addresses
2. Verify COM port for DFB laser (COM3)
3. Review session logs in `./session_data.json`
