import os
import shutil
import numpy as np
from pathlib import Path

from runtime_paths import ensure_directory, get_repo_root

_MPH_IMPORT_ERROR = None
_JPYPE_IMPORT_ERROR = None

try:
    import mph
except Exception as exc:
    mph = None
    _MPH_IMPORT_ERROR = exc

try:
    from jpype.types import JArray, JDouble, JInt, JString
except Exception as exc:
    JArray = JDouble = JInt = JString = None
    _JPYPE_IMPORT_ERROR = exc

class SimulationRun:
    @staticmethod
    def _root_from_comsol_command(comsol_command):
        command_path = Path(comsol_command).resolve()
        # COMSOL executables live under <root>/bin/win64 on Windows.
        return str(command_path.parent.parent.parent)

    @staticmethod
    def _version_home_dir_name(comsol_root):
        name = Path(comsol_root).parent.name
        digits = "".join(ch for ch in name if ch.isdigit())
        if len(digits) >= 2:
            return f"v{digits[:2]}"
        return "v62"

    @staticmethod
    def _prepend_path(path):
        path = str(path)
        current_paths = os.environ.get("PATH", "").split(os.pathsep)
        if path not in current_paths:
            os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")

    @staticmethod
    def _prepare_windows_runtime():
        repo_root = get_repo_root()
        user_home = ensure_directory(os.path.join(repo_root, ".comsol_user"))
        ensure_directory(os.path.join(user_home, ".matplotlib"))

        if os.environ.get("COMSOL_WORKFLOW_ISOLATE_USER_HOME") == "1":
            os.environ["HOME"] = user_home
            os.environ["USERPROFILE"] = user_home
        os.environ["MPLCONFIGDIR"] = os.path.join(user_home, ".matplotlib")

        comsol_command = SimulationRun._find_comsol_command()
        if comsol_command:
            comsol_root = SimulationRun._root_from_comsol_command(comsol_command)
            os.environ["COMSOL_ROOT"] = comsol_root
            SimulationRun._prepend_path(os.path.dirname(comsol_command))
            ensure_directory(
                os.path.join(
                    user_home,
                    ".comsol",
                    SimulationRun._version_home_dir_name(comsol_root),
                    "tomcat",
                )
            )

    @staticmethod
    def _find_comsol_command():
        command_names = ["comsol", "comsolbatch", "comsolmphserver", "mphserver"]

        for command in command_names:
            resolved = shutil.which(command)
            if resolved:
                return resolved

        candidate_roots = []
        env_root = os.environ.get("COMSOL_ROOT")
        if env_root:
            candidate_roots.append(env_root)

        candidate_roots.extend([
            r"D:\Comsol\COMSOL63\Multiphysics",
            r"D:\Comsol\COMSOL62\Multiphysics",
            r"C:\Program Files\COMSOL\COMSOL63\Multiphysics",
            r"C:\Program Files\COMSOL\COMSOL62\Multiphysics",
            r"C:\Program Files\COMSOL\COMSOL61\Multiphysics",
        ])

        for root in candidate_roots:
            bin_dir = os.path.join(root, "bin", "win64")
            for command in command_names:
                exe_path = os.path.join(bin_dir, f"{command}.exe")
                if os.path.isfile(exe_path):
                    return exe_path

        return None

    def __init__(self):
        self.client = None
        self.model = None
        self._ensure_runtime_ready()

        try:
            if os.name == "nt":
                session = os.environ.get("COMSOL_WORKFLOW_MPH_SESSION", "client-server")
                mph.option("session", session)
            version = os.environ.get("COMSOL_VERSION")
            self.client = mph.start(version=version)
            self.model = self.client.create("Model")
        except Exception as exc:
            raise RuntimeError(
                "Failed to start COMSOL through MPh/JPype. Ensure COMSOL is installed, its executables are on PATH, "
                "and the active Python 3.10 environment contains both `MPh` and `jpype1`."
            ) from exc
    
    def __del__(self):
        try:
            self.clear()
        except Exception:
            pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clear()
        return False

    @staticmethod
    def _ensure_runtime_ready():
        if _MPH_IMPORT_ERROR is not None:
            raise RuntimeError(
                "MPh is unavailable. Install `MPh` in the active Python 3.10 environment before running COMSOL-dependent scripts."
            ) from _MPH_IMPORT_ERROR

        if _JPYPE_IMPORT_ERROR is not None:
            raise RuntimeError(
                "JPype is unavailable. Install `jpype1` in the active Python 3.10 environment before running COMSOL-dependent scripts."
            ) from _JPYPE_IMPORT_ERROR

        if os.name == "nt":
            SimulationRun._prepare_windows_runtime()
            comsol_command = SimulationRun._find_comsol_command()
            if comsol_command is None:
                raise RuntimeError(
                    "COMSOL executables were not found. Add COMSOL to PATH or set COMSOL_ROOT to the COMSOL Multiphysics install directory."
                )

    def clear(self):
        if self.client is None or self.model is None:
            return

        try:
            self.client.remove(self.model)
        finally:
            self.model = None

    def build_and_run(self, a, triangles, k=None):
        jmodel = self.model.java  # com.comsol.model.Model

        jmodel.param().set("a", f"{a} [um]")
        jmodel.param().set("H", "200 [nm]")
        jmodel.param().set("H_air", "lda0")
        jmodel.param().set("lda0", "1550 [nm]")
        jmodel.param().set("G", "4*pi/sqrt(3)/a")
        
        if k is not None:
            jmodel.param().set("kx", f"{k['kx']}*G")
            jmodel.param().set("ky", f"{k['ky']}*G")
        else:
            jmodel.param().set("kx", f"0*G")
            jmodel.param().set("ky", f"0*G")

        jmodel.component().create("comp1", True)
        jmodel.component("comp1").geom().create("geom1", 3)
        jmodel.component("comp1").mesh().create("mesh1")

        jmodel.component("comp1").geom("geom1").lengthUnit("um")
        jmodel.component("comp1").geom("geom1").create("wp1", "WorkPlane")
        jmodel.component("comp1").geom("geom1").feature("wp1").set("unite", True)

        hex_table = [
            ["a/sqrt(3)*cos(pi/6)", "a/sqrt(3)*sin(pi/6)"],
            ["0", "a/sqrt(3)"],
            ["-a/sqrt(3)*cos(pi/6)", "a/sqrt(3)*sin(pi/6)"],
            ["-a/sqrt(3)*cos(pi/6)", "-a/sqrt(3)*sin(pi/6)"],
            ["0", "-a/sqrt(3)"],
            ["a/sqrt(3)*cos(pi/6)", "-a/sqrt(3)*sin(pi/6)"],
        ]

        jmodel.component("comp1").geom("geom1").feature("wp1").geom().create("pol1", "Polygon")
        jmodel.component("comp1").geom("geom1").feature("wp1").geom().feature("pol1").label("Hex")
        jmodel.component("comp1").geom("geom1").feature("wp1").geom().feature("pol1").set("source", "table")
        jmodel.component("comp1").geom("geom1").feature("wp1").geom().feature("pol1").set(
            "table",
            JArray(JString, 2)(hex_table),
        )

        tri_tables = {
            f"pol{i + 2}": (
                f"Tri_{i + 1}",
                [[f"{x} [um]", f"{y} [um]"] for (x, y) in tri],
            )
            for i, tri in enumerate(triangles)
        }

        for tag, (label, table) in tri_tables.items():
            jmodel.component("comp1").geom("geom1").feature("wp1").geom().create(tag, "Polygon")
            jmodel.component("comp1").geom("geom1").feature("wp1").geom().feature(tag).label(label)
            jmodel.component("comp1").geom("geom1").feature("wp1").geom().feature(tag).set("source", "table")
            jmodel.component("comp1").geom("geom1").feature("wp1").geom().feature(tag).set(
                "table",
                JArray(JString, 2)(table),
            )

        jmodel.component("comp1").geom("geom1").create("ext1", "Extrude")
        jmodel.component("comp1").geom("geom1").feature("ext1").setIndex("distance", "H/2", 0)
        jmodel.component("comp1").geom("geom1").feature("ext1").selection("input").set("wp1")

        jmodel.component("comp1").geom("geom1").create("wp2", "WorkPlane")
        jmodel.component("comp1").geom("geom1").feature("wp2").set("quickz", "H/2")
        jmodel.component("comp1").geom("geom1").feature("wp2").set("unite", True)

        jmodel.component("comp1").geom("geom1").feature("wp2").geom().create("pol8", "Polygon")
        jmodel.component("comp1").geom("geom1").feature("wp2").geom().feature("pol8").label("Hex 1")
        jmodel.component("comp1").geom("geom1").feature("wp2").geom().feature("pol8").set("source", "table")
        jmodel.component("comp1").geom("geom1").feature("wp2").geom().feature("pol8").set(
            "table",
            JArray(JString, 2)(hex_table),
        )

        jmodel.component("comp1").geom("geom1").create("ext2", "Extrude")
        jmodel.component("comp1").geom("geom1").feature("ext2").set(
            "distance",
            JArray(JString, 1)(["H_air", "H_air*1.5"]),
        )
        jmodel.component("comp1").geom("geom1").feature("ext2").set(
            "scale",
            JArray(JDouble, 2)([[1.0, 1.0], [1.0, 1.0]]),
        )
        jmodel.component("comp1").geom("geom1").feature("ext2").set(
            "displ",
            JArray(JDouble, 2)([[0.0, 0.0], [0.0, 0.0]]),
        )
        jmodel.component("comp1").geom("geom1").feature("ext2").set(
            "twist",
            JArray(JInt, 1)([0, 0]),
        )
        jmodel.component("comp1").geom("geom1").feature("ext2").selection("input").set("wp2")

        jmodel.component("comp1").geom("geom1").run()

        jmodel.component("comp1").selection().create("sel1", "Explicit")
        jmodel.component("comp1").selection("sel1").geom("geom1", 2)
        jmodel.component("comp1").selection("sel1").set(JArray(JInt, 1)([3]))
        jmodel.component("comp1").selection("sel1").label("bottom")
        jmodel.component("comp1").selection("sel1").set("groupcontang", True)

        jmodel.component("comp1").material().create("mat1", "Common")
        jmodel.component("comp1").material().create("mat2", "Common")
        jmodel.component("comp1").material("mat1").propertyGroup().create("RefractiveIndex", "Refractive Index")
        jmodel.component("comp1").material("mat2").selection().set(JArray(JInt, 1)([1]))
        jmodel.component("comp1").material("mat2").propertyGroup().create("RefractiveIndex", "Refractive Index")

        jmodel.component("comp1").coordSystem().create("pml1", "PML")
        jmodel.component("comp1").coordSystem("pml1").selection().set(JArray(JInt, 1)([3]))

        jmodel.component("comp1").physics().create("ewfd", "ElectromagneticWavesFrequencyDomain", "geom1")
        jmodel.component("comp1").physics("ewfd").create("sctr1", "Scattering", 2)
        jmodel.component("comp1").physics("ewfd").feature("sctr1").selection().set(JArray(JInt, 1)([10]))

        jmodel.component("comp1").physics("ewfd").create("pmc1", "PerfectMagneticConductor", 2)
        jmodel.component("comp1").physics("ewfd").feature("pmc1").selection().named("sel1")

        jmodel.component("comp1").physics("ewfd").create("pc1", "PeriodicCondition", 2)
        jmodel.component("comp1").physics("ewfd").feature("pc1").selection().set(JArray(JInt, 1)([2, 5, 8, 32, 33, 34]))

        jmodel.component("comp1").physics("ewfd").create("pc2", "PeriodicCondition", 2)
        jmodel.component("comp1").physics("ewfd").feature("pc2").selection().set(JArray(JInt, 1)([11, 12, 13, 29, 30, 31]))

        jmodel.component("comp1").physics("ewfd").create("pc3", "PeriodicCondition", 2)
        jmodel.component("comp1").physics("ewfd").feature("pc3").selection().set(JArray(JInt, 1)([1, 4, 7, 50, 51, 52]))

        if k is not None:
            jmodel.component("comp1").physics("ewfd").feature("pc1").set("PeriodicType", "Floquet")
            jmodel.component("comp1").physics("ewfd").feature("pc1").set("kFloquet", JArray(JString, 1)(["kx", "ky", "0"]))

            jmodel.component("comp1").physics("ewfd").feature("pc2").set("PeriodicType", "Floquet")
            jmodel.component("comp1").physics("ewfd").feature("pc2").set("kFloquet", JArray(JString, 1)(["kx", "ky", "0"]))

            jmodel.component("comp1").physics("ewfd").feature("pc3").set("PeriodicType", "Floquet")
            jmodel.component("comp1").physics("ewfd").feature("pc3").set("kFloquet", JArray(JString, 1)(["kx", "ky", "0"]))

        jmodel.component("comp1").view("view1").set("scenelight", False)
        jmodel.component("comp1").view("view2").axis().set("xmin", -0.7867843508720398)
        jmodel.component("comp1").view("view2").axis().set("xmax", 0.830589234828949)
        jmodel.component("comp1").view("view2").axis().set("ymin", -0.6027438640594482)
        jmodel.component("comp1").view("view2").axis().set("ymax", 0.7357029914855957)
        jmodel.component("comp1").view("view3").axis().set("xmin", -6.29296152965253e-7)
        jmodel.component("comp1").view("view3").axis().set("xmax", 6.29296152965253e-7)
        jmodel.component("comp1").view("view3").axis().set("ymin", -5.207699018683343e-7)
        jmodel.component("comp1").view("view3").axis().set("ymax", 5.207699018683343e-7)

        jmodel.component("comp1").material("mat1").label("Air")
        jmodel.component("comp1").material("mat1").propertyGroup("RefractiveIndex").set("n", "")
        jmodel.component("comp1").material("mat1").propertyGroup("RefractiveIndex").set("ki", "")
        jmodel.component("comp1").material("mat1").propertyGroup("RefractiveIndex").set(
            "n",
            JArray(JString, 1)(["1", "0", "0", "0", "1", "0", "0", "0", "1"]),
        )
        jmodel.component("comp1").material("mat1").propertyGroup("RefractiveIndex").set(
            "ki",
            JArray(JString, 1)(["0", "0", "0", "0", "0", "0", "0", "0", "0"]),
        )

        jmodel.component("comp1").material("mat2").label("Mat")
        jmodel.component("comp1").material("mat2").propertyGroup("RefractiveIndex").set("n", "")
        jmodel.component("comp1").material("mat2").propertyGroup("RefractiveIndex").set("ki", "")
        jmodel.component("comp1").material("mat2").propertyGroup("RefractiveIndex").set("n", "")
        jmodel.component("comp1").material("mat2").propertyGroup("RefractiveIndex").set("ki", "")
        jmodel.component("comp1").material("mat2").propertyGroup("RefractiveIndex").set(
            "n",
            JArray(JString, 1)(["3.3", "0", "0", "0", "3.3", "0", "0", "0", "3.3"]),
        )
        jmodel.component("comp1").material("mat2").propertyGroup("RefractiveIndex").set(
            "ki",
            JArray(JString, 1)(["0", "0", "0", "0", "0", "0", "0", "0", "0"]),
        )

        jmodel.study().create("std1")
        jmodel.study("std1").create("eig", "Eigenfrequency")
        jmodel.study("std1").feature("eig").set("shift", "c_const/1.55[um]")
        jmodel.study("std1").feature("eig").set("neigsactive", True)
        jmodel.study("std1").feature("eig").set("neigs", JInt(8))

        jmodel.component("comp1").mesh("mesh1").run()

        jmodel.study("std1").createAutoSequences("all")

        jmodel.sol("sol1").runAll()

        # output 1: eigenfrequencies
        jmodel.result().numerical().create("gev1", "EvalGlobal")
        jmodel.result().numerical("gev1").label("Eigenfrequencies (ewfd)")
        jmodel.result().numerical("gev1").set("data", "dset1")
        # angular freq = omega + i damp, Q = omega / (2*damp)
        # freq = angular freq / (2*pi), so divide by 2*pi to get freq and damp in THz
        jmodel.result().numerical("gev1").set("expr", ["ewfd.omega/2/pi", "ewfd.damp/2/pi", "ewfd.Qfactor"])
        jmodel.result().numerical("gev1").set("unit", ["THz", "THz", "1"])

        jmodel.result().table().create("tbl1", "Table")
        jmodel.result().numerical("gev1").set("table", "tbl1")
        jmodel.result().numerical("gev1").run()
        jmodel.result().numerical("gev1").setResult()

        # output 2: 2D field
        # center
        jmodel.result().dataset().create("cpl1", "CutPlane")
        jmodel.result().dataset("cpl1").set("quickplane", "xy")
        # air
        jmodel.result().dataset().create("cpl2", "CutPlane")
        jmodel.result().dataset("cpl2").set("quickplane", "xy")
        jmodel.result().dataset("cpl2").set("quickz", "0.75*H_air")
        # yz
        jmodel.result().dataset().create("cpl3", "CutPlane")
        jmodel.result().dataset("cpl3").set("quickplane", "yz")
        # xz
        jmodel.result().dataset().create("cpl4", "CutPlane")
        jmodel.result().dataset("cpl4").set("quickplane", "xz")

        self.plane_datasets = {
            "center": "cpl1",
            "air":    "cpl2",
            "yz":     "cpl3",
            "xz":     "cpl4",
        }
        jmodel.result().numerical().create("int1", "Interp")

        jmodel.result().create("pg1", "PlotGroup2D")
        jmodel.result("pg1").label("2D Field (ewfd)")
        jmodel.result("pg1").run()
        jmodel.result("pg1").create("surf1", "Surface")
        jmodel.result("pg1").feature("surf1").set("expr", "ewfd.normH")
        jmodel.result("pg1").run()
        jmodel.result().export().create("plot1", "pg1", "surf1", "Plot")
        jmodel.result().export().create("img1", "pg1", "Image")
        jmodel.result().export("img1").set("target", "file")

        # output 3: 3D field
        jmodel.result().create("pg2", "PlotGroup3D")
        jmodel.result("pg2").run()
        jmodel.result("pg2").label("3D Plot")
        jmodel.result("pg2").create("mslc1", "Multislice")
        jmodel.result("pg2").feature("mslc1").set("multiplanexmethod", "coord")
        jmodel.result("pg2").feature("mslc1").set("xcoord", JInt(0))
        jmodel.result("pg2").feature("mslc1").set("multiplaneymethod", "coord")
        jmodel.result("pg2").feature("mslc1").set("ycoord", JInt(0))
        jmodel.result("pg2").feature("mslc1").set("multiplanezmethod", "coord")
        jmodel.result("pg2").feature("mslc1").set("zcoord", JInt(0))
        jmodel.result("pg2").feature("mslc1").set("expr", "ewfd.normE")
        jmodel.result("pg2").run()
        jmodel.result().export().create("img2", "pg2", "Image")
        jmodel.result().export("img2").set("target", "file")

        return

    def export_eigenfrequencies(self, save_path):
        os.makedirs(save_path, exist_ok=True)
        jmodel = self.model.java  # com.comsol.model.Model
        jmodel.result().table("tbl1").save(os.path.join(save_path, "eigenfrequencies.txt"))
    
    def get_eigenfrequencies(self):
        jmodel = self.model.java
        jmodel.result().numerical("gev1").run()
        data = np.asarray(jmodel.result().numerical("gev1").getReal()).T  # (expr, N) -> (N, expr)
        return data

    def export_2d_fields(self, eigenmode_idx, expr, expr_name, save_path, plane="center", export_data=True, export_image=True):
        os.makedirs(save_path, exist_ok=True)
        jmodel = self.model.java  # com.comsol.model.Model
        jmodel.result("pg1").run()
        jmodel.result("pg1").set("data", self.plane_datasets[plane])
        jmodel.result("pg1").set("looplevel", JArray(JInt, 1)([eigenmode_idx + 1]))
        jmodel.result("pg1").feature("surf1").set("expr", expr)
        jmodel.result("pg1").run()
        if export_data:
            jmodel.result().export("plot1").set("filename", os.path.join(save_path, f"{eigenmode_idx:02d}_{expr_name}_{plane}_2d.txt"))
            jmodel.result().export("plot1").run()
        if export_image:
            jmodel.result().export("img1").set("pngfilename", os.path.join(save_path, f"{eigenmode_idx:02d}_{expr_name}_{plane}_2d.png"))
            jmodel.result().export("img1").run()
    
    # Interp Doc: https://doc.comsol.com/6.3/docserver/#!/com.comsol.help.comsol/comsol_api_results.52.075.html
    def get_2d_fields(self, eigenmode_idx, expr, plane="center"):
        jmodel = self.model.java
        jmodel.result().numerical("int1").set("data", self.plane_datasets[plane])
        jmodel.result().numerical("int1").set("expr", JArray(JString, 1)([expr]))
        jmodel.result().numerical("int1").set("solnum", JArray(JInt, 1)([eigenmode_idx + 1]))
        jmodel.result().numerical("int1").run()

        coords = np.asarray(jmodel.result().numerical("int1").getCoordinates()).T # (2, N) -> (N, 2)
        values = np.asarray(jmodel.result().numerical("int1").getData()).reshape(-1) # (expr, solnum, coordinates) -> (N,)
        return coords, values

    def export_3d_fields(self, eigenmode_idx, expr, expr_name, save_path):
        os.makedirs(save_path, exist_ok=True)
        jmodel = self.model.java  # com.comsol.model.Model
        jmodel.result("pg2").run()
        jmodel.result("pg2").set("data", "dset1")
        jmodel.result("pg2").set("looplevel", JArray(JInt, 1)([eigenmode_idx + 1]))
        jmodel.result("pg2").feature("mslc1").set("expr", expr)
        jmodel.result("pg2").run()
        jmodel.result().export("img2").set("pngfilename", os.path.join(save_path, f"{eigenmode_idx:02d}_{expr_name}_3d.png"))
        jmodel.result().export("img2").run()
