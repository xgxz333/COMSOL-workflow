import pandas as pd
from filelock import FileLock
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../comsol_workflow"))
from runtime_paths import get_workspaces_path

save_path = get_workspaces_path("param_sweep_runs")
file_name = "sweep_info"

parquet_path = os.path.join(save_path, file_name + ".parquet")
csv_path = os.path.join(save_path, file_name + ".csv")
lock_path = os.path.join(save_path, file_name + ".lock")

with FileLock(lock_path):
    df = pd.read_parquet(parquet_path)
    
    mask = (pd.to_numeric(df.get('freq_p', pd.Series(dtype=float)), errors='coerce') > 280) & (df['___status'] == 'done')
    
    # Update status to trimmed
    df.loc[mask, '___status'] = 'failed'
    
    # Save updated dataframe
    df = df.sort_index()
    df.to_parquet(parquet_path + ".tmp")
    os.replace(parquet_path + ".tmp", parquet_path)
    
    df.reset_index().to_csv(csv_path + ".tmp", index=False)
    os.replace(csv_path + ".tmp", csv_path)
    
    print(f"Updated {mask.sum()} records from 'done' to 'failed'")
