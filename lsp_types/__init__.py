from .requests import *  # noqa: F401, F403
from .session import *  # noqa: F401, F403
from .types import *  # noqa: F401, F403

import importlib.metadata

try:
    __version__ = importlib.metadata.version("lsp-types")
except Exception:
    __version__ = "0.0.0"  # Fallback for development
