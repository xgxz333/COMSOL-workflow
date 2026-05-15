import os
import sys
import numpy as np
import pandas as pd
import shutil

# Ensure imports work relative to this script location
sys.path.append(os.path.join(os.path.dirname(__file__), "../comsol_workflow"))

from ask_tell_wrappers import (
    OptimizationStorage,
    make_optimizer,
    QuasiRandomSamplerWrapper,
    OptunaWrapper,
    NevergradWrapper,
)
from runtime_paths import get_tests_out_path


def _get_test_dir(*parts):
    return get_tests_out_path("test_ask_tell_results", *parts)


def test_storage_init_and_save():
    print("\n=== TEST: Storage Initialization & Save ===")
    
    test_dir = _get_test_dir("test_storage")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    storage = OptimizationStorage(test_dir, "test_runs")
    
    # Check empty dataframe has correct MultiIndex structure
    df = storage.get_all_runs()
    assert isinstance(df.columns, pd.MultiIndex), "Columns should be MultiIndex"
    assert df.columns.nlevels == 2, "Should have 2 levels"
    assert len(df) == 0, "Should start empty"
    print("[Pass] Storage initializes with empty MultiIndex DataFrame")
    
    # Write some rows
    rows = [
        {
            "meta": {"run_id": 0, "optimizer": "test"},
            "params": {"x": 1.0, "y": 2.0},
            "result": {"objective": 10.0},
            "attrs": {"time": 0.5},
        },
        {
            "meta": {"run_id": 1, "optimizer": "test"},
            "params": {"x": 1.5, "y": 2.5},
            "result": {"objective": 15.0},
            "attrs": {"time": 0.6},
        },
    ]
    
    storage.write(rows)
    
    # Check files exist
    assert os.path.exists(storage.parquet_path), "Parquet file should exist"
    assert os.path.exists(storage.csv_path), "CSV file should exist"
    print("[Pass] Files created after write")
    
    # Check data persists
    df = storage.get_all_runs()
    assert len(df) == 2, f"Should have 2 rows, got {len(df)}"
    assert ("meta", "run_id") in df.columns, "Should have run_id column"
    assert ("params", "x") in df.columns, "Should have params.x column"
    print("[Pass] Data written correctly with MultiIndex columns")
    
    # Test loading from disk
    storage2 = OptimizationStorage(test_dir, "test_runs")
    df2 = storage2.get_all_runs()
    assert len(df2) == 2, "Should load 2 rows from disk"
    assert df2[("result", "objective")].iloc[0] == 10.0, "Data should match"
    print("[Pass] Data persists and loads from disk")


def test_storage_dynamic_columns():
    print("\n=== TEST: Storage Dynamic Column Expansion ===")
    
    test_dir = _get_test_dir("test_storage_dynamic")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    storage = OptimizationStorage(test_dir, "dynamic_test")
    
    # Write first batch with subset of columns
    rows1 = [
        {
            "meta": {"run_id": 0},
            "params": {"a": 1.0},
            "result": {"objective": 5.0},
        }
    ]
    storage.write(rows1)
    
    df1 = storage.get_all_runs()
    assert ("params", "a") in df1.columns, "Should have params.a"
    assert ("params", "b") not in df1.columns, "Should not have params.b yet"
    print("[Pass] Initial columns created")
    
    # Write second batch with new columns
    rows2 = [
        {
            "meta": {"run_id": 1},
            "params": {"a": 2.0, "b": 3.0, "c": 4.0},
            "result": {"objective": 10.0, "constraint": -1.0},
            "attrs": {"wall_time": 1.5},
        }
    ]
    storage.write(rows2)
    
    df2 = storage.get_all_runs()
    assert ("params", "b") in df2.columns, "Should have params.b now"
    assert ("params", "c") in df2.columns, "Should have params.c now"
    assert ("result", "constraint") in df2.columns, "Should have result.constraint"
    assert ("attrs", "wall_time") in df2.columns, "Should have attrs.wall_time"
    print("[Pass] Columns expanded dynamically")
    
    # Check NaN filling for old rows
    assert pd.isna(df2.loc[0, ("params", "b")]), "Old row should have NaN for new column"
    assert df2.loc[1, ("params", "b")] == 3.0, "New row should have value"
    print("[Pass] NaN filled for missing values in old rows")


