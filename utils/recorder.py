
import logging
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pathlib
import time
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')


@dataclass
class PlotConfig:
    """Configuration for plot generation."""
    plot_type: str = "line"
    figsize: Tuple[int, int] = (12, 6)
    dpi: int = 150
    linewidth: float = 1.5
    alpha: float = 0.7
    grid: bool = True


@dataclass
class DataConfig:
    """Configuration for data handling and processing."""
    auto_detect_types: bool = True
    handle_missing: str = "fill"  # Options: 'fill', 'drop', 'interpolate'
    numeric_precision: int = 6
    encoding: str = "utf-8"


class UniversalRecorder:
    """
    A comprehensive recorder for test and measurement data.

    This class handles the creation of a structured directory system for test runs,
    data processing, plotting, and metadata generation.
    """
    def __init__(
        self,
        top_dir: str,
        plot_config: Optional[PlotConfig] = None,
        data_config: Optional[DataConfig] = None
    ) -> None:
        """
        Initializes the recorder.

        Args:
            top_dir (str): The root directory where all test data will be stored.
            plot_config (Optional[PlotConfig]): Configuration for plots.
            data_config (Optional[DataConfig]): Configuration for data handling.
        """
        self.top_dir = pathlib.Path(top_dir)
        self.plot_config = plot_config or PlotConfig()
        self.data_config = data_config or DataConfig()
        self._setup_directories()
        
        self.run_dir: pathlib.Path | str = ""
        self.phase_dir: pathlib.Path | str = ""
        self.cwd: pathlib.Path = self.top_dir
        
        self.current_run_info: Dict[str, Any] = {}

    def _setup_directories(self) -> None:
        """Creates the top-level directory if it doesn't exist."""
        self.top_dir.mkdir(parents=True, exist_ok=True)

    def _convert_to_dataframe(self, data: Any, headers: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Converts various data types into a pandas DataFrame.
        Supports file paths (CSV, TXT), pandas DataFrames, numpy arrays,
        dictionaries, and lists/tuples.
        """
        if isinstance(data, (str, pathlib.Path)):
            path = pathlib.Path(data)
            if path.exists() and path.is_file():
                ext = path.suffix.lower()
                if ext == '.csv':
                    return pd.read_csv(path, encoding=self.data_config.encoding)
                elif ext == '.txt':
                    return self._parse_txt_file(path)
                else: # Treat as a generic text file with one column
                    with open(path, 'r', encoding=self.data_config.encoding) as f:
                        lines = [line.rstrip('\n') for line in f]
                    return pd.DataFrame(lines, columns=['value'])

        if isinstance(data, pd.DataFrame):
            return data.copy()
        elif isinstance(data, np.ndarray):
            df = pd.DataFrame(data)
            if headers and len(headers) == df.shape[1]:
                df.columns = headers
            return df
        elif isinstance(data, dict):
            return pd.DataFrame([data]) if not all(isinstance(v, (list, tuple)) for v in data.values()) else pd.DataFrame(data)
        elif isinstance(data, (list, tuple)):
            if not data:
                return pd.DataFrame()
            if isinstance(data[0], dict):
                return pd.DataFrame(data)
            elif isinstance(data[0], (list, tuple)):
                df = pd.DataFrame(data)
                if headers and len(headers) == df.shape[1]:
                    df.columns = headers
                return df
            else: # List of scalars
                return pd.DataFrame(data, columns=['value'])
        else: # Treat as a single scalar value
            return pd.DataFrame([data], columns=['value'])

    def _parse_txt_file(self, path: pathlib.Path) -> pd.DataFrame:
        """Parses a space- or tab-delimited text file into a DataFrame."""
        with open(path, 'r', encoding=self.data_config.encoding) as f:
            raw_lines = [line.rstrip('\n') for line in f]

        lines = [line for line in raw_lines if line.strip() and not line.lstrip().startswith('#')]
        if not lines:
            return pd.DataFrame()

        first_tokens = lines[0].strip().split()
        header_detected = any(not self._is_numeric(token) for token in first_tokens)
        
        if header_detected:
            headers = first_tokens
            data_lines = lines[1:]
        else:
            headers = None
            data_lines = lines

        data_rows = [line.strip().split() for line in data_lines]
        if not data_rows:
            return pd.DataFrame()

        max_cols = max(len(row) for row in data_rows)
        padded_rows = [row + [np.nan] * (max_cols - len(row)) for row in data_rows]
        
        df = pd.DataFrame(padded_rows)
        
        if headers and len(headers) == df.shape[1]:
            df.columns = headers
        else:
            df.columns = [f"col_{i}" for i in range(max_cols)]

        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def _is_numeric(self, value: str) -> bool:
        """Helper to check if a string can be cast to a float."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def _process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies data cleaning steps based on DataConfig."""
        df = df.copy()
        
        if self.data_config.handle_missing == "drop":
            df = df.dropna()
        elif self.data_config.handle_missing == "fill":
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = df[col].fillna(df[col].mean())
                else:
                    mode_val = df[col].mode()
                    fill_val = mode_val.iloc[0] if not mode_val.empty else 'Unknown'
                    df[col] = df[col].fillna(fill_val)
        elif self.data_config.handle_missing == "interpolate":
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = df[col].interpolate()

        if self.data_config.auto_detect_types:
            for col in df.columns:
                if df[col].dtype == 'object':
                    numeric_series = pd.to_numeric(df[col], errors='coerce')
                    if not numeric_series.isna().all():
                        df[col] = numeric_series
        return df

    def test_run_start(
        self,
        workstation: str,
        dut_family: str,
        dut_batch: str,
        dut_lot: str,
        dut_wafer: str,
        dut_id: str,
        run_set_id: int = 1,
        run_id: int = 1
    ) -> bool:
        """
        Starts a new test run, creating the required directory structure.
        """
        self.run_end()
        
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        run_dir_name = f"{dut_id}_{timestamp}_S{run_set_id}_RUN{run_id:04d}"
        
        full_path = (
            self.top_dir
            / workstation
            / dut_family
            / dut_batch
            / dut_lot
            / dut_wafer
            / dut_id
            / run_dir_name
        )
        
        try:
            full_path.mkdir(parents=True, exist_ok=True)
            self.run_dir = full_path
            self.cwd = self.run_dir
            
            self.current_run_info = {
                'workstation': workstation,
                'dut_family': dut_family,
                'dut_batch': dut_batch,
                'dut_lot': dut_lot,
                'dut_wafer': dut_wafer,
                'dut_id': dut_id,
                'run_set_id': str(run_set_id),
                'run_id': str(run_id)
            }
            
            logging.info(f'TEST_RUN_START: {dut_id} run {run_id} at {self.run_dir}')
            return True
        except Exception as e:
            logging.error(f'Failed to create run directory {full_path}: {e}')
            return False

    def run_end(self):
        """Ends the current test run."""
        self.phase_end()
        if self.run_dir:
            logging.info(f'RUN_END')
            self.cwd = self.top_dir
            self.run_dir = ""
            self.current_run_info = {}

    def phase_start(self, phase_idx: int, phase_name: str) -> bool:
        """Starts a new phase within the current test run."""
        self.phase_end()
        if not self.run_dir:
            logging.error("No active run. Cannot start a phase.")
            return False
            
        phase_dir = self.run_dir / f"{phase_idx:04d}_{phase_name}"
        try:
            phase_dir.mkdir(parents=True, exist_ok=True)
            self.phase_dir = phase_dir
            self.cwd = self.phase_dir
            logging.info(f'PHASE_START: {phase_idx} - {phase_name}')
            return True
        except Exception as e:
            logging.error(f'Failed to create phase directory: {e}')
            return False

    def phase_end(self):
        """Ends the current phase."""
        if self.phase_dir:
            logging.info(f'PHASE_END')
            self.cwd = self.run_dir if self.run_dir else self.top_dir
            self.phase_dir = ""

    def create_plot(
        self,
        name: str,
        x_data: Union[List, np.ndarray, pd.Series],
        y_data: Union[List, np.ndarray, pd.Series],
        title: str = "",
        xlabel: str = "",
        ylabel: str = "",
        plot_config: Optional[PlotConfig] = None
    ) -> Optional[pathlib.Path]:
        """Creates and saves a single plot."""
        config = plot_config or self.plot_config
        
        try:
            fig, ax = plt.subplots(figsize=config.figsize)
            
            if config.plot_type == "line":
                ax.plot(x_data, y_data, linewidth=config.linewidth, alpha=config.alpha)
            else:
                ax.scatter(x_data, y_data, alpha=config.alpha)

            ax.set_title(title or "Data Plot", fontsize=12)
            ax.set_xlabel(xlabel, fontsize=10)
            ax.set_ylabel(ylabel, fontsize=10)
            
            if config.grid:
                ax.grid(True, alpha=0.3)

            filepath = self.cwd / f"{name}.png"
            fig.savefig(filepath, dpi=config.dpi, bbox_inches='tight')
            plt.close(fig)
            
            logging.info(f'Saved plot: {filepath}')
            return filepath
        except Exception as e:
            logging.error(f'Failed to create plot: {e}')
            return None

    def _generate_basic_statistics(self, df: pd.DataFrame) -> Dict:
        """Helper to generate descriptive statistics for numeric columns."""
        stats = {}
        try:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                desc = df[numeric_cols].describe()
                for col in numeric_cols:
                    stats[col] = {
                        "count": float(desc.loc['count', col]),
                        "mean": float(desc.loc['mean', col]),
                        "std": float(desc.loc['std', col]),
                        "min": float(desc.loc['min', col]),
                        "25%": float(desc.loc['25%', col]),
                        "50%": float(desc.loc['50%', col]),
                        "75%": float(desc.loc['75%', col]),
                        "max": float(desc.loc['max', col])
                    }
        except Exception as e:
            logging.warning(f"Could not generate statistics: {e}")
        return stats

    def _get_relative_path(self, filepath: pathlib.Path) -> str:
        """Gets the path of a file relative to the top_dir."""
        try:
            return filepath.relative_to(self.top_dir).as_posix()
        except ValueError:
            return str(filepath)

    def record_complete_dataset(
        self,
        name: str,
        data: Any,
        test_info: Dict,
        environment_info: Dict,
        *,
        column_names: Optional[List[str]] = None,
        testing_variable: Optional[Union[int, str]] = None,
        dependent_variables: Optional[List[Union[int, str]]] = None,
        headers: Optional[List[str]] = None,
        plot_config: Optional[PlotConfig] = None,
        parameters: Optional[Dict] = None,
        equipment_ids: Optional[str] = None,
        dut_fab: Optional[str] = None,
        dut_subchip_id: Optional[str] = None,
        dut_subcomponent_id: Optional[str] = None,
        script_version: Optional[str] = None,
        comments: Optional[str] = None,
        **csv_kwargs
    ) -> Optional[Dict]:
        """
        Records a complete dataset, including CSV, plots, and metadata.

        This is the main public method for recording data. It orchestrates
        data conversion, cleaning, saving, plotting, and metadata generation.
        """
        try:
            required_test_fields = ["test_name", "test_location", "test_user"]
            required_env_fields = ["environment_temp", "environment_humidity"]
            
            for field in required_test_fields:
                if field not in test_info:
                    raise ValueError(f"Required test_info field '{field}' is missing")
            
            for field in required_env_fields:
                if field not in environment_info:
                    raise ValueError(f"Required environment_info field '{field}' is missing")

            df = self._convert_to_dataframe(data, headers)
            
            if column_names:
                if len(column_names) != df.shape[1]:
                    raise ValueError(f"column_names length ({len(column_names)}) doesn't match DataFrame columns ({df.shape[1]})")
                df.columns = column_names
            
            df = self._process_dataframe(df)

            csv_path = self.cwd / f"{name}.csv"
            csv_params = {
                'index': False,
                'encoding': self.data_config.encoding,
                'float_format': f'%.{self.data_config.numeric_precision}g'
            }
            csv_params.update(csv_kwargs)
            df.to_csv(csv_path, **csv_params)
            logging.info(f'Saved CSV: {csv_path}')

            if df.empty:
                x_col, y_cols = None, []
            elif testing_variable is None:
                x_col = df.columns[0]
            else:
                try:
                    x_idx = int(testing_variable)
                    x_col = df.columns[x_idx]
                except (ValueError, IndexError):
                    x_col = str(testing_variable)
                    if x_col not in df.columns:
                        raise ValueError(f"Testing variable '{testing_variable}' not found in DataFrame columns.")

            if df.empty:
                y_cols = []
            elif dependent_variables is None:
                y_cols = [col for col in df.columns if col != x_col]
            else:
                y_cols = []
                for dv in dependent_variables:
                    try:
                        y_idx = int(dv)
                        y_col = df.columns[y_idx]
                    except (ValueError, IndexError):
                        y_col = str(dv)
                        if y_col not in df.columns:
                            raise ValueError(f"Dependent variable '{dv}' not found in DataFrame columns.")
                    y_cols.append(y_col)

            plot_files = []
            if x_col:
                for y_col in y_cols:
                    plot_name = f"{name}_{x_col}_vs_{y_col}"
                    plot_path = self.create_plot(
                        name=plot_name,
                        x_data=df[x_col],
                        y_data=df[y_col],
                        title=f"{y_col} vs {x_col}",
                        xlabel=x_col,
                        ylabel=y_col,
                        plot_config=plot_config
                    )
                    
                    if plot_path:
                        plot_files.append({
                            "filename": f"{plot_name}.png",
                            "relative_path": self._get_relative_path(plot_path),
                            "type": "image_png",
                            "tab_name": plot_name.replace("_", " ")
                        })
            
            metadata = {
                "test_location": test_info["test_location"],
                "test_user": test_info["test_user"],
                "test_name": test_info["test_name"],
                
                **self.current_run_info,
                
                "dut_fab": dut_fab,
                "dut_subchip_id": dut_subchip_id,
                "dut_subcomponent_id": dut_subcomponent_id,
                
                "equipment_ids": equipment_ids,
                "testing_variable_ids": x_col if x_col else None,
                "dependent_variable_ids": ", ".join(y_cols) if y_cols else None,
                
                "environment_temp": environment_info["environment_temp"],
                "environment_humidity": environment_info["environment_humidity"],
                
                "script_version": script_version,
                "comments": comments,
                
                "timestamp_generated_utc": datetime.now(timezone.utc).isoformat(),
                "data_preview": df.head(5).to_dict('records') if not df.empty else [],
                "basic_statistics": self._generate_basic_statistics(df),
                "csv_relative_path": self._get_relative_path(csv_path),
                
                "plot_files": plot_files,
                "sql_table_name": None,
                "sql_relative_path": None,
                "nd_data_tables": [],
                
                "parameters": parameters or {}
            }

            metadata_path = self.cwd / "metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            logging.info(f'Saved metadata: {metadata_path}')

            return {
                'csv_path': csv_path,
                'dataframe': df,
                'plot_files': plot_files,
                'metadata_path': metadata_path,
                'metadata': metadata
            }

        except Exception as e:
            logging.error(f'Failed to record dataset "{name}": {e}', exc_info=True)
            return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    
    data_config = DataConfig(
        auto_detect_types=True,
        handle_missing="interpolate",
        numeric_precision=4,
        encoding="utf-8"
    )
    
    plot_config = PlotConfig(
        plot_type="line",
        figsize=(14, 8),
        dpi=200,
        linewidth=2.0,
        alpha=0.8,
        grid=True
    )
    
    recorder = UniversalRecorder(
        top_dir='./test_output_demo',
        plot_config=plot_config,
        data_config=data_config
    )
    
    recorder.test_run_start(
        workstation='Autotester2',
        dut_family='SL6', 
        dut_batch='DemoBatch',
        dut_lot='DemoLot',
        dut_wafer='W01C1',
        dut_id='R1C1',
        run_set_id=1,
        run_id=1
    )
    
    recorder.phase_start(1, "Numpy_Data_Test")
    
    x_np = np.linspace(0, 2 * np.pi, 100)
    y_np = np.sin(x_np) + np.random.normal(0, 0.1, 100)
    numpy_data = np.column_stack([x_np, y_np])
    
    test_info = {"test_name": "SineWaveTest", "test_location": "Lab A", "test_user": "demo_user"}
    env_info = {"environment_temp": 25.0, "environment_humidity": 45.0}

    result1 = recorder.record_complete_dataset(
        name='sine_wave_data',
        data=numpy_data,
        test_info=test_info,
        environment_info=env_info,
        column_names=["Angle_rad", "Amplitude_V"],
        testing_variable="Angle_rad",
        dependent_variables=["Amplitude_V"],
        script_version="v1.1",
        comments="This is a test with numpy data."
    )
    if result1:
        print("Successfully recorded numpy dataset.")
    
    recorder.phase_end()
    
    recorder.phase_start(2, "Text_File_Test")

    dummy_txt_content = """# My Test Data File
1549.5  -10.1
1550.0  -9.8
1550.5  -9.9
1551.0  -10.3
1551.5  -11.0
"""
    dummy_txt_path = recorder.cwd / "sample_data.txt"
    with open(dummy_txt_path, "w") as f:
        f.write(dummy_txt_content)
        
    result2 = recorder.record_complete_dataset(
        name='optical_spectrum',
        data=str(dummy_txt_path), # Pass the path as a string
        test_info=test_info,
        environment_info=env_info,
        headers=["Wavelength_nm", "Power_dBm"],
        script_version="v1.1",
        comments="Data loaded from a text file."
    )
    if result2:
        print("Successfully recorded text file dataset.")

    recorder.phase_end()
    
    recorder.run_end()