import os
import sys
import time
import random
import tempfile
from multiprocessing import freeze_support, get_context

import numpy as np
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "../comsol_workflow"))
from run_manager import RunManager


# ── helpers ───────────────────────────────────────────────────────────────────

def make_manager(tmpdir, config_cols=None, restart_timeout="4h", file_name="test_runs"):
    if config_cols is None:
        config_cols = ["param_a", "param_b"]
    return RunManager(
        save_path=tmpdir,
        file_name=file_name,
        config_cols=config_cols,
        restart_timeout=restart_timeout,
    )


# ── multiprocessing worker (module-level required for pickling) ───────────────

def _worker(args):
    """Returns (worker_id, 'completed'|'blocked', reason)."""
    save_path, file_name, config, config_cols, worker_id = args
    manager = RunManager(save_path, file_name, config_cols=config_cols)
    result = manager.register_start(config)
    if result["can_run"]:
        task_score = float(worker_id) * 100.0
        manager.report_done(config, {"worker_id": float(worker_id), "task_score": task_score})
        return (worker_id, "completed", result["reason"])
    else:
        return (worker_id, "blocked", result["reason"])


def _worker_shared_tasks(args):
    """Worker that iterates all tasks and runs any it can register."""
    save_path, file_name, all_configs, config_cols, worker_id = args
    completed = []
    manager = RunManager(save_path, file_name, config_cols=config_cols)
    for cfg in all_configs:
        result = manager.register_start(cfg)
        if result["can_run"]:
            task_score = float(worker_id) * 100.0 + float(cfg["task_id"])
            manager.report_done(cfg, {"worker_id": float(worker_id), "task_score": task_score})
            completed.append(cfg["task_id"])
    return (worker_id, completed)


# ── initialisation ────────────────────────────────────────────────────────────

def test_initialization_creates_files():
    """RunManager creates parquet, CSV, and lock files on first init."""
    with tempfile.TemporaryDirectory() as tmpdir:
        make_manager(tmpdir)
        assert os.path.exists(os.path.join(tmpdir, "test_runs.parquet")), \
            "Parquet file not created on init"
        assert os.path.exists(os.path.join(tmpdir, "test_runs.csv")), \
            "CSV file not created on init"


def test_initialization_starts_empty():
    """Fresh RunManager has zero records."""
    with tempfile.TemporaryDirectory() as tmpdir:
        make_manager(tmpdir)
        df = RunManager.get_records_df(tmpdir, "test_runs")
        assert len(df) == 0, f"Expected empty DataFrame, got {len(df)} rows"


def test_initialization_idempotent():
    """Creating a second RunManager at the same path must not wipe existing data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        m.register_start({"param_a": "x", "param_b": "y"})
        make_manager(tmpdir)  # second manager, same path
        df = RunManager.get_records_df(tmpdir, "test_runs")
        assert len(df) == 1, "Second init must not delete existing records"


# ── register_start: new run ───────────────────────────────────────────────────

def test_register_start_returns_dict_with_required_keys():
    """register_start always returns a dict with 'can_run' and 'reason' keys."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        result = m.register_start({"param_a": "1", "param_b": "2"})
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "can_run" in result, "Result should have 'can_run' key"
        assert "reason" in result, "Result should have 'reason' key"


def test_register_new_can_run():
    """First registration of a config returns can_run=True, reason='new'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        result = m.register_start({"param_a": "1", "param_b": "2"})
        assert result["can_run"] is True, f"Expected can_run=True, got {result}"
        assert result["reason"] == "new", f"Expected reason='new', got {result['reason']}"


def test_register_new_sets_running_status():
    """After register_start the record status must be 'running'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        m.register_start({"param_a": "1", "param_b": "2"})
        df = RunManager.get_records_df(tmpdir, "test_runs")
        assert df.iloc[0]["___status"] == "running", \
            f"Expected 'running', got {df.iloc[0]['___status']}"


