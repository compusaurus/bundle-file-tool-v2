"""BFT-owned PyThermX presentation settings shared by Tk and terminal adapters."""
from pathlib import Path
import warnings

PROFILE_PATH = Path(__file__).resolve().parents[2] / 'config' / 'pythermx_profile.json'


def load_progress_profile():
    from pythermx import load_profile, load_default_profile
    try:
        return load_profile(PROFILE_PATH)
    except (OSError, ValueError) as error:
        warnings.warn(f'BFT progress settings could not be loaded; using PyThermX defaults: {error}', RuntimeWarning)
        return load_default_profile()


def progress_enabled():
    return bool(load_progress_profile().as_dict()['enabled'])
