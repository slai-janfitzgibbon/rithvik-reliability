#!/usr/bin/env python3

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class DataSavingPreferences:
    """User preferences for data saving"""
    # Core data (always saved for safety)
    save_raw_measurements: bool = True  # Cannot be disabled
    save_test_parameters: bool = True   # Cannot be disabled
    save_session_log: bool = True       # Cannot be disabled
    
    # Analysis and plots (user configurable)
    save_analysis_plots: bool = True
    save_summary_plots: bool = True
    save_statistical_analysis: bool = True
    save_derived_parameters: bool = True
    
    # Export formats (user configurable)
    export_csv: bool = True
    export_excel: bool = False
    export_json: bool = True
    export_matlab: bool = False
    
    # Data organization
    create_date_folders: bool = True
    create_operator_folders: bool = False
    compress_old_data: bool = False
    
    # Storage options
    base_directory: str = "./test_data"
    backup_enabled: bool = True
    backup_directory: str = "./backup"
    
    # Retention policy
    auto_cleanup_days: int = 0  # 0 = never auto-delete
    max_storage_mb: int = 0     # 0 = unlimited

class DataManager:
    """Manages data saving preferences and operations"""
    
    def __init__(self, preferences: DataSavingPreferences = None):
        self.preferences = preferences or DataSavingPreferences()
        self.session_files = []
        
    def get_user_preferences(self) -> DataSavingPreferences:
        """Interactive setup of data saving preferences"""
        print("\n" + "="*60)
        print("DATA SAVING PREFERENCES")
        print("="*60)
        
        print("📁 Core data (measurements, parameters, logs) is ALWAYS saved for safety")
        print("   You can configure additional analysis and export options below.\n")
        
        # Analysis options
        print("📊 Analysis & Visualization:")
        self.preferences.save_analysis_plots = self._get_yes_no(
            "Generate detailed analysis plots?", self.preferences.save_analysis_plots
        )
        
        self.preferences.save_summary_plots = self._get_yes_no(
            "Generate summary overview plots?", self.preferences.save_summary_plots
        )
        
        self.preferences.save_statistical_analysis = self._get_yes_no(
            "Perform statistical analysis (mean, std, trends)?", self.preferences.save_statistical_analysis
        )
        
        self.preferences.save_derived_parameters = self._get_yes_no(
            "Calculate derived parameters (efficiency, stability)?", self.preferences.save_derived_parameters
        )
        
        # Export formats
        print("\n💾 Export Formats:")
        print("   CSV format is always enabled")
        
        self.preferences.export_excel = self._get_yes_no(
            "Export Excel spreadsheets (.xlsx)?", self.preferences.export_excel
        )
        
        self.preferences.export_json = self._get_yes_no(
            "Export JSON data files?", self.preferences.export_json
        )
        
        self.preferences.export_matlab = self._get_yes_no(
            "Export MATLAB data files (.mat)?", self.preferences.export_matlab
        )
        
        # Storage organization
        print("\n📂 Data Organization:")
        self.preferences.create_date_folders = self._get_yes_no(
            "Organize data by date folders (YYYY/MM/DD)?", self.preferences.create_date_folders
        )
        
        self.preferences.create_operator_folders = self._get_yes_no(
            "Create separate folders per operator?", self.preferences.create_operator_folders
        )
        
        # Storage location
        print("\n💽 Storage Location:")
        new_dir = input(f"Data directory [{self.preferences.base_directory}]: ").strip()
        if new_dir:
            self.preferences.base_directory = new_dir
        
        # Backup options
        self.preferences.backup_enabled = self._get_yes_no(
            "Enable automatic backup?", self.preferences.backup_enabled
        )
        
        if self.preferences.backup_enabled:
            backup_dir = input(f"Backup directory [{self.preferences.backup_directory}]: ").strip()
            if backup_dir:
                self.preferences.backup_directory = backup_dir
        
        # Show summary
        self._show_preferences_summary()
        
        return self.preferences
    
    def _get_yes_no(self, prompt: str, default: bool) -> bool:
        """Get yes/no response with default"""
        default_str = "y" if default else "n"
        response = input(f"  {prompt} (y/n) [{default_str}]: ").strip().lower()
        
        if not response:
            return default
        
        return response in ['y', 'yes', '1', 'true']
    
    def _show_preferences_summary(self):
        """Show summary of selected preferences"""
        print("\n" + "="*60)
        print("DATA SAVING SUMMARY")
        print("="*60)
        
        print("✅ ALWAYS SAVED (Safety):")
        print("   • Raw measurement data")
        print("   • Test parameters & settings")
        print("   • Session logs & timestamps")
        print("   • CSV data exports")
        
        print("\n📊 ANALYSIS & PLOTS:")
        print(f"   • Detailed analysis plots: {'✅' if self.preferences.save_analysis_plots else '❌'}")
        print(f"   • Summary overview plots: {'✅' if self.preferences.save_summary_plots else '❌'}")
        print(f"   • Statistical analysis: {'✅' if self.preferences.save_statistical_analysis else '❌'}")
        print(f"   • Derived parameters: {'✅' if self.preferences.save_derived_parameters else '❌'}")
        
        print("\n💾 EXPORT FORMATS:")
        print("   • CSV files: ✅ (Always)")
        print(f"   • Excel files (.xlsx): {'✅' if self.preferences.export_excel else '❌'}")
        print(f"   • JSON files: {'✅' if self.preferences.export_json else '❌'}")
        print(f"   • MATLAB files (.mat): {'✅' if self.preferences.export_matlab else '❌'}")
        
        print(f"\n📂 STORAGE:")
        print(f"   • Location: {self.preferences.base_directory}")
        print(f"   • Date folders: {'✅' if self.preferences.create_date_folders else '❌'}")
        print(f"   • Operator folders: {'✅' if self.preferences.create_operator_folders else '❌'}")
        print(f"   • Backup: {'✅' if self.preferences.backup_enabled else '❌'}")
        
    def get_data_directory(self, device_id: str, operator: str = None, timestamp: str = None) -> str:
        """Generate appropriate data directory based on preferences"""
        base_dir = self.preferences.base_directory
        
        # Add date folder if enabled
        if self.preferences.create_date_folders:
            if timestamp:
                date_obj = datetime.fromisoformat(timestamp)
                date_folder = date_obj.strftime("%Y/%m/%d")
            else:
                date_folder = datetime.now().strftime("%Y/%m/%d")
            base_dir = os.path.join(base_dir, date_folder)
        
        # Add operator folder if enabled
        if self.preferences.create_operator_folders and operator:
            base_dir = os.path.join(base_dir, operator)
        
        # Add device folder
        device_dir = os.path.join(base_dir, device_id)
        
        return device_dir
    
    def save_preferences(self, filename: str = "./data_preferences.json"):
        """Save preferences to file"""
        try:
            import dataclasses
            prefs_dict = dataclasses.asdict(self.preferences)
            with open(filename, 'w') as f:
                json.dump(prefs_dict, f, indent=2)
            print(f"✅ Preferences saved to {filename}")
        except Exception as e:
            print(f"❌ Could not save preferences: {e}")
    
    def load_preferences(self, filename: str = "./data_preferences.json") -> bool:
        """Load preferences from file"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    prefs_dict = json.load(f)
                
                # Update preferences object
                for key, value in prefs_dict.items():
                    if hasattr(self.preferences, key):
                        setattr(self.preferences, key, value)
                
                print(f"✅ Preferences loaded from {filename}")
                return True
        except Exception as e:
            print(f"❌ Could not load preferences: {e}")
        
        return False
    
    def get_quick_presets(self) -> Dict[str, DataSavingPreferences]:
        """Get predefined data saving presets"""
        presets = {
            "minimal": DataSavingPreferences(
                save_analysis_plots=False,
                save_summary_plots=True,
                save_statistical_analysis=False,
                save_derived_parameters=False,
                export_excel=False,
                export_json=False,
                export_matlab=False,
                create_date_folders=False
            ),
            "standard": DataSavingPreferences(
                save_analysis_plots=True,
                save_summary_plots=True,
                save_statistical_analysis=True,
                save_derived_parameters=True,
                export_excel=False,
                export_json=True,
                export_matlab=False,
                create_date_folders=True
            ),
            "complete": DataSavingPreferences(
                save_analysis_plots=True,
                save_summary_plots=True,
                save_statistical_analysis=True,
                save_derived_parameters=True,
                export_excel=True,
                export_json=True,
                export_matlab=True,
                create_date_folders=True,
                create_operator_folders=True,
                backup_enabled=True
            )
        }
        
        return presets
    
    def select_preset(self) -> DataSavingPreferences:
        """Interactive preset selection"""
        presets = self.get_quick_presets()
        
        print("\n" + "="*60)
        print("QUICK DATA SAVING PRESETS")
        print("="*60)
        
        print("1. Minimal    - Core data only, basic plots, CSV export")
        print("2. Standard   - Analysis + plots, JSON export, date folders")  
        print("3. Complete   - All features enabled, full backup")
        print("4. Custom     - Configure your own preferences")
        
        choice = input("\nSelect preset [2]: ").strip()
        
        if choice == "1":
            self.preferences = presets["minimal"]
            print("✅ Using Minimal preset")
        elif choice == "3":
            self.preferences = presets["complete"] 
            print("✅ Using Complete preset")
        elif choice == "4":
            return self.get_user_preferences()
        else:  # Default to standard
            self.preferences = presets["standard"]
            print("✅ Using Standard preset")
        
        self._show_preferences_summary()
        return self.preferences
    
    def create_data_structure(self, device_id: str, operator: str = None, timestamp: str = None) -> Dict[str, str]:
        """Create directory structure and return paths"""
        base_dir = self.get_data_directory(device_id, operator, timestamp)
        
        # Create main directory
        os.makedirs(base_dir, exist_ok=True)
        
        paths = {"base": base_dir}
        
        # Create subdirectories based on preferences
        if self.preferences.save_analysis_plots or self.preferences.save_summary_plots:
            plots_dir = os.path.join(base_dir, "plots")
            os.makedirs(plots_dir, exist_ok=True)
            paths["plots"] = plots_dir
        
        if self.preferences.export_excel or self.preferences.export_matlab:
            exports_dir = os.path.join(base_dir, "exports")
            os.makedirs(exports_dir, exist_ok=True)
            paths["exports"] = exports_dir
        
        if self.preferences.save_statistical_analysis:
            analysis_dir = os.path.join(base_dir, "analysis")
            os.makedirs(analysis_dir, exist_ok=True)
            paths["analysis"] = analysis_dir
        
        # Create backup directory if enabled
        if self.preferences.backup_enabled:
            backup_dir = os.path.join(self.preferences.backup_directory, device_id)
            os.makedirs(backup_dir, exist_ok=True)
            paths["backup"] = backup_dir
        
        return paths
    
    def get_save_summary(self, paths: Dict[str, str]) -> str:
        """Generate summary of what will be saved"""
        summary = []
        base_dir = paths["base"]
        
        summary.append("📁 DATA SAVING PLAN:")
        summary.append(f"   Base Directory: {base_dir}")
        
        summary.append("\n💾 Files to be saved:")
        summary.append("   • Raw measurements (CSV) - ALWAYS")
        summary.append("   • Test parameters (JSON) - ALWAYS") 
        summary.append("   • Session log (TXT) - ALWAYS")
        
        if self.preferences.save_analysis_plots:
            summary.append("   • Detailed analysis plots (PNG)")
        
        if self.preferences.save_summary_plots:
            summary.append("   • Summary plots (PNG)")
        
        if self.preferences.export_excel:
            summary.append("   • Excel spreadsheet (XLSX)")
        
        if self.preferences.export_json:
            summary.append("   • JSON data files")
        
        if self.preferences.export_matlab:
            summary.append("   • MATLAB data files (MAT)")
        
        if self.preferences.save_statistical_analysis:
            summary.append("   • Statistical analysis report")
        
        if self.preferences.backup_enabled:
            summary.append(f"   • Backup copy in: {paths.get('backup', 'N/A')}")
        
        return "\n".join(summary)

def test_data_manager():
    """Test the data manager functionality"""
    print("Data Manager Test")
    print("="*50)
    
    manager = DataManager()
    
    # Load existing preferences
    if manager.load_preferences():
        print("Using saved preferences")
    else:
        print("No saved preferences found, using defaults")
    
    # Show current preferences
    manager._show_preferences_summary()
    
    # Test directory creation
    device_id = "TEST_DEVICE_001"
    operator = "TestUser"
    
    paths = manager.create_data_structure(device_id, operator)
    print(f"\nCreated directory structure:")
    for key, path in paths.items():
        print(f"  {key}: {path}")
    
    # Show save summary
    summary = manager.get_save_summary(paths)
    print(f"\n{summary}")

if __name__ == "__main__":
    test_data_manager()