def test_register_new_records_start_utc():
    """After register_start, ___start_utc must be a parseable UTC timestamp."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        m.register_start({"param_a": "1", "param_b": "2"})
        df = RunManager.get_records_df(tmpdir, "test_runs")
        ts = pd.to_datetime(df.iloc[0]["___start_utc"])
        assert ts is not pd.NaT, "start_utc is NaT"


# ── register_start: running (within timeout) ──────────────────────────────────

def test_register_while_running_blocks():
    """Re-registering within the timeout returns can_run=False, reason='running'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir, restart_timeout="4h")
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        result = m.register_start(cfg)
        assert result["can_run"] is False, f"Expected blocked, got {result}"
        assert result["reason"] == "running", f"Expected 'running', got {result['reason']}"


def test_register_within_timeout_does_not_update_start_utc():
    """Blocked re-registration must NOT change the original start_utc."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir, restart_timeout="4h")
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        t1 = pd.to_datetime(
            RunManager.get_records_df(tmpdir, "test_runs").iloc[0]["___start_utc"]
        )
        time.sleep(1.1)
        m.register_start(cfg)  # blocked
        t2 = pd.to_datetime(
            RunManager.get_records_df(tmpdir, "test_runs").iloc[0]["___start_utc"]
        )
        assert t1 == t2, "start_utc should not change on a blocked registration"


# ── register_start: past timeout (restart) ────────────────────────────────────

def test_restart_after_timeout():
    """A run stuck in 'running' past the timeout allows re-registration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir, restart_timeout="1s")
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        time.sleep(1.1)
        result = m.register_start(cfg)
        assert result["can_run"] is True, f"Expected can_run=True after timeout, got {result}"
        assert result["reason"] == "restart", f"Expected 'restart', got {result['reason']}"


def test_restart_updates_start_utc():
    """After a restart registration, ___start_utc must advance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir, restart_timeout="1s")
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        t1 = pd.to_datetime(
            RunManager.get_records_df(tmpdir, "test_runs").iloc[0]["___start_utc"]
        )
        time.sleep(1.1)
        m.register_start(cfg)
        t2 = pd.to_datetime(
            RunManager.get_records_df(tmpdir, "test_runs").iloc[0]["___start_utc"]
        )
        assert t2 > t1, f"start_utc not updated on restart: {t1} vs {t2}"


def test_restart_sets_running_status_again():
    """After a restart registration, status must go back to 'running'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir, restart_timeout="1s")
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        time.sleep(1.1)
        m.register_start(cfg)
        df = RunManager.get_records_df(tmpdir, "test_runs")
        assert df.iloc[0]["___status"] == "running"


def test_timeout_all_configs_together():
    """Register many configs, wait for timeout, then all should restart."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir, restart_timeout="1s")
        configs = [{"param_a": str(i), "param_b": "y"} for i in range(5)]
        for cfg in configs:
            m.register_start(cfg)
        time.sleep(1.1)
        for cfg in configs:
            result = m.register_start(cfg)
            assert result["can_run"] is True, \
                f"Expected restart for {cfg}, got {result}"
            assert result["reason"] == "restart"


# ── register_start: done ──────────────────────────────────────────────────────

def test_done_blocks_rerun():
    """After report_done, register_start must return can_run=False, reason='done'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        m.report_done(cfg, {"score": 1.0})
        result = m.register_start(cfg)
        assert result["can_run"] is False, f"Expected blocked, got {result}"
        assert result["reason"] == "done", f"Expected 'done', got {result['reason']}"


def test_done_blocks_even_after_timeout():
    """A 'done' record must never be restarted, even past the timeout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir, restart_timeout="1s")
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        m.report_done(cfg, {})
        time.sleep(1.1)
        result = m.register_start(cfg)
        assert result["can_run"] is False, \
            "A 'done' run must never be restarted, regardless of timeout"
        assert result["reason"] == "done"


# ── report_done ───────────────────────────────────────────────────────────────

def test_report_done_stores_metrics():
    """report_done must persist all supplied metric values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        m.report_done(cfg, {"score": 99.5, "loss": 0.01})
        df = RunManager.get_records_df(tmpdir, "test_runs")
        assert np.isclose(df.iloc[0]["score"], 99.5), f"score mismatch: {df.iloc[0]['score']}"
        assert np.isclose(df.iloc[0]["loss"], 0.01), f"loss mismatch: {df.iloc[0]['loss']}"


