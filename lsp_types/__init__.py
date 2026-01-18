import importlib.metadata

from . import methods  # noqa: F401
from .requests import *  # noqa: F401, F403
from .semantic_tokens import CANONICAL_LEGEND  # noqa: F401
from .session import *  # noqa: F401, F403
from .types import *  # noqa: F401, F403

try:
    __version__ = importlib.metadata.version("lsp-types")
except Exception:
    __version__ = "0.0.0"  # Fallback for development