def test_storage_valid_runs():
    print("\n=== TEST: Storage Valid Runs Filtering ===")
    
    test_dir = _get_test_dir("test_storage_valid")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    storage = OptimizationStorage(test_dir, "valid_test")
    
    rows = [
        {
            "meta": {"run_id": 0},
            "params": {"x": 1.0},
            "result": {"objective": 10.0},
            "attrs": {},
        },
        {
            "meta": {"run_id": 1},
            "params": {"x": 2.0},
            "result": {},  # Missing objective
            "attrs": {},
        },
        {
            "meta": {"run_id": 2},
            # Missing params
            "result": {"objective": 15.0},
            "attrs": {},
        },
        {
            "meta": {"run_id": 3},
            "params": {"x": 3.0},
            "result": {"objective": 20.0},
            "attrs": {},
        },
    ]
    storage.write(rows)
    
    all_runs = storage.get_all_runs()
    valid_runs = storage.get_valid_runs()
    
    assert len(all_runs) == 4, f"Should have 4 total rows, got {len(all_runs)}"
    assert len(valid_runs) == 2, f"Should have 2 valid rows, got {len(valid_runs)}"
    
    valid_ids = valid_runs[("meta", "run_id")].tolist()
    assert 0 in valid_ids, "Run 0 should be valid"
    assert 3 in valid_ids, "Run 3 should be valid"
    assert 1 not in valid_ids, "Run 1 should be invalid (missing objective)"
    assert 2 not in valid_ids, "Run 2 should be invalid (missing params)"
    print("[Pass] Valid runs filtered correctly")


def test_storage_get_best_run():
    print("\n=== TEST: Storage Get Best Run ===")
    
    test_dir = _get_test_dir("test_storage_best")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    storage = OptimizationStorage(test_dir, "best_test")
    
    # Test empty storage
    best_idx, best_run = storage.get_best_run()
    assert best_idx is None, "Should return None for empty storage"
    assert len(best_run) == 0, "Should return empty Series for empty storage"
    print("[Pass] Returns None for empty storage")
    
    # Write some runs
    rows = [
        {
            "meta": {"run_id": 0, "optimizer": "test"},
            "params": {"x": 1.0, "y": 2.0},
            "result": {"objective": 10.0},
        },
        {
            "meta": {"run_id": 1, "optimizer": "test"},
            "params": {"x": 1.5, "y": 2.5},
            "result": {"objective": 15.0},
        },
        {
            "meta": {"run_id": 2, "optimizer": "test"},
            "params": {"x": 0.5, "y": 1.5},
            "result": {"objective": 8.0},
        },
        {
            "meta": {"run_id": 3, "optimizer": "test"},
            "params": {"x": 2.0, "y": 3.0},
            "result": {"objective": 20.0},  # Best
        },
        {
            "meta": {"run_id": 4, "optimizer": "test"},
            "params": {"x": 1.2, "y": 2.2},
            "result": {"objective": 12.0},
        },
    ]
    storage.write(rows)
    
    # Get best run
    best_idx, best_run = storage.get_best_run()
    assert best_idx == 3, f"Best index should be 3, got {best_idx}"
    assert best_run[("result", "objective")] == 20.0, "Best objective should be 20.0"
    assert best_run[("meta", "run_id")] == 3, "Best run_id should be 3"
    assert best_run[("params", "x")] == 2.0, "Best x should be 2.0"
    assert best_run[("params", "y")] == 3.0, "Best y should be 3.0"
    print("[Pass] Returns correct best run")
    
    # Test with NaN values (invalid runs)
    rows_with_nan = [
        {
            "meta": {"run_id": 5, "optimizer": "test"},
            "params": {"x": 3.0},
            "result": {},  # Missing objective
        },
    ]
    storage.write(rows_with_nan)
    
    best_idx, best_run = storage.get_best_run()
    assert best_idx == 3, "Best should still be run 3 (ignoring NaN)"
    assert best_run[("result", "objective")] == 20.0, "Best objective should still be 20.0"
    print("[Pass] Handles NaN values correctly")