def test_report_done_status_done():
    """Default status after report_done is 'done'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        m.report_done(cfg, {})
        df = RunManager.get_records_df(tmpdir, "test_runs")
        assert df.iloc[0]["___status"] == "done"


def test_report_done_custom_status_failed():
    """report_done with status='failed' saves that status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        m.report_done(cfg, {}, status="failed")
        df = RunManager.get_records_df(tmpdir, "test_runs")
        assert df.iloc[0]["___status"] == "failed", \
            f"Expected 'failed', got {df.iloc[0]['___status']}"


def test_report_done_preserves_start_utc():
    """report_done must not alter the original ___start_utc."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        t_before = pd.to_datetime(
            RunManager.get_records_df(tmpdir, "test_runs").iloc[0]["___start_utc"]
        )
        time.sleep(1.1)
        m.report_done(cfg, {"v": 1.0})
        t_after = pd.to_datetime(
            RunManager.get_records_df(tmpdir, "test_runs").iloc[0]["___start_utc"]
        )
        assert t_before == t_after, "report_done must keep the original start_utc"


def test_report_done_overwrite_metrics():
    """Calling report_done twice on the same config overwrites with latest metrics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        m.report_done(cfg, {"score": 1.0, "version": 1}, status="done")
        # Bypass the done-block by calling report_done directly a second time
        m.report_done(cfg, {"score": 2.0, "version": 2}, status="done")
        df = RunManager.get_records_df(tmpdir, "test_runs")
        assert len(df) == 1, "Should still be exactly one record"
        assert np.isclose(df.iloc[0]["score"], 2.0), \
            "Second report_done should overwrite score"
        assert df.iloc[0]["version"] == 2, \
            "Second report_done should overwrite version"


def test_report_done_without_prior_register():
    """report_done on an un-registered config still saves the record correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        cfg = {"param_a": "5", "param_b": "6"}
        m.report_done(cfg, {"score": 0.0}, status="done")
        df = RunManager.get_records_df(tmpdir, "test_runs")
        assert len(df) == 1
        assert df.iloc[0]["___status"] == "done"
        assert np.isclose(df.iloc[0]["score"], 0.0)
        result = m.register_start(cfg)
        assert result["can_run"] is False and result["reason"] == "done"


def test_metrics_with_nan():
    """NaN metric values round-trip correctly through parquet."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        m.report_done(cfg, {"score": float("nan"), "loss": 0.5})
        df = RunManager.get_records_df(tmpdir, "test_runs")
        assert np.isnan(df.iloc[0]["score"]), "NaN metric should round-trip as NaN"
        assert np.isclose(df.iloc[0]["loss"], 0.5)


def test_reported_values_roundtrip():
    """Metrics passed to report_done are retrievable with full accuracy
    via both get_records_df and get_record."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        configs_and_metrics = [
            (
                {"param_a": str(i), "param_b": str(i * 10)},
                {"score": float(i) * 1.23456789, "loss": float(i) * 0.0001, "step": float(i)},
            )
            for i in range(5)
        ]
        for cfg, metrics in configs_and_metrics:
            m.register_start(cfg)
            m.report_done(cfg, metrics)

        df = RunManager.get_records_df(tmpdir, "test_runs")
        assert len(df) == len(configs_and_metrics), \
            f"Expected {len(configs_and_metrics)} records, got {len(df)}"

        for cfg, metrics in configs_and_metrics:
            record = m.get_record(tmpdir, "test_runs", cfg)
            for key, expected in metrics.items():
                actual = record[key]
                assert np.isclose(actual, expected, equal_nan=True), \
                    f"Metric '{key}' mismatch for {cfg}: expected {expected}, got {actual}"

# ── failed status + timeout ───────────────────────────────────────────────────

def test_failed_run_restarts_after_timeout():
    """A 'failed' (non-done) run may be restarted after the timeout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir, restart_timeout="1s")
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        m.report_done(cfg, {}, status="failed")
        time.sleep(1.1)
        result = m.register_start(cfg)
        assert result["can_run"] is True, \
            f"Expected can_run=True for failed run past timeout, got {result}"
        assert result["reason"] == "restart"


