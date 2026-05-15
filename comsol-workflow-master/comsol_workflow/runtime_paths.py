import os
import tempfile


def get_repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_root_from_env(env_name, default_dir_name):
    value = os.environ.get(env_name)
    if value:
        if not os.path.isabs(value):
            value = os.path.join(get_repo_root(), value)
        return os.path.abspath(value)
    return os.path.join(get_repo_root(), default_dir_name)


def get_out_root():
    return _get_root_from_env("COMSOL_WORKFLOW_OUT_DIR", ".out")


def get_workspaces_root():
    return _get_root_from_env("COMSOL_WORKFLOW_WORKSPACES_DIR", "workspaces")


def get_workspace_tmp_root():
    return os.path.join(get_workspaces_root(), "_tmp")


def get_out_path(*parts):
    return os.path.join(get_out_root(), *parts)


def get_workspaces_path(*parts):
    return os.path.join(get_workspaces_root(), *parts)


def get_tests_out_path(*parts):
    return get_out_path("tests", *parts)


def ensure_directory(path):
    os.makedirs(path, exist_ok=True)
    return path


def make_workspace_temp_dir(prefix="cw_"):
    return tempfile.mkdtemp(prefix=prefix, dir=ensure_directory(get_workspace_tmp_root()))


def get_max_processes(default):
    raw_value = os.environ.get("COMSOL_WORKFLOW_MAX_PROCESSES")
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    return value if value > 0 else default
