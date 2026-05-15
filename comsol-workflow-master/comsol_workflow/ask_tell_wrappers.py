import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

class OptimizationStorage:  
    def __init__(
        self,
        save_path, 
        file_name,
    ):
        os.makedirs(save_path, exist_ok=True)
        self.csv_path = os.path.join(save_path, file_name+".csv")
        self.parquet_path = os.path.join(save_path, file_name+".parquet")
        self.plot_path = os.path.join(save_path, file_name+".png")
        
        self.df = self.load()

    def save(self):
        self.df.to_parquet(self.parquet_path+".tmp")
        os.replace(self.parquet_path+".tmp", self.parquet_path)

        df_flat = self.df.copy()
        df_flat.columns = ['.'.join(col) for col in df_flat.columns.to_flat_index()]
        df_flat.to_csv(self.csv_path+".tmp", index=False)
        os.replace(self.csv_path+".tmp", self.csv_path)

        self.plot()
    
    def load(self):
        if os.path.exists(self.parquet_path):
            df = pd.read_parquet(self.parquet_path)
            return df
        else:
            return pd.DataFrame(columns=pd.MultiIndex.from_product([["meta", "params", "result", "attrs"], []]))
    
    def write(self, rows):
        for row in rows:
            row_df = pd.concat({
                cat: pd.Series(row[cat]) 
                for cat in ["meta", "params", "result", "attrs"]
                if cat in row.keys()
            }).to_frame().T
            self.df = pd.concat([self.df, row_df], ignore_index=True)
        self.save()

    def get_all_runs(self):
        return self.df

    def get_valid_runs(self):
        subset_cols = self.df.columns[self.df.columns.get_level_values(0).isin(["params", "result"])]
        return self.df.dropna(subset=subset_cols)
    
    def get_best_run(self):
        """Get the run with the highest objective value."""
        if len(self.get_valid_runs()) == 0:
            return None, pd.Series(index=self.df.columns)
        
        best_idx = self.df[("result", "objective")].argmax()
        return best_idx, self.df.iloc[best_idx]

    def plot(self):
        """Generate a progress plot showing objective values and cumulative best."""
        if len(self.df) == 0:
            objectives = pd.Series([], dtype=float)
            run_ids = pd.Series([], dtype=int)
            cum_max = pd.Series([], dtype=float)
        else:
            objectives = self.df[("result", "objective")]
            run_ids = self.df[("meta", "run_id")]
            cum_max = objectives.cummax().astype(float).ffill().bfill()
        
        fig, ax = plt.subplots(figsize=(10, 6))
        # Scatter plot of all runs
        ax.scatter(run_ids, objectives, alpha=0.8, s=30, label="Run Value", zorder=2)
        
        # Cumulative maximum line
        ax.plot(run_ids, cum_max, color='red', linewidth=1, label="Best Value", zorder=3)

        # Horizontal line at 7
        ax.axhline(y=7, color='red', linestyle='--', linewidth=1, zorder=1)
        
        ax.set_xlabel("Run ID", fontsize=12)
        ax.set_ylabel("Objective Value", fontsize=12)
        ax.set_title("Optimization Progress", fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--', zorder=1)
        
        plt.tight_layout()
        plt.savefig(self.plot_path, dpi=300, bbox_inches='tight')
        plt.close()

# ----------------------------
# Unified ask/tell interface
# ----------------------------

class Suggestion:
    def __init__(self, token, params):
        self.token = token  # opaque object used for tell, None for stateless optimizers
        self.params = params  # dict of parameter values


class OptimizerWrapperBase:
    def ask(self, n):
        raise NotImplementedError

    def tell(self, suggestions, objectives):
        raise NotImplementedError


# ----------------------------
# Optimizer factory
# ----------------------------

def make_optimizer(
    method,
    bounds,
    batch_size,
    history,
):
    if method in ["Sobol", "Halton"]:
        return QuasiRandomSamplerWrapper(method, bounds, batch_size, history)
    elif method in ["OptunaAuto", "OptunaTPE", "OptunaCMAES"]:
        return OptunaWrapper(method, bounds, batch_size, history)
    elif method in ["NevergradNGOpt", "NevergradCMA", "NevergradOnePlusOne"]:
        return NevergradWrapper(method, bounds, batch_size, history)
    else:
        raise ValueError(f"Unknown optimizer method: {method}")


# ----------------------------
# Quasi-random + Random
# ----------------------------

class QuasiRandomSamplerWrapper(OptimizerWrapperBase):
    def __init__(self, method, bounds, batch_size, history):
        self.name = method
        self.method = method
        self.bounds = bounds
        self.batch_size = batch_size
        self.ndim = len(bounds)
        self.keys = list(bounds.keys())
        self.low = np.array([bounds[k][0] for k in self.keys], dtype=float) # [N]
        self.high = np.array([bounds[k][1] for k in self.keys], dtype=float) # [N]

        from scipy.stats import qmc
        if method == "Sobol":
            self.sampler = qmc.Sobol(d=self.ndim)
        elif method == "Halton":
            self.sampler = qmc.Halton(d=self.ndim)
        else:
            raise ValueError(f"Unknown quasi-random method: {method}")

        if len(history) > 0:
            self.sampler.fast_forward(len(history))

    def ask(self):
        u = self.sampler.random(self.batch_size)  # in [0,1), [n, N]
        x = self.low + u * (self.high - self.low) # [n, N]

        suggestions = []
        for row in x:
            params = {k: float(v) for k, v in zip(self.keys, row)}
            suggestions.append(Suggestion(token=None, params=params))
        return suggestions

    def tell(self, suggestions, objectives):
        # quasi-random doesn't learn; noop
        return


# ----------------------------
# Optuna
# ----------------------------

class OptunaWrapper(OptimizerWrapperBase):
    def __init__(self, method, bounds, batch_size, history):
        self.name = method
        self.batch_size = batch_size

        import optuna
        from optuna.distributions import FloatDistribution
        from optuna.trial import create_trial

        self.space = {k: FloatDistribution(v[0], v[1]) for k, v in bounds.items()}

        if method == "OptunaAuto":
            sampler = optuna.samplers.AutoSampler()
        elif method == "OptunaTPE":
            sampler = optuna.samplers.TPESampler()
        elif method == "OptunaCMAES":
            sampler = optuna.samplers.CmaEsSampler()
        else:
            raise ValueError(f"Unknown optuna method: {method}")

        self.study = optuna.create_study(direction="maximize", sampler=sampler)

        # replay history (stateless rebuild)
        for _, r in history.iterrows():
            params = {k: float(r[("params", k)]) for k in bounds.keys()}
            value = float(r[("result", "objective")])
            trial = create_trial(params=params, distributions=self.space, value=value)
            self.study.add_trial(trial)

    def ask(self):
        suggestions = []
        for _ in range(self.batch_size):
            t = self.study.ask(fixed_distributions=self.space)
            suggestions.append(Suggestion(token=t, params=dict(t.params)))
        return suggestions

    def tell(self, suggestions, objectives):
        for s, y in zip(suggestions, objectives):
            self.study.tell(s.token, float(y))


# ----------------------------
# Nevergrad
# ----------------------------

class NevergradWrapper(OptimizerWrapperBase):
    def __init__(self, method, bounds, batch_size, history):
        self.name = method
        self.batch_size = batch_size

        import nevergrad as ng
        self.param = ng.p.Dict(**{k: ng.p.Scalar(lower=bounds[k][0], upper=bounds[k][1]) for k in bounds.keys()})

        if method == "NevergradNGOpt":
            self.opt = ng.optimizers.NGOpt(
                parametrization=self.param, 
                budget=len(history) + 1000,
                num_workers=batch_size,
            )
        elif method == "NevergradCMA":
            self.opt = ng.optimizers.CMA(
                parametrization=self.param, 
                budget=len(history) + 1000,
                num_workers=batch_size,
            )
        elif method == "NevergradOnePlusOne":
            self.opt = ng.optimizers.OnePlusOne(
                parametrization=self.param, 
                budget=len(history) + 1000, 
                num_workers=batch_size,
            )
        else:
            raise ValueError(f"Unknown nevergrad method: {method}")

        # replay history (stateless rebuild)
        # Nevergrad minimizes => maximize objective by telling (-objective)
        for _, r in history.iterrows():
            cand = self.opt.parametrization.spawn_child()
            cand.value = {k: float(r[("params", k)]) for k in bounds.keys()}
            y = float(r[("result", "objective")])
            self.opt.tell(cand, -y)

    def ask(self):
        suggestions = []
        for _ in range(self.batch_size):
            c = self.opt.ask()
            suggestions.append(Suggestion(token=c, params=dict(c.value)))
        return suggestions

    def tell(self, suggestions, objectives):
        for s, y in zip(suggestions, objectives):
            self.opt.tell(s.token, -float(y))  # negate to maximize

