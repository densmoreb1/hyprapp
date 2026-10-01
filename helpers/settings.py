import os
import pathlib
import shutil


def state_dir() -> pathlib.Path:
    """
    Directory holding everything the app writes. Whatever launches the app creates it.
    Inputs:
        None
    Outputs:
        Path to the state directory
    """
    STATE_DIR_VAR = "HYPRAPP_STATE_DIR"
    value = os.environ.get(STATE_DIR_VAR)
    if not value:
        raise RuntimeError(
            "%s is unset. The nix wrapper, the dev shell and the systemd unit "
            "each set it; export it by hand to run the app another way." % STATE_DIR_VAR
        )
    path = pathlib.Path(value)
    if not path.is_dir():
        raise RuntimeError("%s=%s does not exist" % (STATE_DIR_VAR, value))
    return path


def db_path() -> pathlib.Path:
    """
    Location of the SQLite database.
    Inputs:
        None
    Outputs:
        Path to fitness.db inside the state directory
    """
    return state_dir() / "fitness.db"


def config_path() -> pathlib.Path:
    """
    Credentials file, seeded from the packaged example the first time it is needed.
    Inputs:
        None
    Outputs:
        Path to config.yml inside the state directory
    """
    path = state_dir() / "config.yml"
    if not path.exists():
        example = (
            pathlib.Path(__file__).resolve().parent.parent
            / ".streamlit"
            / "config.yml.example"
        )
        shutil.copy(example, path)
        # Holds the cookie signing key and every user's password hash.
        path.chmod(0o600)
    return path