def test_storage_plot_generation():
    print("\n=== TEST: Storage Plot Generation ===")
    
    test_dir = _get_test_dir("test_storage_plot")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    storage = OptimizationStorage(test_dir, "plot_test")
    
    # Test plot doesn't crash on empty storage
    storage.plot()
    print("[Pass] Plot handles empty storage")
    
    # Write runs with varying objectives
    np.random.seed(42)
    objectives = [5.0, 8.0, 6.0, 12.0, 10.0, 15.0, 14.0, 18.0, 16.0, 20.0]
    rows = [
        {
            "meta": {"run_id": i, "optimizer": "test"},
            "params": {"x": float(np.random.randn())},
            "result": {"objective": obj},
        }
        for i, obj in enumerate(objectives)
    ]
    storage.write(rows)
    
    # Check plot file exists
    assert os.path.exists(storage.plot_path), "Plot file should be created"
    print("[Pass] Plot file created")
    
    # Check plot has reasonable file size (not empty)
    plot_size = os.path.getsize(storage.plot_path)
    assert plot_size > 1000, f"Plot file seems too small: {plot_size} bytes"
    print(f"[Pass] Plot file has reasonable size: {plot_size} bytes")
    
    # Verify cumulative max logic by checking the data
    df = storage.get_all_runs()
    objectives_arr = df[("result", "objective")].values
    cum_max = np.maximum.accumulate(objectives_arr)
    
    # Check cumulative max is monotonically increasing
    assert np.all(cum_max[1:] >= cum_max[:-1]), "Cumulative max should be monotonically increasing"
    assert cum_max[-1] == 20.0, "Final cumulative max should be 20.0"
    assert cum_max[0] == 5.0, "First cumulative max should be 5.0"
    assert cum_max[3] == 12.0, "Cumulative max at index 3 should be 12.0"
    print("[Pass] Cumulative max calculated correctly")


def test_storage_plot_with_invalid_runs():
    print("\n=== TEST: Storage Plot with Invalid Runs ===")
    
    test_dir = _get_test_dir("test_storage_plot_invalid")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    storage = OptimizationStorage(test_dir, "plot_invalid_test")
    
    # Mix of valid and invalid runs
    rows = [
        {
            "meta": {"run_id": 0, "optimizer": "test"},
            "params": {"x": 1.0},
            "result": {"objective": 10.0},
        },
        {
            "meta": {"run_id": 1, "optimizer": "test"},
            "params": {"x": 2.0},
            "result": {},  # Invalid - missing objective
        },
        {
            "meta": {"run_id": 2, "optimizer": "test"},
            "params": {"x": 3.0},
            "result": {"objective": 15.0},
        },
        {
            "meta": {"run_id": 3, "optimizer": "test"},
            "params": {},  # Invalid - missing params
            "result": {"objective": 20.0},
        },
        {
            "meta": {"run_id": 4, "optimizer": "test"},
            "params": {"x": 4.0},
            "result": {"objective": 12.0},
        },
    ]
    storage.write(rows)
    
    # Plot should still be generated
    assert os.path.exists(storage.plot_path), "Plot should be created even with invalid runs"
    print("[Pass] Plot created with mixed valid/invalid runs")


def test_quasi_random_samplers():
    print("\n=== TEST: Quasi-Random Samplers ===")
    
    bounds = {"x": (-5.0, 5.0), "y": (0.0, 10.0)}
    batch_size = 5
    
    for method in ["Sobol", "Halton"]:
        print(f"\nTesting {method}...")
        
        # Empty history
        history = pd.DataFrame(columns=pd.MultiIndex.from_product([["params", "result"], []]))
        sampler = QuasiRandomSamplerWrapper(method, bounds, batch_size, history)
        
        # Ask for suggestions
        suggestions = sampler.ask()
        assert len(suggestions) == batch_size, f"Should get {batch_size} suggestions, got {len(suggestions)}"
        
        for s in suggestions:
            assert s.token is None, "Quasi-random should have None token"
            assert "x" in s.params and "y" in s.params, "Should have x and y params"
            assert -5.0 <= s.params["x"] <= 5.0, "x should be in bounds"
            assert 0.0 <= s.params["y"] <= 10.0, "y should be in bounds"
        
        print(f"[Pass] {method} generates valid suggestions")
        
        # Tell should be no-op
        objectives = [1.0, 2.0, 3.0, 4.0, 5.0]
        sampler.tell(suggestions, objectives)
        print(f"[Pass] {method} tell is no-op")


