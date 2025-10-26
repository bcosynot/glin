"""Compatibility shim package for legacy imports.

This package re-exports the public API from the renamed 'seev' package so
existing code and tests that import 'glin' continue to work.
"""

from seev import *  # noqa: F401,F403
