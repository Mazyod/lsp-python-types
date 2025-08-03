# Pyrefly configuration schema
# Based on CLI options documented in PYREFLY_GUIDE.md
# Note: Pyrefly configuration is still evolving, this is a minimal implementation

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

# Basic configuration options based on Pyrefly CLI
IndexingMode = Literal["none", "lazy-non-blocking-background", "lazy-blocking"]


class Model(TypedDict):
    """
    Pyrefly Configuration Schema

    Based on available CLI options and environment variables.
    Note: Pyrefly's configuration format is still evolving.
    """

    # Core options
    verbose: NotRequired[bool]
    threads: NotRequired[int]  # 0 = auto, 1 = sequential, higher = parallel
    color: NotRequired[Literal["auto", "always", "never"]]

    # LSP server options
    indexing_mode: NotRequired[IndexingMode]  # Indexing strategy for LSP server

    # File inclusion/exclusion (basic patterns)
    include: NotRequired[list[str]]
    exclude: NotRequired[list[str]]

    # Environment variables that can be configured
    pyrefly_threads: NotRequired[int]
    pyrefly_color: NotRequired[str]
    pyrefly_verbose: NotRequired[bool]
