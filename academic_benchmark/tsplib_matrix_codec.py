"""Lossless storage codec for cached TSPLIB distance matrices.

Version 1: zlib(level 6) of the full n x n matrix (row-major bytes).
Version 2: lzma(preset 6) of the strict upper triangle (row-major bytes), original dtype.
           Only used for symmetric matrices with an all-zero diagonal; decoding mirrors
           the triangle and leaves the diagonal zero, bit-identical to the source.
"""
import lzma
import zlib
from typing import Tuple

import numpy as np

V1, V2 = 1, 2


def _tri_bytes(dm: np.ndarray) -> bytes:
    n = dm.shape[0]
    out = np.empty(n * (n - 1) // 2, dtype=dm.dtype)
    off = 0
    for i in range(n - 1):
        k = n - 1 - i
        out[off:off + k] = dm[i, i + 1:]
        off += k
    return out.tobytes()


def _is_v2_eligible(dm: np.ndarray) -> bool:
    return (
        dm.ndim == 2 and dm.shape[0] == dm.shape[1] and dm.shape[0] > 0
        and not np.any(np.diagonal(dm))
        and np.array_equal(dm, dm.T)
    )


def encode_matrix(dm: np.ndarray) -> Tuple[bytes, int]:
    """Return (blob, version). Falls back to v1 unless v2 round-trips bit-identically."""
    dm = np.ascontiguousarray(dm)
    if _is_v2_eligible(dm):
        blob = lzma.compress(_tri_bytes(dm), preset=6)
        if decode_matrix(blob, dm.shape[0], str(dm.dtype), V2).tobytes() == dm.tobytes():
            return blob, V2
    return zlib.compress(dm.tobytes(), level=6), V1


def decode_matrix(blob, n: int, dtype, version: int = 1) -> np.ndarray:
    """Decode a stored blob into a fresh, writable n x n array. Raises on corruption."""
    dt = np.dtype(dtype or "int32")
    blob = bytes(blob)
    if version in (None, V1):
        flat = np.frombuffer(zlib.decompress(blob), dtype=dt)
        if flat.size != n * n:
            raise ValueError(f"v1 matrix size mismatch: {flat.size} != {n}*{n}")
        return flat.reshape(n, n).copy()
    if version == V2:
        tri = np.frombuffer(lzma.decompress(blob), dtype=dt)
        if tri.size != n * (n - 1) // 2:
            raise ValueError(f"v2 triangle size mismatch: {tri.size} for n={n}")
        out = np.zeros((n, n), dtype=dt)
        off = 0
        for i in range(n - 1):
            k = n - 1 - i
            row = tri[off:off + k]
            out[i, i + 1:] = row
            out[i + 1:, i] = row
            off += k
        return out
    raise ValueError(f"unknown matrix storage version {version}")
