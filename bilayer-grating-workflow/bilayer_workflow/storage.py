import json
import os

import pandas as pd


def _flatten(record, prefix=""):
    output = {}
    for key, value in record.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            output.update(_flatten(value, name))
        else:
            output[name] = value
    return output


class OptimizationStorage:
    def __init__(self, directory):
        self.directory = directory
        self.json_path = os.path.join(directory, "history.json")
        self.csv_path = os.path.join(directory, "history.csv")
        self.plot_path = os.path.join(directory, "progress.png")
        os.makedirs(directory, exist_ok=True)
        self.rows = self._load()

    def _load(self):
        if not os.path.exists(self.json_path):
            return []
        with open(self.json_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def write(self, record):
        self.rows.append(record)
        temp_path = self.json_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(self.rows, handle, indent=2)
        os.replace(temp_path, self.json_path)
        pd.DataFrame([_flatten(row) for row in self.rows]).to_csv(
            self.csv_path, index=False
        )
        self.plot()

    def valid_rows(self):
        return [
            row for row in self.rows
            if isinstance(row.get("result", {}).get("objective"), (int, float))
        ]

    def best(self):
        rows = self.valid_rows()
        if not rows:
            return None
        return max(rows, key=lambda row: row["result"]["objective"])

    def plot(self):
        rows = self.valid_rows()
        if not rows:
            return
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ModuleNotFoundError:
            return
        run_ids = [row["meta"]["run_id"] for row in rows]
        values = [row["result"]["objective"] for row in rows]
        best_values = []
        current = float("-inf")
        for value in values:
            current = max(current, value)
            best_values.append(current)
        fig, ax = plt.subplots(figsize=(8, 4.8))
        ax.scatter(run_ids, values, s=22, label="objective")
        ax.plot(run_ids, best_values, color="#c23834", label="best")
        ax.set_xlabel("run id")
        ax.set_ylabel("objective")
        ax.set_title("Bilayer optimization progress")
        ax.grid(True, alpha=0.25)
        ax.legend()
        fig.tight_layout()
        fig.savefig(self.plot_path, dpi=180)
        plt.close(fig)
