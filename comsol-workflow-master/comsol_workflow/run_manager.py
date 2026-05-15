import os
from datetime import datetime, timedelta, timezone

import pandas as pd
from filelock import FileLock

class RunManager:
  dummy_col = "___dummy"
  dummy_val = "___"
  base_cols = ["___status", "___start_utc"]

  def __init__(
    self, 
    save_path, 
    file_name,
    config_cols,
    restart_timeout="4h"
  ):
    os.makedirs(save_path, exist_ok=True)
    self.csv_path = os.path.join(save_path, file_name+".csv")
    self.parquet_path = os.path.join(save_path, file_name+".parquet")
    self.lock_path = os.path.join(save_path, file_name+".lock")

    self.reserved_cols = self.base_cols + [self.dummy_col]
    assert all(col not in self.reserved_cols for col in config_cols), f"Config should not contain reserved columns {self.reserved_cols}"
  
    self.config_cols = config_cols + [self.dummy_col]
    self.restart_timeout = pd.to_timedelta(restart_timeout)
    
    # init file
    with FileLock(self.lock_path):
      if not os.path.exists(self.parquet_path):
        df = pd.DataFrame(columns=self.base_cols)
        df.index = pd.MultiIndex.from_arrays([[] for _ in self.config_cols], names=self.config_cols)
        self.save_df_without_lock(df)
      # local cache
      self._cached_df = pd.read_parquet(self.parquet_path)

  @classmethod
  def preprocess_config(cls, config):
    return {
      **config,
      cls.dummy_col: cls.dummy_val,
    }
  
  def get_record(self, save_path, file_name, config):
    parquet_path = os.path.join(save_path, file_name+".parquet")
    lock_path = os.path.join(save_path, file_name+".lock")
    config = self.preprocess_config(config)
    idx = tuple(config[k] for k in self.config_cols)
    with FileLock(lock_path):
      df = pd.read_parquet(parquet_path)
    record = df.loc[idx]
    return record
  
  @classmethod
  def get_records_df(cls, save_path, file_name):
    parquet_path = os.path.join(save_path, file_name+".parquet")
    lock_path = os.path.join(save_path, file_name+".lock")
    with FileLock(lock_path):
      df = pd.read_parquet(parquet_path)
    return df.reset_index().drop(columns=cls.dummy_col)

  def save_df_without_lock(self, df):
    df = df.sort_index()
    df.to_parquet(self.parquet_path+".tmp")
    os.replace(self.parquet_path+".tmp", self.parquet_path)

    df.reset_index().to_csv(self.csv_path+".tmp", index=False)
    os.replace(self.csv_path+".tmp", self.csv_path)

  def register_start(self, config):
    config = self.preprocess_config(config)
    result = {
      "can_run": False,
      "reason": "unknown",
    }

    # TATAS lock: 1. check without lock
    idx = tuple(config[k] for k in self.config_cols)
    now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    if idx in self._cached_df.index:
      record = self._cached_df.loc[idx]
      if record["___status"] == "done":
        result["can_run"] = False
        result["reason"] = "done"
        return result
      if pd.to_datetime(record["___start_utc"]) + self.restart_timeout > now_utc:
        result["can_run"] = False
        result["reason"] = "running"
        return result

    # TATAS lock: 2. check with lock and update
    with FileLock(self.lock_path):
      now_utc = datetime.now(timezone.utc).replace(microsecond=0)
      now_str = now_utc.isoformat()
      df = pd.read_parquet(self.parquet_path)

      idx = tuple(config[k] for k in self.config_cols)
      if idx in df.index:
        record = df.loc[idx]
        status = record["___status"]
        if status == "done":
          # done, no run
          result["can_run"] = False
          result["reason"] = "done"
        else:
          start_utc = pd.to_datetime(record["___start_utc"])
          if start_utc + self.restart_timeout <= now_utc:
            # past restart timeout, can run
            result["can_run"] = True
            result["reason"] = "restart"
            df.at[idx, "___status"] = "running"
            df.at[idx, "___start_utc"] = now_str
            self.save_df_without_lock(df)
          else:
            # running, no run
            result["can_run"] = False
            result["reason"] = "running"
      
      else:
        # no record
        result["can_run"] = True
        result["reason"] = "new"
        df.at[idx, "___status"] = "running"
        df.at[idx, "___start_utc"] = now_str
        self.save_df_without_lock(df)
      
      self._cached_df = df.sort_index()
        
    return result

  def report_done(self, config, metrics, status="done"):
    config = self.preprocess_config(config)
    assert all(k not in self.reserved_cols for k in metrics.keys()), f"Metrics should not contain reserved columns {self.reserved_cols}"
    with FileLock(self.lock_path):
      df = pd.read_parquet(self.parquet_path)

      idx = tuple(config[col] for col in self.config_cols)

      if idx in df.index:
        start_utc = df.at[idx, "___start_utc"]
      else:
        now_utc = datetime.now(timezone.utc).replace(microsecond=0)
        start_utc = now_utc.isoformat()

      record = {
        **metrics,
        "___status": status,
        "___start_utc": start_utc,
      }

      df.loc[idx, list(record.keys())] = list(record.values())
      self.save_df_without_lock(df)
      self._cached_df = df.sort_index()
    return