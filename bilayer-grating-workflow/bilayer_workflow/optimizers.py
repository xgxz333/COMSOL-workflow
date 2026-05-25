import numpy as np


class Suggestion:
    def __init__(self, token, params):
        self.token = token
        self.params = params


class RandomOptimizer:
    name = "Random"

    def __init__(self, bounds, batch_size, history):
        self.keys = list(bounds)
        self.low = np.array([bounds[key][0] for key in self.keys], dtype=float)
        self.high = np.array([bounds[key][1] for key in self.keys], dtype=float)
        self.batch_size = batch_size
        self.rng = np.random.default_rng(seed=20240525 + len(history))

    def ask(self):
        values = self.rng.uniform(self.low, self.high, size=(self.batch_size, len(self.keys)))
        return [
            Suggestion(None, {key: float(value) for key, value in zip(self.keys, row)})
            for row in values
        ]

    def tell(self, suggestions, objectives):
        return


class SobolOptimizer:
    name = "Sobol"

    def __init__(self, bounds, batch_size, history):
        from scipy.stats import qmc

        self.keys = list(bounds)
        self.low = np.array([bounds[key][0] for key in self.keys], dtype=float)
        self.high = np.array([bounds[key][1] for key in self.keys], dtype=float)
        self.batch_size = batch_size
        self.sampler = qmc.Sobol(d=len(bounds), scramble=True)
        if history:
            self.sampler.fast_forward(len(history))

    def ask(self):
        samples = self.sampler.random(self.batch_size)
        values = self.low + samples * (self.high - self.low)
        return [
            Suggestion(None, {key: float(value) for key, value in zip(self.keys, row)})
            for row in values
        ]

    def tell(self, suggestions, objectives):
        return


class NevergradOptimizer:
    def __init__(self, method, bounds, batch_size, history):
        import nevergrad as ng

        self.name = method
        self.keys = list(bounds)
        parameter = ng.p.Dict(
            **{
                key: ng.p.Scalar(lower=value[0], upper=value[1])
                for key, value in bounds.items()
            }
        )
        optimizer_cls = {
            "NevergradNGOpt": ng.optimizers.NGOpt,
            "NevergradCMA": ng.optimizers.CMA,
            "NevergradOnePlusOne": ng.optimizers.OnePlusOne,
        }[method]
        self.optimizer = optimizer_cls(
            parametrization=parameter,
            budget=len(history) + 1000,
            num_workers=batch_size,
        )
        self.batch_size = batch_size
        for row in history:
            candidate = self.optimizer.parametrization.spawn_child()
            candidate.value = {key: float(row["params"][key]) for key in self.keys}
            self.optimizer.tell(candidate, -float(row["result"]["objective"]))

    def ask(self):
        suggestions = []
        for _ in range(self.batch_size):
            candidate = self.optimizer.ask()
            suggestions.append(Suggestion(candidate, dict(candidate.value)))
        return suggestions

    def tell(self, suggestions, objectives):
        for suggestion, objective in zip(suggestions, objectives):
            self.optimizer.tell(suggestion.token, -float(objective))


def make_optimizer(method, bounds, batch_size, history):
    if method == "Random":
        return RandomOptimizer(bounds, batch_size, history)
    if method == "Sobol":
        return SobolOptimizer(bounds, batch_size, history)
    if method in {"NevergradNGOpt", "NevergradCMA", "NevergradOnePlusOne"}:
        return NevergradOptimizer(method, bounds, batch_size, history)
    raise ValueError(f"Unknown optimizer method: {method}")
