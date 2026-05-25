import os


def get_repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_root(env_name, default_dir):
    value = os.environ.get(env_name)
    if value:
        if not os.path.isabs(value):
            value = os.path.join(get_repo_root(), value)
        return os.path.abspath(value)
    return os.path.join(get_repo_root(), default_dir)


def get_out_path(*parts):
    return os.path.join(_get_root("BILAYER_WORKFLOW_OUT_DIR", ".out"), *parts)


def get_workspace_path(*parts):
    return os.path.join(
        _get_root("BILAYER_WORKFLOW_WORKSPACES_DIR", "workspaces"), *parts
    )


def ensure_directory(path):
    os.makedirs(path, exist_ok=True)
    return path
