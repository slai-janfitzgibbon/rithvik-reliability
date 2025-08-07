import logging
import time
import numpy as np
import pandas as pd
from drivers.smu import AimTTi_SMU4000, SMUSweepConfig
from utils.recorder import UniversalRecorder

SMU_VISA_ADDRESS = 'TCPIP::10.11.83.58::INSTR' 
# Directory to save the test data
OUTPUT_DIRECTORY = './test_output'

def run_iv_sweep():
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    
    smu = None
    try:
        logging.info(f"Connecting to SMU at {SMU_VISA_ADDRESS}...")
        smu = AimTTi_SMU4000(SMU_VISA_ADDRESS, unit_id="SMU1_IV_Sweep")
        logging.info("SMU connected successfully.")

        recorder = UniversalRecorder(top_dir=OUTPUT_DIRECTORY)
        logging.info(f"Recorder initialized. Output will be saved to '{OUTPUT_DIRECTORY}'.")

        # --- Setup Test Run ---
        recorder.test_run_start(
            workstation='TestBench1',
            dut_family='ExampleDevice',
            dut_batch='B01',
            dut_lot='L01',
            dut_wafer='W01',
            dut_id='Device_001',
            run_set_id=1,
            run_id=1
        )

        # --- Setup and Run the Sweep ---
        recorder.phase_start(phase_idx=1, phase_name="IV_Sweep")
        
        logging.info("Configuring IV sweep...")
        iv_sweep_config = SMUSweepConfig(
            start_value=0.0,      # Start Voltage (V)
            stop_value=5.0,       # Stop Voltage (V)
            steps=51,             # Number of steps
            step_delay=0.05,      # Delay between steps (s)
            compliance_limit=0.01 # Current limit (A)
        )

        logging.info(f"Starting voltage sweep from {iv_sweep_config.start_value}V to {iv_sweep_config.stop_value}V...")
        # The voltage_sweep method handles setting the mode, limits, and looping.
        sweep_data = smu.voltage_sweep(iv_sweep_config)
        logging.info("Sweep complete.")

        # --- Log the Data ---
        logging.info("Logging data...")
        
        # Define metadata for the recorder
        test_info = {
            "test_name": "Simple_IV_Sweep",
            "test_location": "Oxford Lab",
            "test_user": "Rithvik"
        }
        env_info = {
            "environment_temp": 23.5,
            "environment_humidity": 45.2
        }

        # The record_complete_dataset function saves the CSV, plots, and metadata
        recorder.record_complete_dataset(
            name='iv_curve',
            data=sweep_data,
            test_info=test_info,
            environment_info=env_info,
            testing_variable="set_voltage",
            dependent_variables=["measured_current"],
            equipment_ids="SMU1",
            script_version="1.0",
            comments="A simple IV sweep test."
        )
        
        logging.info("Data logging complete.")
        recorder.phase_end()

    except Exception as e:
        logging.error(f"An error occurred during the test: {e}", exc_info=True)
        
    finally:
        # --- Cleanup ---
        logging.info("Cleaning up resources...")
        if smu:
            smu.disconnect()

        if 'recorder' in locals():
            recorder.run_end()
            
        logging.info("Script finished.")

if __name__ == "__main__":
    run_iv_sweep()
