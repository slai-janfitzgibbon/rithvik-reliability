"""
SMU Test Script - Aim-TTi SMU4000 Series
Test script for debugging and validating SMU communication and functionality.
"""

import sys
import os
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drivers.smu import AimTTi_SMU4000

def test_smu_connection(address: str, unit_id: str = "SMU_TEST"):
    """Test basic SMU connection and identification"""
    print(f"\n{'='*60}")
    print(f"TESTING SMU CONNECTION: {unit_id}")
    print(f"Address: {address}")
    print(f"{'='*60}")
    
    try:
        smu = AimTTi_SMU4000(address, unit_id)
        print("SUCCESS: SMU connection established")
        
        idn = smu.get_idn()
        print(f"Identification: {idn}")
        
        errors = smu.get_errors()
        if errors:
            print(f"Initial errors found: {len(errors)}")
            for error in errors:
                print(f"  - {error}")
            smu.clear_errors()
            print("Errors cleared")
        else:
            print("No initial errors")
        
        smu.disconnect()
        return True
        
    except Exception as e:
        print(f"FAILED: SMU connection failed - {e}")
        return False

def test_smu_basic_functions(address: str, unit_id: str = "SMU_TEST"):
    """Test basic SMU functions without enabling output"""
    print(f"\n{'='*60}")
    print(f"TESTING SMU BASIC FUNCTIONS: {unit_id}")
    print(f"{'='*60}")
    
    try:
        smu = AimTTi_SMU4000(address, unit_id)
        
        print("\nTesting voltage source mode...")
        smu.set_mode_source_voltage()
        mode = smu.get_source_mode()
        print(f"Current mode: {mode}")
        
        print("\nTesting current source mode...")
        smu.set_mode_source_current()
        mode = smu.get_source_mode()
        print(f"Current mode: {mode}")
        
        output_state = smu.get_output_state()
        print(f"\nOutput enabled: {output_state}")
        if output_state:
            print("WARNING: Output is enabled - disabling for safety")
            smu.enable_output(False)
        
        print("\nTesting measurements (output disabled)...")
        voltage = smu.measure_voltage()
        current = smu.measure_current()
        power = smu.measure_power()
        
        print(f"Measured voltage: {voltage:.6f} V")
        print(f"Measured current: {current:.9f} A")  
        print(f"Measured power: {power:.9f} W")
        
        print("\nGetting comprehensive status...")
        status = smu.get_status()
        print("Status information:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        smu.disconnect()
        print("\nSUCCESS: Basic function tests completed")
        return True
        
    except Exception as e:
        print(f"FAILED: Basic function test failed - {e}")
        return False

def test_smu_safe_output(address: str, unit_id: str = "SMU_TEST"):
    """Test SMU output with safe parameters"""
    print(f"\n{'='*60}")
    print(f"TESTING SMU SAFE OUTPUT: {unit_id}")
    print(f"{'='*60}")
    
    print("WARNING: This test will briefly enable SMU output with safe parameters")
    print("Make sure no device is connected or use appropriate safety measures")
    
    confirm = input("Continue with output test? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("Output test skipped")
        return True
    
    try:
        smu = AimTTi_SMU4000(address, unit_id)
        
        print("\nConfiguring voltage source mode...")
        smu.set_mode_source_voltage()
        
        print("Setting safe parameters: 1V, 1mA limit")
        
        print("Enabling output for 2 seconds...")
        smu.enable_output(True)
        time.sleep(0.5)
        
        voltage = smu.measure_voltage()
        current = smu.measure_current()
        power = smu.measure_power()
        
        print(f"Output voltage: {voltage:.6f} V")
        print(f"Output current: {current:.9f} A")
        print(f"Output power: {power:.9f} W")
        
        time.sleep(1.5)
        
        print("Disabling output...")
        smu.enable_output(False)
        
        output_state = smu.get_output_state()
        print(f"Output disabled: {not output_state}")
        
        smu.disconnect()
        print("\nSUCCESS: Safe output test completed")
        return True
        
    except Exception as e:
        print(f"FAILED: Safe output test failed - {e}")
        return False

def test_smu_error_handling(address: str, unit_id: str = "SMU_TEST"):
    """Test SMU error handling capabilities"""
    print(f"\n{'='*60}")
    print(f"TESTING SMU ERROR HANDLING: {unit_id}")
    print(f"{'='*60}")
    
    try:
        smu = AimTTi_SMU4000(address, unit_id)
        
        smu.clear_errors()
        
        errors = smu.get_errors()
        print(f"Errors after clear: {len(errors)}")
        
        print("\nTesting error detection...")
        try:
            response = smu.query("INVALID:COMMAND?")
            print(f"Unexpected response to invalid command: {response}")
        except:
            print("Expected error from invalid command")
        
        errors = smu.get_errors()
        if errors:
            print(f"Detected {len(errors)} errors:")
            for i, error in enumerate(errors):
                print(f"  {i+1}. {error}")
            smu.clear_errors()
            print("Errors cleared")
        else:
            print("No errors detected")
        
        smu.disconnect()
        print("\nSUCCESS: Error handling test completed")
        return True
        
    except Exception as e:
        print(f"FAILED: Error handling test failed - {e}")
        return False

def run_comprehensive_smu_test():
    """Run comprehensive SMU testing"""
    print("SMU COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_configs = [
        {"address": "TCPIP::10.11.83.58::INSTR", "unit_id": "SMU1"},
        {"address": "TCPIP::10.11.83.60::INSTR", "unit_id": "SMU2"},
    ]
    
    all_results = []
    
    for config in test_configs:
        address = config["address"]
        unit_id = config["unit_id"]
        
        print(f"\n\nTESTING SMU: {unit_id}")
        print(f"Address: {address}")
        
        result1 = test_smu_connection(address, unit_id)
        
        result2 = False
        if result1:
            result2 = test_smu_basic_functions(address, unit_id)
        
        result3 = False
        if result2:
            result3 = test_smu_error_handling(address, unit_id)
        
        result4 = False
        if result2:
            result4 = test_smu_safe_output(address, unit_id)
        
        all_results.append({
            "unit_id": unit_id,
            "address": address,
            "connection": result1,
            "basic_functions": result2,
            "error_handling": result3,
            "safe_output": result4
        })
    
    print(f"\n\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    
    for result in all_results:
        print(f"\n{result['unit_id']} ({result['address']}):")
        print(f"  Connection:      {'PASS' if result['connection'] else 'FAIL'}")
        print(f"  Basic Functions: {'PASS' if result['basic_functions'] else 'FAIL'}")
        print(f"  Error Handling:  {'PASS' if result['error_handling'] else 'FAIL'}")
        print(f"  Safe Output:     {'PASS' if result['safe_output'] else 'SKIP'}")
    
    total_tests = len(all_results)
    passed_connections = sum(1 for r in all_results if r['connection'])
    
    print(f"\nOVERALL RESULTS:")
    print(f"Total SMUs tested: {total_tests}")
    print(f"Successful connections: {passed_connections}")
    
    if passed_connections == total_tests:
        print("STATUS: All SMUs operational")
    else:
        print(f"STATUS: {total_tests - passed_connections} SMU(s) have connection issues")

def main():
    """Main test execution"""
    if len(sys.argv) > 1:
        address = sys.argv[1]
        unit_id = sys.argv[2] if len(sys.argv) > 2 else "SMU_MANUAL"
        
        print("SINGLE SMU TEST MODE")
        print(f"Address: {address}")
        print(f"Unit ID: {unit_id}")
        
        test_smu_connection(address, unit_id)
        test_smu_basic_functions(address, unit_id)
        test_smu_error_handling(address, unit_id)
        test_smu_safe_output(address, unit_id)
    else:
        run_comprehensive_smu_test()

if __name__ == "__main__":
    main()