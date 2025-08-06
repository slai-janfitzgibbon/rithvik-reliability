import time
import numpy as np
import pandas as pd
import logging

from drivers.tti_ql355tp import TTi_QL355TP
from drivers.aim_smu4000 import AimTTi_SMU4000
from drivers.thorlabs_pm import Thorlabs_PMxxx
from utils.recorder import UniversalRecorder, PlotConfig, DataConfig

PSU_VISA_ADDRESS = 'USB0::0x103E::0x0109::...::INSTR'
SMU_VISA_ADDRESS = 'USB0::0x103E::0x4002::...::INSTR'
PD_VISA_ADDRESS  = 'USB0::0x1313::0x8078::...::INSTR'

TARGET_POWER_MW = 5.0
STABILIZATION_TOLERANCE_MW = 0.05
MAX_STABILIZATION_ATTEMPTS = 20
PSU_INITIAL_VOLTAGE = 3.3
PSU_CHANNEL = 1

SMU_CURRENT_START_A = 0.0
SMU_CURRENT_STOP_A = 0.05
SMU_CURRENT_STEPS = 51
SMU_VOLTAGE_LIMIT_V = 5.0

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
recorder = UniversalRecorder(top_dir='./test_output')

def stabilize_psu_output(psu: TTi_QL355TP, pd: Thorlabs_PMxxx):
    logging.info(f"--- Starting PSU stabilization for {TARGET_POWER_MW:.2f} mW ---")
    
    current_voltage = PSU_INITIAL_VOLTAGE
    psu.set_voltage(PSU_CHANNEL, current_voltage)
    psu.enable_output(PSU_CHANNEL, True)
    time.sleep(0.5)

    for attempt in range(MAX_STABILIZATION_ATTEMPTS):
        measured_power_mw = pd.read_power() * 1000
        error_mw = measured_power_mw - TARGET_POWER_MW
        
        logging.info(
            f"Attempt {attempt+1}/{MAX_STABILIZATION_ATTEMPTS}: "
            f"Voltage={current_voltage:.3f}V, "
            f"Power={measured_power_mw:.3f}mW, "
            f"Error={error_mw:.3f}mW"
        )
        
        if abs(error_mw) <= STABILIZATION_TOLERANCE_MW:
            logging.info(f"Stabilization successful at {measured_power_mw:.3f} mW.")
            return True
        
        p_gain = 0.02
        voltage_adjustment = -error_mw * p_gain
        current_voltage += voltage_adjustment
        current_voltage = max(0, min(5.0, current_voltage))
        
        psu.set_voltage(PSU_CHANNEL, current_voltage)
        time.sleep(0.2)

    logging.error("Failed to stabilize power within max attempts.")
    psu.enable_output(PSU_CHANNEL, False)
    return False

def run_smu_sweep(smu: AimTTi_SMU4000, pd: Thorlabs_PMxxx):
    logging.info(f"--- Starting SMU current sweep from {SMU_CURRENT_START_A}A to {SMU_CURRENT_STOP_A}A ---")
    
    smu.set_mode_source_current()
    smu.set_voltage_limit(SMU_VOLTAGE_LIMIT_V)
    smu.enable_output(True)
    
    current_sweep = np.linspace(SMU_CURRENT_START_A, SMU_CURRENT_STOP_A, SMU_CURRENT_STEPS)
    measured_powers = []
    
    for i, current in enumerate(current_sweep):
        smu.set_source_current(current)
        time.sleep(0.1)
        
        power = pd.read_power()
        measured_powers.append(power)
        
        logging.info(f"Step {i+1}/{SMU_CURRENT_STEPS}: Set Current={current*1000:.2f}mA, Measured Power={power*1000:.3f}mW")
        
    smu.enable_output(False)
    
    results_df = pd.DataFrame({
        'SMU_Current_A': current_sweep,
        'Photodetector_Power_W': measured_powers
    })
    
    return results_df

if __name__ == "__main__":
    psu = None
    smu = None
    pd = None

    try:
        logging.info("Connecting to instruments...")
        psu = TTi_QL355TP(PSU_VISA_ADDRESS)
        smu = AimTTi_SMU4000(SMU_VISA_ADDRESS)
        pd = Thorlabs_PMxxx(PD_VISA_ADDRESS)
        
        pd.set_wavelength(1550)
        pd.set_power_unit("W")
        pd.set_auto_range(True)
        psu.set_current_limit(PSU_CHANNEL, 0.5)

        recorder.test_run_start(
            workstation='AutoTest-01',
            dut_family='MyDeviceFamily', 
            dut_batch='B01',
            dut_lot='L01',
            dut_wafer='W01',
            dut_id='DUT-SN123',
            run_set_id=1,
            run_id=1
        )

        recorder.phase_start(phase_idx=1, phase_name="PSU_Stabilization")
        if stabilize_psu_output(psu, pd):
            logging.info("PSU stabilization phase complete.")
        else:
            raise RuntimeError("Could not complete PSU stabilization phase.")
        recorder.phase_end()
        
        recorder.phase_start(phase_idx=2, phase_name="SMU_Current_Sweep")
        sweep_data = run_smu_sweep(smu, pd)
        
        test_info = {"test_name": "SMU_IV_Sweep", "test_location": "Lab_B", "test_user": "AutoScript"}
        env_info = {"environment_temp": 22.5, "environment_humidity": 48.1}

        recorder.record_complete_dataset(
            name='smu_sweep_results',
            data=sweep_data,
            test_info=test_info,
            environment_info=env_info,
            testing_variable="SMU_Current_A",
            dependent_variables=["Photodetector_Power_W"],
            script_version="1.0"
        )
        
        logging.info("SMU sweep phase complete.")
        recorder.phase_end()

    except Exception as e:
        logging.error(f"An error occurred during the test flow: {e}", exc_info=True)
        
    finally:
        logging.info("Test flow finished. Cleaning up...")
        if psu:
            psu.enable_output(1, False)
            psu.enable_output(2, False)
            psu.disconnect()
        if smu:
            smu.enable_output(False)
            smu.disconnect()
        if pd:
            pd.disconnect()
            
        recorder.run_end()
        logging.info("All resources closed.")