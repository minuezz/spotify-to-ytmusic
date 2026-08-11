import argparse
import os
import re
import csv
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Tuple

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from ytmusicapi import YTMusic

load_dotenv()

SPOTIFY_SCOPES = "playlist-read-private playlist-read-collaborative user-read-private"

# =========================
# SETTINGS
# =========================
DEFAULT_YTMUSIC_AUTH = "browser.json"
DEFAULT_CACHE_FILE = "matches_cache.json"
DEFAULT_REPORT_FILE = "transfer_report.csv"
DEFAULT_YTMUSIC_PLAYLIST_DESC = "Migrated from Spotify with spotTrans"

RECHECK_REVIEW = True
RECHECK_GOOD = False

DEBUG_TRACKS = {
    # ("Уходящая натура", "Zamay"),
    # ("Винтаж", "Zamay"),
    # ("Абориген", "Zamay"),
}

SEARCH_LIMIT = 5
REQUEST_SLEEP = 0.15
BATCH_SIZE = 50

# =========================
# ARTISTS' ALIASES
# =========================
ARTIST_ALIASES = {
    "max korzh": ["макс корж"],
    "макс корж": ["max korzh"],

    "zveri": ["звери"],
    "звери": ["zveri"],

    "neschastny sluchai": ["несчастный случай"],
    "несчастный случай": ["neschastny sluchai"],

    "semyon slepakov": ["семен слепаков", "семён слепаков"],
    "семен слепаков": ["semyon slepakov", "семён слепаков"],
    "семён слепаков": ["semyon slepakov", "семен слепаков"],

    "neuromonakh feofan": ["нейромонах феофан"],
    "нейромонах феофан": ["neuromonakh feofan"],

    "slava kpss": ["слава кпсс", "гнойный"],
    "слава кпсс": ["slava kpss", "гнойный"],

    "vremya i steklo": ["время и стекло"],
    "время и стекло": ["vremya i steklo"],

    "gradusy": ["градусы", 'группа "градусы"'],
    "градусы": ["gradusy", 'группа "градусы"'],
    'группа "градусы"': ["gradusy", "градусы"],

    "luna": ["луна"],
    "луна": ["luna"],

    "vorovayki": ["воровайки"],
    "воровайки": ["vorovayki"],

    "professor lebedinskiy": ["профессор лебединский"],
    "профессор лебединский": ["professor lebedinskiy"],

    "pasha technique": ["паша техник"],
    "паша техник": ["pasha technique"],

    "dyuna": ["дюна"],
    "дюна": ["dyuna"],

    "marliny": ["марлины"],
    "марлины": ["marliny"],

    "golos omeriki": ["голос омерики"],
    "голос омерики": ["golos omeriki"],

    "elektroslabost": ["электрослабость"],
    "электрослабость": ["elektroslabost"],

    "zamay": ["замай"],
    "замай": ["zamay"],

    "sd": ["сд"],
    "сд": ["sd"],

    "dolphin": ["дельфин"],
    "дельфин": ["dolphin"],

    "mukka": ["мукка"],
    "мукка": ["mukka"],

    "zemfira": ["земфира"],
    "земфира": ["zemfira"],

    "leningrad": ["ленинград"],
    "ленинград": ["leningrad"],

    "kino": ["кино"],
    "кино": ["kino"],

    "viktor tsoi": ["виктор цой"],
    "виктор цой": ["viktor tsoi"],

    "poshlaya molly": ["пошлая молли"],
    "пошлая молли": ["poshlaya molly"],

    "hleb": ["хлеб"],
    "хлеб": ["hleb"],

    "monetochka": ["монеточка"],
    "монеточка": ["monetochka"],

    "nol": ["ноль"],
    "ноль": ["nol"],

    "my": ["мы"],
    "мы": ["my"],

    "polumyagkiye": ["полумягкие"],
    "полумягкие": ["polumyagkiye"],

    "proyekt uvechye": ["проект увечье"],
    "проект увечье": ["proyekt uvechye"],

    "pyrokinesis": ["пирокинезис"],
    "пирокинезис": ["pyrokinesis"],
}

# =========================
# UTILITIES
# =========================
def extract_spotify_playlist_id(url_or_id: str) -> str:
    if "open.spotify.com/playlist/" in url_or_id:
        m = re.search(r"playlist/([a-zA-Z0-9]+)", url_or_id)
        if not m:
            raise ValueError("Не удалось извлечь Spotify playlist id")
        return m.group(1)
    return url_or_id.strip()