def test_failed_run_blocked_within_timeout():
    """A 'failed' run within the timeout must not be restarted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir, restart_timeout="10s")
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        m.report_done(cfg, {}, status="failed")
        result = m.register_start(cfg)
        assert result["can_run"] is False
        assert result["reason"] == "running"


# ── multiple configs ──────────────────────────────────────────────────────────

def test_multiple_configs_tracked_independently():
    """Multiple distinct configs each get their own record."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        configs = [
            {"param_a": "1", "param_b": "A"},
            {"param_a": "1", "param_b": "B"},
            {"param_a": "2", "param_b": "A"},
        ]
        for cfg in configs:
            result = m.register_start(cfg)
            assert result["can_run"] is True, f"Expected new run for {cfg}"
        df = RunManager.get_records_df(tmpdir, "test_runs")
        assert len(df) == 3, f"Expected 3 records, got {len(df)}"


def test_done_one_does_not_affect_others():
    """Completing one config must not change the status of other configs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        cfg1 = {"param_a": "1", "param_b": "A"}
        cfg2 = {"param_a": "2", "param_b": "B"}
        m.register_start(cfg1)
        m.register_start(cfg2)
        m.report_done(cfg1, {"score": 1.0})
        result2 = m.register_start(cfg2)
        assert result2["can_run"] is False
        assert result2["reason"] == "running"


def test_many_configs_sequential():
    """Register and complete 50 configs sequentially; all must end as 'done'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        N = 50
        for i in range(N):
            cfg = {"param_a": str(i), "param_b": str(i * 2)}
            m.register_start(cfg)
            m.report_done(cfg, {"idx": float(i)})
        df = RunManager.get_records_df(tmpdir, "test_runs")
        assert len(df) == N, f"Expected {N} records, got {len(df)}"
        assert (df["___status"] == "done").all(), "Not all records are 'done'"


def test_high_volume_param_sweep():
    """Simulate a realistic parameter sweep grid; all configs registered and completed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = RunManager(
            save_path=tmpdir,
            file_name="sweep",
            config_cols=["model", "lr", "batch_size"],
        )
        configs = [
            {"model": model, "lr": lr, "batch_size": bs}
            for model in ["resnet18", "resnet50", "vgg16"]
            for lr in ["0.001", "0.01", "0.1"]
            for bs in ["32", "64", "128"]
        ]
        for cfg in configs:
            result = m.register_start(cfg)
            assert result["can_run"] is True
            assert result["reason"] == "new", f"Expected 'new', got {result['reason']}"

        for cfg in configs:
            m.report_done(cfg, {"accuracy": 0.9})

        df = RunManager.get_records_df(tmpdir, "sweep")
        assert len(df) == len(configs), f"Expected {len(configs)} records, got {len(df)}"
        assert (df["___status"] == "done").all(), "Not all records are 'done'"

        for cfg in configs:
            result = m.register_start(cfg)
            assert result["can_run"] is False
            assert result["reason"] == "done"


# ── get_record / get_records_df ───────────────────────────────────────────────

def test_get_records_df_excludes_dummy_col():
    """get_records_df must strip the internal dummy column."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        m.register_start({"param_a": "1", "param_b": "2"})
        df = RunManager.get_records_df(tmpdir, "test_runs")
        assert RunManager.dummy_col not in df.columns, \
            f"Dummy column {RunManager.dummy_col!r} should be absent from get_records_df"


def test_get_records_df_contains_config_and_status_cols():
    """get_records_df output must include config columns and status columns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        m.register_start({"param_a": "1", "param_b": "2"})
        df = RunManager.get_records_df(tmpdir, "test_runs")
        for col in ("param_a", "param_b", "___status", "___start_utc"):
            assert col in df.columns, f"Column {col!r} missing from get_records_df"


def test_get_record_returns_correct_row():
    """get_record fetches the right row for a given config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        cfg = {"param_a": "7", "param_b": "8"}
        m.register_start(cfg)
        m.report_done(cfg, {"score": 42.0})
        record = m.get_record(tmpdir, "test_runs", cfg)
        assert np.isclose(record["score"], 42.0), f"score mismatch: {record['score']}"
        assert record["___status"] == "done"