def test_optuna_wrapper():
    print("\n=== TEST: Optuna Wrapper ===")
    
    bounds = {"x": (-5.0, 5.0), "y": (0.0, 10.0)}
    batch_size = 3
    
    # Create history with proper MultiIndex
    history_data = {
        ("params", "x"): [1.0, -2.0],
        ("params", "y"): [2.0, 5.0],
        ("result", "objective"): [10.0, 8.0],
    }
    history = pd.DataFrame(history_data)
    
    for method in ["OptunaTPE", "OptunaCMAES"]:
        print(f"\nTesting {method}...")
        
        opt = OptunaWrapper(method, bounds, batch_size, history)
        assert len(opt.study.trials) == 2, "Should have 2 trials from history"
        print(f"[Pass] {method} initialized with history")
        
        # Ask
        suggestions = opt.ask()
        assert len(suggestions) == batch_size, f"Should get {batch_size} suggestions"
        
        for s in suggestions:
            assert s.token is not None, "Optuna should have non-None token"
            assert "x" in s.params and "y" in s.params, "Should have x and y params"
        
        print(f"[Pass] {method} ask works")
        
        # Tell
        objectives = [12.0, 9.0, 11.0]
        opt.tell(suggestions, objectives)
        assert len(opt.study.trials) == 5, "Should have 5 trials after tell"
        print(f"[Pass] {method} tell works")


def test_nevergrad_wrapper():
    print("\n=== TEST: Nevergrad Wrapper ===")
    
    bounds = {"x": (-5.0, 5.0), "y": (0.0, 10.0)}
    batch_size = 3
    
    # Create history with proper MultiIndex
    history_data = {
        ("params", "x"): [1.0, -2.0],
        ("params", "y"): [2.0, 5.0],
        ("result", "objective"): [10.0, 8.0],
    }
    history = pd.DataFrame(history_data)
    
    for method in ["NevergradOnePlusOne", "NevergradCMA"]:
        print(f"\nTesting {method}...")
        
        opt = NevergradWrapper(method, bounds, batch_size, history)
        print(f"[Pass] {method} initialized with history")
        
        # Ask
        suggestions = opt.ask()
        assert len(suggestions) == batch_size, f"Should get {batch_size} suggestions"
        
        for s in suggestions:
            assert s.token is not None, "Nevergrad should have non-None token"
            assert "x" in s.params and "y" in s.params, "Should have x and y params"
        
        print(f"[Pass] {method} ask works")
        
        # Tell
        objectives = [12.0, 9.0, 11.0]
        opt.tell(suggestions, objectives)
        print(f"[Pass] {method} tell works")


def test_optimizer_factory():
    print("\n=== TEST: Optimizer Factory ===")
    
    bounds = {"x": (-5.0, 5.0), "y": (0.0, 10.0)}
    batch_size = 2
    history = pd.DataFrame(columns=pd.MultiIndex.from_product([["params", "result"], []]))
    
    methods = [
        "Sobol", "Halton",
        "OptunaTPE", "OptunaCMAES",
        "NevergradOnePlusOne", "NevergradCMA"
    ]
    
    for method in methods:
        opt = make_optimizer(method, bounds, batch_size, history)
        assert opt.name == method, f"Name should be {method}"
        
        suggestions = opt.ask()
        assert len(suggestions) == batch_size, f"Should get {batch_size} suggestions from {method}"
        
        print(f"[Pass] Factory creates {method} correctly")