def spotify_client() -> spotipy.Spotify:
    required = ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Missing Spotify configuration: " + ", ".join(missing) +
            ". Copy .env.example to .env and fill in your Spotify app credentials."
        )

    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            scope=SPOTIFY_SCOPES,
            client_id=os.environ["SPOTIPY_CLIENT_ID"],
            client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
            redirect_uri=os.environ["SPOTIPY_REDIRECT_URI"],
            open_browser=True,
            cache_path=".spotify_cache",
        )
    )


def is_debug_track(track: Dict) -> bool:
    return (track["title"], track["artists"][0] if track["artists"] else "") in DEBUG_TRACKS


def normalize(s: str) -> str:
    s = (s or "").lower().strip()
    s = s.replace("ё", "е")
    s = s.replace("’", "'").replace("`", "'").replace("“", '"').replace("”", '"')
    s = s.replace("—", "-").replace("–", "-")

    s = re.sub(r"\[.*?feat.*?\]", "", s)
    s = re.sub(r"\(.*?feat.*?\)", "", s)
    s = re.sub(r"\[.*?ft\..*?\]", "", s)
    s = re.sub(r"\(.*?ft\..*?\)", "", s)

    s = re.sub(r"\(.*?prod.*?\)", "", s)
    s = re.sub(r"\[.*?prod.*?\]", "", s)

    s = re.sub(r"\(.*?radio edit.*?\)", "", s)
    s = re.sub(r"\[.*?radio edit.*?\]", "", s)

    s = re.sub(r"\(.*?remix.*?\)", "", s)
    s = re.sub(r"\[.*?remix.*?\]", "", s)

    s = re.sub(r"\(.*?version.*?\)", "", s)
    s = re.sub(r"\(.*?remaster.*?\)", "", s)
    s = re.sub(r"\[.*?remaster.*?\]", "", s)

    s = s.replace("&", " and ")
    s = re.sub(r"[^a-zа-я0-9\s'\-]", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def expand_artist_aliases(name: str) -> List[str]:
    base = normalize(name)
    variants = {base}
    for alias in ARTIST_ALIASES.get(base, []):
        variants.add(normalize(alias))
    return list(variants)


def cache_key(track: Dict) -> str:
    return f"{track['title']}|{track['artist_str']}".lower().strip()


def load_cache(cache_file: str) -> Dict:
    path = Path(cache_file)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}
        return {k: v for k, v in raw.items() if isinstance(v, dict)}
    except Exception:
        return {}


