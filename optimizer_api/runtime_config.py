import os


def optimizer_host() -> str:
    return os.getenv("OPTIMIZER_HOST", "127.0.0.1")
