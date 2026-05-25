"""Platform-specific initialization utilities.

Import at the top of each entry-point module:
    from uniride_core.algorithms._platform import fix_windows_encoding
    fix_windows_encoding()
"""

import sys
import io


def fix_windows_encoding() -> None:
    """Fix Windows console UTF-8 encoding for Unicode output.

    On Windows, the default console encoding (charmap) cannot handle
    Unicode characters (e.g., Turkish: ş, ğ, ı, ö, ü, ç). This function
    reconfigures stdout/stderr to use UTF-8 with error replacement.

    Safe to call on all platforms — only applies on Windows.
    """
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


__all__ = ["fix_windows_encoding"]
