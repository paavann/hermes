from __future__ import annotations
import hashlib
import re
from collections import Counter
from collections.abc import Sequence


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def normalize_tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.casefold())


def simhash_hex(text: str) -> str | None:
    """Return a 64-bit SimHash as 16 hex characters, or None for empty text."""
    tokens = normalize_tokens(text)
    if not tokens:
        return None

    vector = [0] * 64
    for token, weight in Counter(tokens).items():
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        for bit in range(64):
            vector[bit] += weight if (value >> bit) & 1 else -weight

    fingerprint = 0
    for bit, weight in enumerate(vector):
        if weight >= 0:
            fingerprint |= 1 << bit
    return f"{fingerprint:016x}"


def hamming_distance_hex(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cosine_similarity(
    left: Sequence[float],
    right: Sequence[float],
) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for left_value, right_value in zip(left, right, strict=True):
        dot += left_value * right_value
        left_norm += left_value * left_value
        right_norm += right_value * right_value
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return dot / ((left_norm**0.5) * (right_norm**0.5))
