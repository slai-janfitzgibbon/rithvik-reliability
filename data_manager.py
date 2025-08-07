
import os
import json
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class DataSavingPreferences:
    """Simple data saving preferences"""
    save_raw_measurements: bool = True  # Always enabled
    save_test_parameters: bool = True   # Always enabled
    save_session_log: bool = True       # Always enabled
    
    save_plots: bool = True
    export_json: bool = True
    
    create_date_folders: bool = True
    base_directory: str = "./test_data"

class DataManager:
    
    def __init__(self, preferences: DataSavingPreferences = None):
        self.preferences = preferences or DataSavingPreferences()
        
    def get_user_preferences(self) -> DataSavingPreferences:
        print("\n" + "="*50)
        print("DATA SAVING PREFERENCES")
        print("="*50)
        
        print("Core data (measurements, parameters, logs) is always saved.")
        print("Configure optional outputs below:\n")
        
        self.preferences.save_plots = self._get_yes_no(
            "Generate analysis plots?", self.preferences.save_plots
        )
        
        self.preferences.export_json = self._get_yes_no(
            "Export additional JSON files?", self.preferences.export_json
        )
        
        self.preferences.create_date_folders = self._get_yes_no(
            "Organize data by date folders?", self.preferences.create_date_folders
        )
        
        new_dir = input(f"Data directory [{self.preferences.base_directory}]: ").strip()
        if new_dir:
            self.preferences.base_directory = new_dir
        
        self._show_preferences_summary()
        
        return self.preferences
    
    def _get_yes_no(self, prompt: str, default: bool) -> bool:
        default_str = "y" if default else "n"
        response = input(f"  {prompt} (y/n) [{default_str}]: ").strip().lower()
        
        if not response:
            return default
        
        return response in ['y', 'yes', '1', 'true']
    
    def _show_preferences_summary(self):
        print("\n" + "="*50)
        print("DATA SAVING SUMMARY")
        print("="*50)
        
        print("ALWAYS SAVED:")
        print("   - Raw measurements (CSV)")
        print("   - Test parameters (JSON)")
        print("   - Session logs (TXT)")
        
        print("\nOPTIONAL OUTPUTS:")
        print(f"   - Analysis plots: {'Yes' if self.preferences.save_plots else 'No'}")
        print(f"   - Additional JSON: {'Yes' if self.preferences.export_json else 'No'}")
        
        print(f"\nSTORAGE:")
        print(f"   - Location: {self.preferences.base_directory}")
        print(f"   - Date folders: {'Yes' if self.preferences.create_date_folders else 'No'}")
        
    def get_data_directory(self, device_id: str, timestamp: str = None) -> str:
        base_dir = self.preferences.base_directory
        
        if self.preferences.create_date_folders:
            if timestamp:
                date_obj = datetime.fromisoformat(timestamp)
                date_folder = date_obj.strftime("%Y-%m-%d")
            else:
                date_folder = datetime.now().strftime("%Y-%m-%d")
            base_dir = os.path.join(base_dir, date_folder)
        
        device_dir = os.path.join(base_dir, device_id)
        
        return device_dir
    
    def save_preferences(self, filename: str = "./data_preferences.json"):
        try:
            import dataclasses
            prefs_dict = dataclasses.asdict(self.preferences)
            with open(filename, 'w') as f:
                json.dump(prefs_dict, f, indent=2)
            print(f"Preferences saved to {filename}")
        except Exception as e:
            print(f"Could not save preferences: {e}")
    
    def load_preferences(self, filename: str = "./data_preferences.json") -> bool:
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    prefs_dict = json.load(f)
                
                for key, value in prefs_dict.items():
                    if hasattr(self.preferences, key):
                        setattr(self.preferences, key, value)
                
                print(f"Preferences loaded from {filename}")
                return True
        except Exception as e:
            print(f"Could not load preferences: {e}")
        
        return False
    
    def get_quick_presets(self) -> Dict[str, DataSavingPreferences]:
        presets = {
            "minimal": DataSavingPreferences(
                save_plots=False,
                export_json=False,
                create_date_folders=False
            ),
            "standard": DataSavingPreferences(
                save_plots=True,
                export_json=True,
                create_date_folders=True
            )
        }
        
        return presets
    
    def select_preset(self) -> DataSavingPreferences:
        presets = self.get_quick_presets()
        
        print("\n" + "="*40)
        print("DATA SAVING PRESETS")
        print("="*40)
        
        print("1. Minimal  - Core data only (CSV)")
        print("2. Standard - Core data + plots + JSON")  
        print("3. Custom   - Configure manually")
        
        choice = input("\nSelect preset [2]: ").strip()
        
        if choice == "1":
            self.preferences = presets["minimal"]
            print("Using Minimal preset")
        elif choice == "3":
            return self.get_user_preferences()
        else:  # Default to standard
            self.preferences = presets["standard"]
            print("Using Standard preset")
        
        self._show_preferences_summary()
        return self.preferences
    
    def create_data_structure(self, device_id: str, timestamp: str = None) -> Dict[str, str]:
        base_dir = self.get_data_directory(device_id, timestamp)
        
        os.makedirs(base_dir, exist_ok=True)
        
        paths = {"base": base_dir}
        
        if self.preferences.save_plots:
            plots_dir = os.path.join(base_dir, "plots")
            os.makedirs(plots_dir, exist_ok=True)
            paths["plots"] = plots_dir
        
        return paths
    
    def get_save_summary(self, paths: Dict[str, str]) -> str:
        summary = []
        base_dir = paths["base"]
        
        summary.append("DATA SAVING PLAN:")
        summary.append(f"   Directory: {base_dir}")
        
        summary.append("\nFiles to be saved:")
        summary.append("   - Raw measurements (CSV)")
        summary.append("   - Test parameters (JSON)") 
        summary.append("   - Session log (TXT)")
        
        if self.preferences.save_plots:
            summary.append("   - Analysis plots (PNG)")
        
        if self.preferences.export_json:
            summary.append("   - Additional JSON exports")
        
        return "\n".join(summary)

def test_data_manager():
    print("Data Manager Test")
    print("="*50)
    
    manager = DataManager()
    
    if manager.load_preferences():
        print("Using saved preferences")
    else:
        print("No saved preferences found, using defaults")
    
    manager._show_preferences_summary()
    
    device_id = "DEVICE_001"
    
    paths = manager.create_data_structure(device_id)
    print(f"\nCreated directory structure:")
    for key, path in paths.items():
        print(f"  {key}: {path}")
    
    summary = manager.get_save_summary(paths)
    print(f"\n{summary}")

if __name__ == "__main__":
    test_data_manager()