# ── validation guards ─────────────────────────────────────────────────────────

def test_reserved_config_cols_raise():
    """Passing any reserved column as a config_col must raise AssertionError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        for col in RunManager.base_cols + [RunManager.dummy_col]:
            try:
                RunManager(
                    save_path=tmpdir,
                    file_name="bad",
                    config_cols=[col],
                )
                assert False, f"Should have raised for reserved config_col {col!r}"
            except AssertionError:
                pass  # expected


def test_reserved_metric_keys_raise():
    """Passing reserved column names as metric keys must raise AssertionError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        m.register_start({"param_a": "1", "param_b": "2"})
        for col in RunManager.base_cols + [RunManager.dummy_col]:
            try:
                m.report_done({"param_a": "1", "param_b": "2"}, {col: 1.0})
                assert False, f"Should have raised for reserved metric key {col!r}"
            except AssertionError:
                pass  # expected


# ── atomic I/O and file consistency ──────────────────────────────────────────

def test_no_tmp_files_left_after_operations():
    """No .tmp files should remain after normal register/report_done cycles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        m.report_done(cfg, {"score": 1.0})
        tmp_files = [f for f in os.listdir(tmpdir) if f.endswith(".tmp")]
        assert not tmp_files, f"Leftover .tmp files: {tmp_files}"


def test_csv_and_parquet_consistent():
    """CSV and parquet files must agree on row count and columns after operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        for i in range(5):
            cfg = {"param_a": str(i), "param_b": "x"}
            m.register_start(cfg)
            m.report_done(cfg, {"val": float(i)})
        df_parquet = pd.read_parquet(os.path.join(tmpdir, "test_runs.parquet"))
        df_csv = pd.read_csv(os.path.join(tmpdir, "test_runs.csv"))
        assert len(df_parquet) == len(df_csv), \
            f"Row count mismatch: parquet={len(df_parquet)}, csv={len(df_csv)}"
        assert set(df_parquet.reset_index().columns) == set(df_csv.columns), \
            "Column mismatch between parquet and CSV"


# ── multiprocessing ───────────────────────────────────────────────────────────

def test_multiprocessing_independent_configs():
    """Each worker has a unique config; all should complete with reason='new',
    and re-submission should be blocked with reason='done'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_cols = ["task_id", "model"]
        configs = [{"task_id": str(i), "model": "resnet"} for i in range(10)]
        tasks = [
            (tmpdir, "mp_runs", cfg, config_cols, i)
            for i, cfg in enumerate(configs)
        ]
        with get_context("spawn").Pool(processes=4) as pool:
            results = pool.map(_worker, tasks)

        completed = [r for r in results if r[1] == "completed"]
        blocked   = [r for r in results if r[1] == "blocked"]
        assert len(completed) == len(configs), \
            f"Expected all {len(configs)} to complete, got {len(completed)}"
        assert len(blocked) == 0, f"Expected 0 blocked, got {len(blocked)}"
        for _, _, reason in completed:
            assert reason == "new", \
                f"First run reason should be 'new', got '{reason}'"

        # Verify stored metrics match the reporting worker
        df = RunManager.get_records_df(tmpdir, "mp_runs")
        for worker_id, _, _ in completed:
            row = df[df["task_id"] == str(worker_id)]
            assert len(row) == 1
            assert np.isclose(row.iloc[0]["worker_id"], float(worker_id)), \
                f"task_id={worker_id}: worker_id mismatch"
            assert np.isclose(row.iloc[0]["task_score"], float(worker_id) * 100.0), \
                f"task_id={worker_id}: task_score mismatch"

        # Re-submit; all should be blocked with 'done'
        tasks2 = [
            (tmpdir, "mp_runs", cfg, config_cols, i + 100)
            for i, cfg in enumerate(configs)
        ]
        with get_context("spawn").Pool(processes=4) as pool:
            results2 = pool.map(_worker, tasks2)

        blocked2 = [r for r in results2 if r[1] == "blocked"]
        assert len(blocked2) == len(configs), \
            f"Expected all {len(configs)} re-runs blocked, got {len(blocked2)}"
        for _, _, reason in blocked2:
            assert reason == "done", \
                f"Re-submission reason should be 'done', got '{reason}'"


def test_race_condition_single_config():
    """Multiple workers competing for the same config; exactly one must win."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_cols = ["experiment"]
        shared_config = {"experiment": "shared"}
        num_workers = 15
        tasks = [
            (tmpdir, "race_runs", shared_config, config_cols, i)
            for i in range(num_workers)
        ]
        with get_context("spawn").Pool(processes=8) as pool:
            results = pool.map(_worker, tasks)

        completed = [r for r in results if r[1] == "completed"]
        blocked   = [r for r in results if r[1] == "blocked"]
        assert len(completed) == 1, \
            f"Exactly one worker should win the race, got {len(completed)}"
        assert len(blocked) == num_workers - 1, \
            f"Expected {num_workers - 1} blocked, got {len(blocked)}"
        assert completed[0][2] == "new", \
            f"Winner reason should be 'new', got '{completed[0][2]}'"
        for _, _, reason in blocked:
            assert reason in ("running", "done"), \
                f"Loser reason should be 'running' or 'done', got '{reason}'"

        # Verify stored metrics match the winning worker
        winning_worker_id = completed[0][0]
        record = RunManager.get_records_df(tmpdir, "race_runs")
        assert len(record) == 1
        assert np.isclose(record.iloc[0]["worker_id"], float(winning_worker_id)), \
            f"Stored worker_id {record.iloc[0]['worker_id']} != winner {winning_worker_id}"
        assert np.isclose(record.iloc[0]["task_score"], float(winning_worker_id) * 100.0), \
            f"Stored task_score {record.iloc[0]['task_score']} != expected {winning_worker_id * 100.0}"


