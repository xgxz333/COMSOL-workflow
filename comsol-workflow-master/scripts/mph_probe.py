import os
import sys
import traceback
from pathlib import Path


def prepare_windows_runtime(redirect_home=True):
    repo_root = Path(__file__).resolve().parents[1]
    user_home = repo_root / ".comsol_user_probe"
    if redirect_home:
        (user_home / ".comsol" / "v63" / "tomcat").mkdir(parents=True, exist_ok=True)
        (user_home / ".matplotlib").mkdir(parents=True, exist_ok=True)

        os.environ["HOME"] = str(user_home)
        os.environ["USERPROFILE"] = str(user_home)
        os.environ["MPLCONFIGDIR"] = str(user_home / ".matplotlib")
    os.environ.setdefault("COMSOL_ROOT", r"D:\Comsol\COMSOL63\Multiphysics")

    return repo_root, user_home


def dump_environment(user_home):
    print(f"Repo root: {Path(__file__).resolve().parents[1]}", flush=True)
    print(f"Probe HOME: {user_home}", flush=True)
    print(f"HOME env: {os.environ.get('HOME')}", flush=True)
    print(f"USERPROFILE env: {os.environ.get('USERPROFILE')}", flush=True)
    print(f"MPLCONFIGDIR env: {os.environ.get('MPLCONFIGDIR')}", flush=True)
    print(f"COMSOL_ROOT: {os.environ.get('COMSOL_ROOT')}", flush=True)


def probe_standalone():
    import mph

    print(f"MPh module: {mph.__file__}", flush=True)
    print(f"MPh config before: {mph.option()}", flush=True)
    mph.option("session", "stand-alone")
    print(f"MPh config after: {mph.option()}", flush=True)
    print("Calling mph.start()...", flush=True)
    client = mph.start()
    print(f"Client started: {client}", flush=True)

    java = client.java
    print(f"COMSOL version: {java.getComsolVersion()}", flush=True)
    print("hasProduct('COMSOL') ->", java.hasProduct("COMSOL"), flush=True)
    print("checkoutLicense('COMSOL') ->", java.checkoutLicense("COMSOL"), flush=True)
    print("About to call client.java.create('Model1')", flush=True)
    model = java.create("Model1")
    print(f"Model created: {model}", flush=True)


def main():
    print(f"Python: {sys.executable}", flush=True)
    print(f"Platform: {sys.platform}", flush=True)

    redirect_home = os.environ.get("MPH_PROBE_REDIRECT_HOME", "1") != "0"
    _, user_home = prepare_windows_runtime(redirect_home=redirect_home)
    dump_environment(user_home)

    try:
        probe_standalone()
    except Exception as exc:
        print(f"Probe failed: {exc.__class__.__name__}: {exc}", flush=True)
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