def test_end_to_end_workflow(method):
    print(f"\n=== TEST: End-to-End Workflow ({method}) ===")
    
    test_dir = _get_test_dir(f"test_e2e_{method}")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    storage = OptimizationStorage(test_dir, "e2e_test")
    bounds = {"x": (-5.0, 5.0), "y": (-5.0, 5.0)}
    
    # Simple quadratic objective
    def evaluate(params):
        x, y = params["x"], params["y"]
        return -(x**2 + y**2)  # maximize (peak at origin)
    
    # Run optimization loop
    n_iterations = 5
    batch_size = 2

    history = storage.get_valid_runs()
    opt = make_optimizer(method, bounds, batch_size, history)
    for iteration in range(n_iterations):
        # Ask
        suggestions = opt.ask()
        
        # Evaluate
        objectives = [evaluate(s.params) for s in suggestions]
        
        # Tell
        opt.tell(suggestions, objectives)
        
        # Write results
        rows = []
        for i, (s, obj) in enumerate(zip(suggestions, objectives)):
            run_id = iteration * batch_size + i
            row = {
                "meta": {"run_id": run_id, "iteration": iteration, "optimizer": method},
                "params": s.params,
                "result": {"objective": obj},
                "attrs": {"batch": batch_size},
            }
            rows.append(row)
        
        storage.write(rows)
        print(f"  Iteration {iteration}: Best = {max(objectives):.4f}")
    
    # Check final state
    final_df = storage.get_all_runs()
    assert len(final_df) == n_iterations * batch_size, "Should have correct number of runs"
    
    best_obj = final_df[("result", "objective")].max()
    print(f"[Pass] End-to-end workflow completed. Best objective: {best_obj:.4f}")
    
    # Verify optimization improved
    first_batch_best = final_df.iloc[:batch_size][("result", "objective")].max()
    last_batch_best = final_df.iloc[-batch_size:][("result", "objective")].max()
    # assert last_batch_best >= first_batch_best, "Should improve or maintain"
    # print("[Pass] Optimization shows improvement")


def test_end_to_end_with_best_tracking(method):
    print(f"\n=== TEST: End-to-End with Best Tracking ({method}) ===")
    
    test_dir = _get_test_dir(f"test_e2e_best_{method}")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    storage = OptimizationStorage(test_dir, "e2e_best_test")
    bounds = {"x": (-5.0, 5.0), "y": (-5.0, 5.0)}
    
    # Simple quadratic objective
    def evaluate(params):
        x, y = params["x"], params["y"]
        return -(x**2 + y**2)  # maximize (peak at origin)
    
    # Run optimization loop
    n_iterations = 10
    batch_size = 1

    history = storage.get_valid_runs()
    opt = make_optimizer(method, bounds, batch_size, history)
    
    best_so_far = []
    for iteration in range(n_iterations):
        # Ask
        suggestions = opt.ask()
        
        # Evaluate
        objectives = [evaluate(s.params) for s in suggestions]
        
        # Tell
        opt.tell(suggestions, objectives)
        
        # Write results
        rows = []
        for i, (s, obj) in enumerate(zip(suggestions, objectives)):
            run_id = iteration * batch_size + i
            row = {
                "meta": {"run_id": run_id, "iteration": iteration, "optimizer": method},
                "params": s.params,
                "result": {"objective": obj},
            }
            rows.append(row)
        
        storage.write(rows)
        
        # Track best
        best_idx, best_run = storage.get_best_run()
        best_obj = best_run[("result", "objective")]
        best_so_far.append(best_obj)
        
        print(f"  Iteration {iteration}: Current = {objectives[0]:.4f}, Best so far = {best_obj:.4f} (Run {best_idx})")
    
    # Verify best tracking is monotonically improving
    assert all(best_so_far[i] >= best_so_far[i-1] for i in range(1, len(best_so_far))), \
        "Best so far should be monotonically increasing"
    print("[Pass] Best tracking is monotonically increasing")
    
    # Verify plot was created
    assert os.path.exists(storage.plot_path), "Progress plot should be created"
    print("[Pass] Progress plot generated")
    
    # Get final best
    final_best_idx, final_best_run = storage.get_best_run()
    final_best_obj = final_best_run[("result", "objective")]
    print(f"[Pass] Final best: Run {final_best_idx}, Objective = {final_best_obj:.4f}")


if __name__ == "__main__":
    np.set_printoptions(precision=4, suppress=True)
    
    test_storage_init_and_save()
    test_storage_dynamic_columns()
    test_storage_valid_runs()
    test_storage_get_best_run()
    test_storage_plot_generation()
    test_storage_plot_with_invalid_runs()
    test_quasi_random_samplers()
    test_optuna_wrapper()
    test_nevergrad_wrapper()
    test_optimizer_factory()
    test_end_to_end_workflow("OptunaTPE")
    test_end_to_end_workflow("NevergradNGOpt")
    test_end_to_end_with_best_tracking("OptunaTPE")
    test_end_to_end_with_best_tracking("NevergradNGOpt")
    
    print("\n=== All Tests Completed ===")