def test_multiprocessing_shared_tasks():
    """Each worker sees the same full task list and uses RunManager to claim work.
    Every task must be completed exactly once, and the stored worker_id and
    task_score must match the values reported by the winning worker."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_cols = ["task_id"]
        num_tasks = 20
        all_configs = [{"task_id": str(i)} for i in range(num_tasks)]
        num_workers = 5
        worker_tasks = [
            (tmpdir, "shared_tasks", all_configs, config_cols, i)
            for i in range(num_workers)
        ]
        with get_context("spawn").Pool(processes=num_workers) as pool:
            results = pool.map(_worker_shared_tasks, worker_tasks)

        # Build a map: task_id -> worker_id; detect any duplicates
        completed_map = {}
        for worker_id, completed_ids in results:
            for task_id in completed_ids:
                assert task_id not in completed_map, \
                    f"task_id={task_id} was completed by more than one worker"
                completed_map[task_id] = worker_id

        assert len(completed_map) == num_tasks, \
            f"Expected {num_tasks} unique completions, got {len(completed_map)}"

        # All records stored as 'done'
        df = RunManager.get_records_df(tmpdir, "shared_tasks")
        assert len(df) == num_tasks, f"Expected {num_tasks} records, got {len(df)}"
        assert (df["___status"] == "done").all(), "Not all records are 'done'"

        # Stored metrics must exactly match what the winning worker reported
        for task_id, expected_worker in completed_map.items():
            row = df[df["task_id"] == task_id]
            assert len(row) == 1
            stored_worker_id = row.iloc[0]["worker_id"]
            stored_task_score = row.iloc[0]["task_score"]
            expected_task_score = float(expected_worker) * 100.0 + float(task_id)
            assert np.isclose(stored_worker_id, float(expected_worker)), \
                f"task_id={task_id}: expected worker_id={expected_worker}, " \
                f"got {stored_worker_id}"
            assert np.isclose(stored_task_score, expected_task_score), \
                f"task_id={task_id}: expected task_score={expected_task_score}, " \
                f"got {stored_task_score}"

# ── misc / edge cases ─────────────────────────────────────────────────────────

def test_three_column_config():
    """RunManager works correctly with three config dimensions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = RunManager(
            save_path=tmpdir,
            file_name="three",
            config_cols=["a", "b", "c"],
        )
        cfg = {"a": "1", "b": "2", "c": "3"}
        assert m.register_start(cfg)["can_run"] is True
        m.report_done(cfg, {"score": 7.0})
        assert m.register_start(cfg)["reason"] == "done"


