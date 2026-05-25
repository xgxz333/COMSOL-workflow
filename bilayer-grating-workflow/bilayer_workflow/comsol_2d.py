"""MPh/COMSOL backend for the 2D x-z unit-cell eigenmode model.

The model is intentionally kept in one module so geometry and boundary tags can
be adjusted after the first interactive COMSOL inspection. The pure-Python
workflow and objective can be tested without a COMSOL license.
"""

import os
import shutil

import pandas as pd

from .metrics import ModeResult
from .runtime_paths import ensure_directory

_MPH_ERROR = None
_JPYPE_ERROR = None
try:
    import mph
except Exception as exc:
    mph = None
    _MPH_ERROR = exc

try:
    from jpype.types import JArray, JInt, JString
except Exception as exc:
    JArray = JInt = JString = None
    _JPYPE_ERROR = exc


class Comsol2DBackend:
    """Run one 2D eigenfrequency model for each PCM material state."""

    def __init__(self):
        self._ensure_runtime()

    @staticmethod
    def _ensure_runtime():
        if _MPH_ERROR is not None:
            raise RuntimeError("Install MPh before using the COMSOL backend.") from _MPH_ERROR
        if _JPYPE_ERROR is not None:
            raise RuntimeError("Install jpype1 before using the COMSOL backend.") from _JPYPE_ERROR
        if not any(shutil.which(command) for command in ["comsol", "comsolbatch", "comsolmphserver"]):
            raise RuntimeError("COMSOL executables are not on PATH.")

    def evaluate_state(self, geometry, state, config, workspace):
        ensure_directory(workspace)
        if os.name == "nt":
            mph.option("session", os.environ.get("BILAYER_WORKFLOW_MPH_SESSION", "client-server"))
        client = mph.start(version=os.environ.get("COMSOL_VERSION"))
        model = client.create(f"bilayer_{state}")
        try:
            self._build_and_solve(model.java, geometry, state, config)
            table_path = os.path.join(workspace, "mode_metrics.txt")
            self._export_mode_table(model.java, table_path)
            model.save(os.path.join(workspace, f"bilayer_{state}.mph"))
            model.save(os.path.join(workspace, f"bilayer_{state}.java"))
            return self._read_modes(table_path, state)
        finally:
            client.remove(model)

    @staticmethod
    def _parameter(jmodel, name, value, unit=None):
        text = f"{value} [{unit}]" if unit else str(value)
        jmodel.param().set(name, text)

    @staticmethod
    def _rectangle(geom, tag, rectangle):
        geom.create(tag, "Rectangle")
        geom.feature(tag).set(
            "pos",
            JArray(JString, 1)([f"{rectangle.x0} [um]", f"{rectangle.z0} [um]"]),
        )
        geom.feature(tag).set(
            "size",
            JArray(JString, 1)([f"{rectangle.width} [um]", f"{rectangle.height} [um]"]),
        )
        geom.feature(tag).set("selresult", True)

    @staticmethod
    def _union_selection(component, tag, labels):
        component.selection().create(tag, "Union")
        component.selection(tag).set(
            "input",
            JArray(JString, 1)([f"geom1_{label}_dom" for label in labels]),
        )

    @staticmethod
    def _box_boundary_selection(component, tag, x0, x1, z0, z1):
        component.selection().create(tag, "Box")
        component.selection(tag).geom("geom1", 1)
        component.selection(tag).set("xmin", f"{x0} [um]")
        component.selection(tag).set("xmax", f"{x1} [um]")
        component.selection(tag).set("ymin", f"{z0} [um]")
        component.selection(tag).set("ymax", f"{z1} [um]")

    @staticmethod
    def _material(component, tag, label, n_value, k_value, selection):
        component.material().create(tag, "Common")
        material = component.material(tag)
        material.label(label)
        material.selection().named(selection)
        material.propertyGroup().create("RefractiveIndex", "Refractive Index")
        n_tensor = [str(n_value), "0", "0", "0", str(n_value), "0", "0", "0", str(n_value)]
        k_tensor = [str(k_value), "0", "0", "0", str(k_value), "0", "0", "0", str(k_value)]
        material.propertyGroup("RefractiveIndex").set("n", JArray(JString, 1)(n_tensor))
        material.propertyGroup("RefractiveIndex").set("ki", JArray(JString, 1)(k_tensor))

    def _build_and_solve(self, jmodel, geometry, state, config):
        design = geometry.design
        materials = config["materials"]
        simulation = config["simulation"]
        pcm = materials["pcm_states"][state]
        pcm_k = pcm["k"] if simulation["use_material_loss"] else 0.0

        self._parameter(jmodel, "period", design["period_um"], "um")
        self._parameter(jmodel, "kxnorm", design["kx_norm"])
        self._parameter(jmodel, "kx", "kxnorm*2*pi/period")
        self._parameter(jmodel, "f_shift", simulation["eigenfrequency_shift_thz"], "THz")

        jmodel.component().create("comp1", True)
        component = jmodel.component("comp1")
        component.geom().create("geom1", 2)
        geom = component.geom("geom1")
        geom.lengthUnit("um")
        for domain in geometry.domains:
            self._rectangle(geom, domain.name, domain)
        geom.run()

        self._union_selection(component, "sel_si", ["lower_si_grating", "upper_si_grating"])
        self._union_selection(
            component,
            "sel_sio2",
            ["top_sio2_left", "top_sio2_right", "top_sio2_over_pcm"],
        )
        self._union_selection(component, "sel_air", ["background", "bottom_pml", "top_pml"])
        self._union_selection(component, "sel_pml", ["bottom_pml", "top_pml"])

        self._material(component, "mat_air", "Air", materials["background"]["n"], materials["background"]["k"], "sel_air")
        self._material(component, "mat_si", "Silicon", materials["si"]["n"], materials["si"]["k"], "sel_si")
        self._material(component, "mat_sio2", "SiO2", materials["sio2"]["n"], materials["sio2"]["k"], "sel_sio2")
        self._material(component, "mat_pcm", state, pcm["n"], pcm_k, "geom1_upper_pcm_cap_dom")

        eps = design["period_um"] * 1.0e-5
        left = geometry.boundaries["periodic_left_x"]
        right = geometry.boundaries["periodic_right_x"]
        bottom = geometry.boundaries["pml_bottom_z"]
        top = geometry.boundaries["pml_top_z"]
        monitor_bottom = geometry.boundaries["power_bottom_z"]
        monitor_top = geometry.boundaries["power_top_z"]
        self._box_boundary_selection(component, "sel_periodic", left - eps, left + eps, bottom, top)
        self._box_boundary_selection(component, "sel_periodic_right", right - eps, right + eps, bottom, top)
        self._box_boundary_selection(component, "sel_open_top", left, right, top - eps, top + eps)
        self._box_boundary_selection(component, "sel_open_bottom", left, right, bottom - eps, bottom + eps)
        self._box_boundary_selection(component, "sel_monitor_top", left, right, monitor_top - eps, monitor_top + eps)
        self._box_boundary_selection(component, "sel_monitor_bottom", left, right, monitor_bottom - eps, monitor_bottom + eps)
        self._union_selection(component, "sel_open", [])
        component.selection("sel_open").set(
            "input", JArray(JString, 1)(["sel_open_top", "sel_open_bottom"])
        )
        component.selection().create("sel_periodic_pair", "Union")
        component.selection("sel_periodic_pair").set(
            "input", JArray(JString, 1)(["sel_periodic", "sel_periodic_right"])
        )

        component.coordSystem().create("pml1", "PML")
        component.coordSystem("pml1").selection().named("sel_pml")

        component.physics().create("ewfd", "ElectromagneticWavesFrequencyDomain", "geom1")
        physics = component.physics("ewfd")
        physics.create("sctr1", "Scattering", 1)
        physics.feature("sctr1").selection().named("sel_open")
        physics.create("pc1", "PeriodicCondition", 1)
        physics.feature("pc1").selection().named("sel_periodic_pair")
        physics.feature("pc1").set("PeriodicType", "Floquet")
        physics.feature("pc1").set("kFloquet", JArray(JString, 1)(["kx", "0", "0"]))

        component.cpl().create("int_up", "Integration")
        component.cpl("int_up").selection().named("sel_monitor_top")
        component.cpl().create("int_down", "Integration")
        component.cpl("int_down").selection().named("sel_monitor_bottom")

        component.mesh().create("mesh1")
        component.mesh("mesh1").autoMeshSize(3)
        component.mesh("mesh1").run()

        jmodel.study().create("std1")
        jmodel.study("std1").create("eig", "Eigenfrequency")
        jmodel.study("std1").feature("eig").set("shift", "f_shift")
        jmodel.study("std1").feature("eig").set("neigsactive", True)
        jmodel.study("std1").feature("eig").set("neigs", JInt(int(simulation["num_modes"])))
        jmodel.study("std1").createAutoSequences("all")
        jmodel.sol("sol1").runAll()

    @staticmethod
    def _export_mode_table(jmodel, path):
        jmodel.result().numerical().create("gev_modes", "EvalGlobal")
        result = jmodel.result().numerical("gev_modes")
        result.set("data", "dset1")
        result.set(
            "expr",
            [
                "real(ewfd.omega/2/pi)",
                "ewfd.Qfactor",
                "abs(real(int_up(ewfd.Poavy)))",
                "abs(real(int_down(ewfd.Poavy)))",
            ],
        )
        result.set("unit", ["THz", "1", "W/m", "W/m"])
        jmodel.result().table().create("tbl_modes", "Table")
        result.set("table", "tbl_modes")
        result.run()
        result.setResult()
        jmodel.result().table("tbl_modes").save(path)

    @staticmethod
    def _read_modes(path, state):
        raw = pd.read_csv(path, sep=r"\s+", comment="%", header=None)
        numeric = raw.apply(pd.to_numeric, errors="coerce").dropna(how="all")
        if numeric.shape[1] < 4:
            raise RuntimeError(f"Could not parse COMSOL mode metric table: {path}")
        values = numeric.iloc[:, -4:]
        modes = []
        for mode_index, row in values.iterrows():
            modes.append(
                ModeResult(
                    state=state,
                    mode_index=int(mode_index),
                    frequency_thz=float(row.iloc[0]),
                    q_total=float(row.iloc[1]),
                    power_up=float(row.iloc[2]),
                    power_down=float(row.iloc[3]),
                )
            )
        return modes
