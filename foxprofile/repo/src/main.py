import os
import sys
import ctypes
import faulthandler
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.app import create_app
from src.api.auth import check_bind_safety
from src.api.server import APIServer
from src.core.config import API_HOST, API_PORT, API_TOKEN, LOG_DIR
from src.core.container import Container
from src.core.logging import get_logger
from src.ui.app import App

logger = get_logger("main")


def install_crash_logging() -> None:
    """Leave a trace when the app dies: Python errors in the log, hard crashes in crash.log."""

    def log_uncaught(exc_type, exc, tb):
        logger.critical("Uncaught exception", exc_info=(exc_type, exc, tb))

    def log_thread(args):
        logger.critical(
            "Uncaught exception in thread %s",
            args.thread.name if args.thread else "?",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = log_uncaught
    threading.excepthook = log_thread
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        # Kept open for the life of the process: faulthandler writes to it from the crash handler.
        faulthandler.enable(open(os.path.join(LOG_DIR, "crash.log"), "a", buffering=1))
    except OSError:
        pass


def main() -> None:
    check_bind_safety(API_HOST, API_TOKEN)
    container = Container()
    install_crash_logging()

    fastapi_app = create_app(container)
    api_server = APIServer(fastapi_app)
    api_server.start()
    logger.info("API available at http://%s:%s/api/v1", API_HOST, API_PORT)

    try:
        gui = App(container)
        gui.run()
    finally:
        api_server.stop()


if __name__ == "__main__":
    ctypes.windll.kernel32.SetConsoleTitleW('Muse2tele_FoxProfile')
    main()
