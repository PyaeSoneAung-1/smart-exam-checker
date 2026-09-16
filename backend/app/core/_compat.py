"""Compatibility shims for third-party imports.

`passlib` imports the standard-library `crypt` module, which is deprecated on
Python 3.11+ (removed in 3.13). The warning is pure noise for our bcrypt-only
usage, so it is suppressed here once, where the import actually happens — the
rest of the codebase imports `CryptContext` from this module.
"""
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from passlib.context import CryptContext

__all__ = ["CryptContext"]