def save_cache(cache: Dict, cache_file: str) -> None:
    path = Path(cache_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def write_report(rows: List[Dict], report_file: str) -> None:
    fieldnames = [
        "spotify_title",
        "spotify_artists",
        "yt_title",
        "yt_artists",
        "videoId",
        "status",
        "score",
    ]

    report_path = Path(report_file)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# =========================
# SPOTIFY
# =========================
def get_all_spotify_tracks(sp, playlist_id: str) -> Tuple[str, List[Dict]]:
    me = sp.current_user()
    print("Spotify user:", me.get("id"))
    print("Country:", me.get("country"))

    meta = sp.playlist(playlist_id)
    playlist_name = meta.get("name", "Unknown playlist")
    print(f"Spotify playlist name: {playlist_name}")

    items = []
    offset = 0
    limit = 50
    page_num = 1

    while True:
        page = sp.playlist_items(
            playlist_id,
            offset=offset,
            limit=limit,
            market="from_token",
            additional_types=("track",)
        )

        raw_items = page.get("items", [])
        print(f"[Spotify] page={page_num} offset={offset} raw_items={len(raw_items)} next={bool(page.get('next'))}")

        for idx, row in enumerate(raw_items, start=1):
            track = row.get("track") or row.get("item")

            if track is None:
                print(f"  - item #{idx}: no track/item")
                continue

            if track.get("type") != "track":
                print(f"  - item #{idx}: skipped type={track.get('type')}")
                continue

            if track.get("is_local"):
                print(f"  - item #{idx}: local track skipped: {track.get('name')}")
                continue

            artists = [a.get("name") for a in track.get("artists", []) if a.get("name")]

            item = {
                "spotify_id": track.get("id"),
                "title": (track.get("name") or "").strip(),
                "artists": artists,
                "artist_str": ", ".join(artists),
                "album": ((track.get("album") or {}).get("name") or "").strip(),
                "duration_ms": track.get("duration_ms"),
                "isrc": (track.get("external_ids") or {}).get("isrc"),
            }

            print(f"  + parsed: {item['title']} — {item['artist_str']}")
            items.append(item)

        if not page.get("next"):
            break

        offset += limit
        page_num += 1

    print(f"Итогово распарсено треков: {len(items)}")
    return playlist_name, items


# =========================
# MATCHING
# =========================
def duration_score(a_ms: Optional[int], b_seconds: Optional[int]) -> float:
    if not a_ms or not b_seconds:
        return 0.0
    diff = abs(a_ms - b_seconds * 1000)
    if diff <= 2500:
        return 1.0
    if diff <= 5000:
        return 0.8
    if diff <= 9000:
        return 0.5
    if diff <= 15000:
        return 0.2
    return 0.0


def title_score(sp_title: str, yt_title: str) -> float:
    a = normalize(sp_title)
    b = normalize(yt_title)

    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.9

    a_words = set(a.split())
    b_words = set(b.split())
    inter = len(a_words & b_words)
    denom = max(1, len(a_words))
    ratio = inter / denom

    return min(0.8, ratio)


def artist_match_score(spotify_artists: List[str], yt_artists: List[Dict]) -> float:
    if not spotify_artists or not yt_artists:
        return 0.0

    sp_variants = []
    for a in spotify_artists:
        sp_variants.extend(expand_artist_aliases(a))

    yt_variants = []
    for a in yt_artists:
        name = a.get("name", "")
        yt_variants.extend(expand_artist_aliases(name))

    sp_set = set(sp_variants)
    yt_set = set(yt_variants)

    if sp_set & yt_set:
        return 1.0

    for a in sp_set:
        for b in yt_set:
            if a == b or a in b or b in a:
                return 0.85

    return 0.0


def overall_score(track: Dict, result: Dict) -> float:
    score = 0.0
    score += 0.55 * title_score(track["title"], result.get("title", ""))
    score += 0.30 * artist_match_score(track["artists"], result.get("artists", []))
    score += 0.15 * duration_score(track.get("duration_ms"), result.get("duration_seconds"))

    if result.get("_source_filter") == "videos":
        score -= 0.03
    elif result.get("_source_filter") == "default":
        score -= 0.01

    if track.get("isrc") and result.get("_query") == track.get("isrc"):
        score += 0.35

    return round(max(score, 0.0), 4)


def classify_match(score: float) -> str:
    if score >= 0.90:
        return "exact"
    if score >= 0.72:
        return "good"
    if score >= 0.55:
        return "review"
    return "bad"


def choose_best_match(results: List[Dict], track: Dict) -> Optional[Dict]:
    best = None
    best_score = -1.0

    for r in results:
        if "videoId" not in r:
            continue

        score = overall_score(track, r)
        r["_score"] = score
        r["_class"] = classify_match(score)

        if score > best_score:
            best_score = score
            best = r

    if best is None:
        return None

    threshold = 0.55
    if track.get("isrc") and best.get("_query") == track.get("isrc"):
        threshold = 0.40

    if best_score < threshold:
        return None

    return best


def build_search_queries(track: Dict) -> List[str]:
    title = track["title"]
    artists = track["artists"]
    artist_str = track["artist_str"]

    queries = []
    queries.append(f"{title} {artist_str}")

    if artists:
        first_artist = artists[0]
        queries.append(f"{title} {first_artist}")
        queries.append(f"{first_artist} {title}")

        for alias in expand_artist_aliases(first_artist):
            if alias != normalize(first_artist):
                queries.append(f"{title} {alias}")
                queries.append(f"{alias} {title}")

    if len(artists) > 1:
        queries.append(f"{title} {artists[0]} {artists[1]}")

    if track.get("isrc"):
        queries.append(track["isrc"])

    deduped = []
    seen = set()
    for q in queries:
        qn = q.strip().lower()
        if qn and qn not in seen:
            seen.add(qn)
            deduped.append(q)

    return deduped


def search_ytmusic_track(yt: YTMusic, track: Dict) -> Optional[Dict]:
    all_results = []
    seen = set()

    queries = build_search_queries(track)

    if is_debug_track(track):
        print(f"  DEBUG queries: {queries}")

    search_plans = [
        ("songs", SEARCH_LIMIT),
        ("videos", SEARCH_LIMIT),
        (None, SEARCH_LIMIT),
    ]

    for q in queries:
        for filter_name, limit in search_plans:
            try:
                results = yt.search(q, filter=filter_name, limit=limit)
            except Exception as e:
                results = []
                if is_debug_track(track):
                    print(f"  DEBUG search error: q={q!r}, filter={filter_name}, err={e}")

            if is_debug_track(track):
                print(f"  DEBUG q={q!r}, filter={filter_name}, results={len(results)}")

            for r in results:
                vid = r.get("videoId")
                if vid and vid not in seen:
                    seen.add(vid)
                    r["_source_filter"] = filter_name or "default"
                    r["_query"] = q
                    r["_dbg_score"] = overall_score(track, r)
                    all_results.append(r)

            time.sleep(REQUEST_SLEEP)

    if is_debug_track(track):
        ranked = sorted(
            all_results,
            key=lambda x: x.get("_dbg_score") if x.get("_dbg_score") is not None else -1.0,
            reverse=True
        )
        print("  DEBUG top candidates:")
        for r in ranked[:8]:
            artists = ", ".join(a.get("name", "") for a in r.get("artists", []))
            print(
                f"    title={r.get('title')} | artists={artists} | "
                f"filter={r.get('_source_filter')} | score={r.get('_dbg_score')} | "
                f"videoId={r.get('videoId')}"
            )

    return choose_best_match(all_results, track)


# =========================
# CLI / MAIN
# =========================
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transfer a Spotify playlist to YouTube Music with fuzzy track matching."
    )
    parser.add_argument(
        "playlist",
        help="Spotify playlist URL or playlist ID."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create the YouTube Music playlist. Without this flag the script only searches and writes a report."
    )
    parser.add_argument(
        "--ytmusic-auth",
        default=DEFAULT_YTMUSIC_AUTH,
        help=f"Path to ytmusicapi auth file (default: {DEFAULT_YTMUSIC_AUTH})."
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Name of the new YouTube Music playlist. Defaults to the Spotify playlist name."
    )
    parser.add_argument(
        "--description",
        default=DEFAULT_YTMUSIC_PLAYLIST_DESC,
        help="Description of the new YouTube Music playlist."
    )
    parser.add_argument(
        "--privacy",
        choices=("PRIVATE", "UNLISTED", "PUBLIC"),
        default="PRIVATE",
        help="YouTube Music playlist privacy (default: PRIVATE)."
    )
    parser.add_argument(
        "--cache",
        default=DEFAULT_CACHE_FILE,
        help=f"Match cache path (default: {DEFAULT_CACHE_FILE})."
    )
    parser.add_argument(
        "--report",
        default=DEFAULT_REPORT_FILE,
        help=f"CSV report path (default: {DEFAULT_REPORT_FILE})."
    )
    parser.add_argument(
        "--include-review",
        action="store_true",
        help="Also transfer matches classified as 'review'. By default only exact/good matches are transferred."
    )
    parser.add_argument(
        "--recheck-good",
        action="store_true",
        default=RECHECK_GOOD,
        help="Ignore cached 'good' matches and search them again."
    )
    parser.add_argument(
        "--no-recheck-review",
        action="store_false",
        dest="recheck_review",
        default=RECHECK_REVIEW,
        help="Reuse cached 'review' matches instead of searching them again."
    )
    return parser.parse_args()


