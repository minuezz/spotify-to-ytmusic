from main import (
    artist_match_score,
    build_search_queries,
    classify_match,
    duration_score,
    extract_spotify_playlist_id,
    normalize,
    title_score,
)


def test_extract_spotify_playlist_id_from_url():
    assert (
        extract_spotify_playlist_id(
            "https://open.spotify.com/playlist/3cEYpjA9oz9GiPac4AsH4n?si=test"
        )
        == "3cEYpjA9oz9GiPac4AsH4n"
    )


def test_extract_spotify_playlist_id_accepts_plain_id():
    assert extract_spotify_playlist_id("abc123") == "abc123"


def test_normalize_removes_common_version_suffixes():
    assert normalize("Song (Radio Edit) [feat. Artist]") == "song"


def test_duration_score_prefers_close_duration():
    assert duration_score(180_000, 180) == 1.0
    assert duration_score(180_000, 200) == 0.0


def test_title_score_handles_normalized_titles():
    assert title_score("Ёлка — Song", "елка - song") == 1.0


def test_artist_aliases_match_cyrillic_and_latin_names():
    assert artist_match_score(["zamay"], [{"name": "замай"}]) == 1.0


def test_classify_match_thresholds():
    assert classify_match(0.90) == "exact"
    assert classify_match(0.72) == "good"
    assert classify_match(0.55) == "review"
    assert classify_match(0.54) == "bad"


def test_search_queries_include_isrc_and_are_deduplicated():
    track = {
        "title": "Song",
        "artists": ["Artist"],
        "artist_str": "Artist",
        "isrc": "TEST12345678",
    }
    queries = build_search_queries(track)
    assert "TEST12345678" in queries
    assert len(queries) == len({query.lower() for query in queries})