def test_many_metric_columns():
    """report_done with 20 metrics saves and recalls all of them correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir)
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        metrics = {f"metric_{i}": float(i) * 0.1 for i in range(20)}
        m.report_done(cfg, metrics)
        df = RunManager.get_records_df(tmpdir, "test_runs")
        for i in range(20):
            assert np.isclose(df.iloc[0][f"metric_{i}"], float(i) * 0.1), \
                f"metric_{i} mismatch"


def test_different_file_names_are_independent():
    """Two RunManagers in the same directory with different file names do not interfere."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m1 = make_manager(tmpdir, file_name="runs_a")
        m2 = make_manager(tmpdir, file_name="runs_b")
        cfg = {"param_a": "1", "param_b": "2"}
        m1.register_start(cfg)
        m1.report_done(cfg, {"score": 1.0})
        df2 = RunManager.get_records_df(tmpdir, "runs_b")
        assert len(df2) == 0, "Separate file_name must have independent state"
        result = m2.register_start(cfg)
        assert result["can_run"] is True and result["reason"] == "new"


def test_timeout_boundary_not_yet_expired():
    """A run just started (well within timeout) must not be restartable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = make_manager(tmpdir, restart_timeout="10s")
        cfg = {"param_a": "1", "param_b": "2"}
        m.register_start(cfg)
        result = m.register_start(cfg)
        assert result["can_run"] is False
        assert result["reason"] == "running"


def test_numeric_config_values():
    """RunManager handles integer and float config values correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        m = RunManager(
            save_path=tmpdir,
            file_name="numeric",
            config_cols=["experiment_id", "lr"],
        )
        cfg = {"experiment_id": 42, "lr": 0.001}
        result = m.register_start(cfg)
        assert result["can_run"] is True and result["reason"] == "new"
        m.report_done(cfg, {"accuracy": 0.95})
        result2 = m.register_start(cfg)
        assert result2["can_run"] is False and result2["reason"] == "done"


# ── runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    freeze_support()
    tests = [
        test_initialization_creates_files,
        test_initialization_starts_empty,
        test_initialization_idempotent,
        test_register_start_returns_dict_with_required_keys,
        test_register_new_can_run,
        test_register_new_sets_running_status,
        test_register_new_records_start_utc,
        test_register_while_running_blocks,
        test_register_within_timeout_does_not_update_start_utc,
        test_restart_after_timeout,
        test_restart_updates_start_utc,
        test_restart_sets_running_status_again,
        test_timeout_all_configs_together,
        test_done_blocks_rerun,
        test_done_blocks_even_after_timeout,
        test_report_done_stores_metrics,
        test_report_done_status_done,
        test_report_done_custom_status_failed,
        test_report_done_preserves_start_utc,
        test_report_done_overwrite_metrics,
        test_report_done_without_prior_register,
        test_metrics_with_nan,
        test_reported_values_roundtrip,
        test_failed_run_restarts_after_timeout,
        test_failed_run_blocked_within_timeout,
        test_multiple_configs_tracked_independently,
        test_done_one_does_not_affect_others,
        test_many_configs_sequential,
        test_high_volume_param_sweep,
        test_get_records_df_excludes_dummy_col,
        test_get_records_df_contains_config_and_status_cols,
        test_get_record_returns_correct_row,
        test_reserved_config_cols_raise,
        test_reserved_metric_keys_raise,
        test_no_tmp_files_left_after_operations,
        test_csv_and_parquet_consistent,
        test_multiprocessing_independent_configs,
        test_multiprocessing_shared_tasks,
        test_race_condition_single_config,
        test_three_column_config,
        test_many_metric_columns,
        test_different_file_names_are_independent,
        test_timeout_boundary_not_yet_expired,
        test_numeric_config_values,
    ]

    print("Running RunManager tests...\n")
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✓ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*40}")
    if failed == 0:
        print(f"All {passed} tests passed.")
    else:
        print(f"{passed} passed, {failed} FAILED.")