def make_ytmusic_client(auth_path: str, require_auth: bool) -> YTMusic:
    path = Path(auth_path)
    if path.exists():
        return YTMusic(str(path))
    if require_auth:
        raise RuntimeError(
            f"YouTube Music auth file not found: {auth_path}. "
            "Create it with `ytmusicapi browser` before using --apply."
        )
    print(f"YTMusic auth file not found ({auth_path}); using unauthenticated search for dry run.")
    return YTMusic()


def add_items_in_batches(yt: YTMusic, playlist_id: str, video_ids: List[str]) -> None:
    for start in range(0, len(video_ids), BATCH_SIZE):
        batch = video_ids[start:start + BATCH_SIZE]
        # Preserve duplicate tracks if the source playlist contains them.
        yt.add_playlist_items(playlist_id, batch, duplicates=True)
        time.sleep(0.5)


def main() -> None:
    args = parse_args()

    sp = spotify_client()
    yt = make_ytmusic_client(args.ytmusic_auth, require_auth=args.apply)
    cache = load_cache(args.cache)

    playlist_id = extract_spotify_playlist_id(args.playlist)
    spotify_playlist_name, tracks = get_all_spotify_tracks(sp, playlist_id)

    print(f"Spotify playlist: {spotify_playlist_name}")
    print(f"Треков найдено: {len(tracks)}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}")

    transfer_video_ids: List[str] = []
    not_found = []
    review = []
    report_rows = []

    for i, track in enumerate(tracks, start=1):
        print(f"[{i}/{len(tracks)}] Ищу: {track['title']} — {track['artist_str']}")

        key = cache_key(track)
        match = None
        cached = cache.get(key)

        if isinstance(cached, dict):
            cached_class = cached.get("_class", "good")
            use_cached = True

            if args.recheck_review and cached_class == "review":
                use_cached = False
            if args.recheck_good and cached_class == "good":
                use_cached = False

            if use_cached:
                print(f"  ↺ из кэша: {cached.get('title', '')} [{cached_class}]")
                match = cached
            else:
                print(f"  ↻ переищу cached result: {cached.get('title', '')} [{cached_class}]")
        elif cached is not None:
            print(f"  ! пропускаю битый кэш для ключа: {key}")

        if not match:
            match = search_ytmusic_track(yt, track)
            if match:
                cache[key] = {
                    "videoId": match.get("videoId"),
                    "title": match.get("title"),
                    "artists": match.get("artists", []),
                    "duration_seconds": match.get("duration_seconds"),
                    "_score": match.get("_score"),
                    "_class": match.get("_class"),
                }
                save_cache(cache, args.cache)

        if not match:
            not_found.append(track)
            report_rows.append({
                "spotify_title": track["title"],
                "spotify_artists": track["artist_str"],
                "yt_title": "",
                "yt_artists": "",
                "videoId": "",
                "status": "not_found",
                "score": "",
            })
            print("  ✗ не найдено")
            continue

        match_score = match.get("_score")
        match_class = match.get("_class", "good")
        yt_title = match.get("title", "")
        yt_artists = ", ".join(a.get("name", "") for a in match.get("artists", []))

        print(f"  ✓ {yt_title} [{match_class}, score={match_score}]")

        if match_class == "review":
            review.append({
                "spotify": track,
                "yt": {
                    "title": yt_title,
                    "artists": [a.get("name") for a in match.get("artists", [])],
                    "videoId": match.get("videoId"),
                    "score": match_score,
                }
            })

        report_rows.append({
            "spotify_title": track["title"],
            "spotify_artists": track["artist_str"],
            "yt_title": yt_title,
            "yt_artists": yt_artists,
            "videoId": match.get("videoId", ""),
            "status": match_class,
            "score": match_score,
        })

        should_transfer = match_class in {"exact", "good"} or (
            args.include_review and match_class == "review"
        )
        if should_transfer and match.get("videoId"):
            transfer_video_ids.append(match["videoId"])

    write_report(report_rows, args.report)

    ytm_playlist_id = None
    if args.apply:
        playlist_name = args.name or spotify_playlist_name
        ytm_playlist_id = yt.create_playlist(
            title=playlist_name,
            description=args.description,
            privacy_status=args.privacy,
        )
        if not isinstance(ytm_playlist_id, str):
            raise RuntimeError(f"Could not create YouTube Music playlist: {ytm_playlist_id}")
        add_items_in_batches(yt, ytm_playlist_id, transfer_video_ids)

    print("\n=== ГОТОВО ===")
    print(f"Не найдено: {len(not_found)}")
    print(f"На ручную проверку: {len(review)}")
    print(f"Подготовлено к переносу: {len(transfer_video_ids)}")
    print(f"Отчёт: {args.report}")
    print(f"Кэш: {args.cache}")

    if ytm_playlist_id:
        print(f"Создан плейлист YT Music: {ytm_playlist_id}")
    else:
        print("Плейлист в YouTube Music не создавался (dry run). Для переноса добавьте --apply.")

    if review:
        print("\n--- Проверить вручную ---")
        for x in review:
            sp_t = x["spotify"]
            yt_t = x["yt"]
            print(
                f"SP: {sp_t['title']} — {sp_t['artist_str']}  |  "
                f"YT: {yt_t['title']} — {', '.join(yt_t['artists'])}  |  "
                f"score={yt_t['score']}"
            )

    if not_found:
        print("\n--- Не найдено ---")
        for t in not_found:
            print(f"{t['title']} — {t['artist_str']}")


if __name__ == "__main__":
    main()
