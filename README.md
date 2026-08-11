# spotTrans

A small Python utility for transferring a Spotify playlist to YouTube Music.

The script reads tracks from Spotify, searches YouTube Music for matching songs,
scores candidates by title, artist and duration, caches the matches, writes a CSV
report and can optionally create a new YouTube Music playlist.

> This is a personal/experimental project. `ytmusicapi` is an unofficial YouTube
> Music API and is not supported by Google.

## Features

- reads all tracks from a Spotify playlist;
- searches YouTube Music using several query variants;
- handles Cyrillic/Latin artist aliases used by the matching logic;
- scores candidates by title, artist and duration;
- classifies results as `exact`, `good`, `review` or `bad`;
- caches successful matches to reduce repeated requests;
- writes a CSV transfer report;
- safe dry-run mode by default;
- optional playlist creation with `--apply`;
- preserves duplicate tracks when writing the target playlist.

## Requirements

- Python 3.10+
- a Spotify Developer application;
- Spotify credentials in `.env`;
- YouTube Music authentication only when creating the target playlist.

## Installation

```bash
python -m venv .venv
```

Activate the virtual environment.

Windows / Git Bash:

```bash
source .venv/Scripts/activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Spotify setup

1. Create an application in the Spotify Developer Dashboard.
2. Add this redirect URI to the app settings:

```text
http://127.0.0.1:8888/callback
```

3. Copy the environment template:

```bash
cp .env.example .env
```

4. Fill in your own `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET`.

Do not commit `.env` or `.spotify_cache`.

### Spotify API limitation

For Spotify apps running in current Development Mode, playlist-item access is
restricted to playlists owned by the current user or playlists where the user is
a collaborator. The project therefore targets personal playlist migration rather
than arbitrary public playlists.

## YouTube Music setup

A dry run can search YouTube Music without authentication. Authentication is
required for `--apply`, because creating and modifying a playlist is an
authenticated operation.

The project currently uses ytmusicapi browser authentication. Create the local
file with:

```bash
ytmusicapi browser
```

Follow the prompts to create `browser.json` in the project directory.

`browser.json` contains session credentials. It is ignored by Git and must never
be committed or shared.

## Usage

Run a dry run first:

```bash
python main.py "https://open.spotify.com/playlist/PLAYLIST_ID"
```

This searches for matches and creates:

- `matches_cache.json` — local match cache;
- `transfer_report.csv` — matching report.

Both files are ignored by Git because they contain generated/personal playlist data.

Review the CSV, especially rows with status `review`.

When the results look good, create the YouTube Music playlist:

```bash
python main.py "https://open.spotify.com/playlist/PLAYLIST_ID" --apply
```

By default only `exact` and `good` matches are transferred. To also include
`review` matches:

```bash
python main.py "https://open.spotify.com/playlist/PLAYLIST_ID" --apply --include-review
```

Choose a name and privacy level:

```bash
python main.py "PLAYLIST_ID" \
  --apply \
  --name "Imported from Spotify" \
  --privacy PRIVATE
```

Useful options:

```text
--apply                  actually create the YouTube Music playlist
--include-review         also transfer matches that need manual review
--recheck-good           search cached good matches again
--no-recheck-review      reuse cached review matches
--cache PATH             custom cache file
--report PATH            custom CSV report
--ytmusic-auth PATH      custom ytmusicapi auth file
--privacy LEVEL          PRIVATE, UNLISTED or PUBLIC
```

Full CLI help:

```bash
python main.py --help
```

## Matching approach

Each YouTube Music candidate receives a score based on:

- title similarity — 55%;
- artist match — 30%;
- duration similarity — 15%;
- an additional bonus when a search made with Spotify ISRC finds a candidate.

The thresholds are currently heuristic and are one of the main areas for future
improvement.

## Tests

The matching helpers have small offline unit tests:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

GitHub Actions runs the same checks on pushes and pull requests.

## Project status

The core transfer workflow is implemented and the repository is ready for iterative
development. The most useful next steps are:

1. add an interactive/manual override flow for `review` matches;
2. distinguish API/network failures from genuine `not_found` results;
3. make interrupted playlist creation resumable instead of creating a new playlist;
4. split Spotify, YouTube Music and matching logic into separate modules;
5. expand matching tests with difficult real-world cases such as remixes, covers,
   reordered artists and alternate transliterations.

## Security

Never commit any of the following files:

```text
.env
.spotify_cache
browser.json
oauth.json
matches_cache*.json
transfer_report*.csv
```

If any credential file has ever been committed to a public repository, revoke or
rotate the affected credentials rather than merely deleting the file in a later
commit.
