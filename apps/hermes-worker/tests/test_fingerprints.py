from hermes_worker.jobs.fingerprints import (
    cosine_similarity,
    hamming_distance_hex,
    normalize_tokens,
    sha256_hex,
    simhash_hex,
)


def test_simhash_is_stable_and_hex_encoded() -> None:
    text = "A magnitude 6.1 earthquake struck the coast on Tuesday."
    first = simhash_hex(text)
    second = simhash_hex(text)

    assert first is not None
    assert first == second
    assert len(first) == 16
    assert int(first, 16) >= 0


def test_simhash_returns_none_for_empty_text() -> None:
    assert simhash_hex("") is None
    assert simhash_hex("   ,.;  ") is None


def test_simhash_groups_near_duplicate_text() -> None:
    original = (
        "Rescue teams searched collapsed buildings after a magnitude 6.1 "
        "earthquake struck the region on Tuesday."
    )
    copy = (
        "Rescue teams searched collapsed buildings after a magnitude 6.1 "
        "earthquake struck the region on Tuesday, officials said."
    )
    unrelated = (
        "The central bank raised interest rates by twenty five basis points "
        "at its policy meeting on Wednesday."
    )

    original_hash = simhash_hex(original)
    copy_hash = simhash_hex(copy)
    unrelated_hash = simhash_hex(unrelated)

    assert original_hash is not None
    assert copy_hash is not None
    assert unrelated_hash is not None
    assert hamming_distance_hex(original_hash, copy_hash) <= 6
    assert hamming_distance_hex(original_hash, unrelated_hash) > 6


def test_normalize_tokens_casefolds_and_splits_words() -> None:
    assert normalize_tokens("Quake Hits, Coastal City!") == [
        "quake",
        "hits",
        "coastal",
        "city",
    ]


def test_sha256_hex_is_deterministic() -> None:
    assert sha256_hex("hello") == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def test_cosine_similarity_bounds() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosine_similarity_known_value() -> None:
    similarity = cosine_similarity([1.0, 1.0], [1.0, 0.0])
    assert abs(similarity - 0.7071067811865475) < 1e-12
