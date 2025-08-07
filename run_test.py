"""
Simple launcher for the production test system
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    print("FAU Production Test System")
    print("=" * 50)
    print("1. Interactive Test System (Recommended)")
    print("2. Direct Customer Test Flow")
    print("3. Exit")
    
    choice = input("\nSelect option [1]: ").strip()
    
    if choice == "2":
        print("\nLaunching direct customer test flow...")
        from Test_flow import run_test
        success = run_test()
        sys.exit(0 if success else 1)
    
    elif choice == "3":
        print("Goodbye!")
        sys.exit(0)
    
    else:  # Default to interactive system
        print("\nLaunching interactive test system...")
        from interactive_test_system import InteractiveTestSystem
        system = InteractiveTestSystem()
        system.run()