import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _env(key: str, default: str) -> str:
    """Read the FOXPROFILE_<key> environment variable."""
    return os.getenv(f"FOXPROFILE_{key}", default)


PROFILES_FILE = _env("PROFILES_FILE", "profiles.json")
DATA_DIR = _env("DATA_DIR", "camoufox_data")
LOG_DIR = _env("LOG_DIR", "logs")
SETTINGS_FILE = _env("SETTINGS_FILE", "settings.json")
LOG_LEVEL = _env("LOG_LEVEL", "INFO")
PROXY_CHECK_TIMEOUT = int(_env("PROXY_TIMEOUT", "10"))
LANGUAGE = _env("LANG", "en")

API_HOST = _env("API_HOST", "127.0.0.1")
API_PORT = int(_env("API_PORT", "8000"))

# Seconds the API waits for a launched browser to report ready or failed.
LAUNCH_WAIT_TIMEOUT = int(_env("LAUNCH_TIMEOUT", "90"))

# After this many failed launches of one profile within LAUNCH_FAILURE_WINDOW
# seconds, the API refuses to launch it for LAUNCH_BACKOFF seconds (429), so a
# client retrying in a loop cannot exhaust the machine. 0 turns it off.
LAUNCH_FAILURE_LIMIT = int(_env("LAUNCH_FAILURE_LIMIT", "3"))
LAUNCH_FAILURE_WINDOW = int(_env("LAUNCH_FAILURE_WINDOW", "120"))
LAUNCH_BACKOFF = int(_env("LAUNCH_BACKOFF", "300"))

# Where files a browser downloads are saved. The folder set in the web panel
# (settings.json) wins; this is the default until one is chosen.
DOWNLOAD_DIR = _env("DOWNLOAD_DIR", "")

FINGERPRINT_FILE = "fingerprint.json"


def _headless(value: str) -> bool | str:
    """'true'/'false', or 'virtual' (Linux: hidden Xvfb display, more stealthy)."""
    value = value.strip().lower()
    if value == "virtual":
        return "virtual"
    return value in ("1", "true", "yes")


# Browsers open hidden when true; server mode turns this on by default.
HEADLESS = _headless(_env("HEADLESS", "false"))

# Reopen the tabs a profile had open when it was last stopped.
RESTORE_TABS = _env("RESTORE_TABS", "true").strip().lower() in ("1", "true", "yes")


def _window_size(value: str) -> tuple[int, int] | None:
    """'1280x800' -> (1280, 800); empty or malformed -> None."""
    width, sep, height = value.strip().lower().partition("x")
    if sep and width.isdigit() and height.isdigit() and int(width) and int(height):
        return int(width), int(height)
    return None


# Outer window size for every launch, e.g. 1280x800, applied over the saved
# fingerprint (fingerprint.json is not changed). A smaller window needs less GPU
# memory. Empty keeps the fingerprint's own size.
WINDOW_SIZE = _window_size(_env("WINDOW_SIZE", ""))

# Shared secret for the REST API, the web panel and the MCP server. Required
# whenever the API listens on anything other than the loopback interface.
API_TOKEN = _env("API_TOKEN", "")
