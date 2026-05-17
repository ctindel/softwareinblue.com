"""OAuth flow for Google APIs (YouTube + Sheets).

Uses the same OAuth client credentials as the gws CLI for ctindel@gmail.com.
Stores the token at ~/.config/gws-gmail-ctindel/youtube_token.json.

Usage:
    python3 scripts/podcast_lib/youtube_auth.py          # authorize
    python3 scripts/podcast_lib/youtube_auth.py --test    # test: list channels
    python3 scripts/podcast_lib/youtube_auth.py --reauth  # force re-authorization
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CONFIG_DIR = Path.home() / ".config" / "gws-gmail-ctindel"
CLIENT_SECRET = CONFIG_DIR / "client_secret.json"
TOKEN_FILE = CONFIG_DIR / "youtube_token.json"

SCOPES = [
    # YouTube
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    # Drive & Docs
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/presentations",
    # Gmail & Calendar
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/calendar",
    # Tasks & People
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/contacts",
]


def get_credentials() -> Credentials:
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[yt-auth] refreshing expired token")
            creds.refresh(Request())
        else:
            print("[yt-auth] starting OAuth flow")
            print("[yt-auth] listening on localhost:8085")
            print("[yt-auth] if remote, set up tunnel: ssh -L 8085:localhost:8085 elastic")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET), SCOPES,
            )
            creds = flow.run_local_server(port=8085, open_browser=False)
        TOKEN_FILE.write_text(creds.to_json())
        print(f"[yt-auth] token saved to {TOKEN_FILE}")
    return creds


def test_connection(creds: Credentials) -> None:
    yt = build("youtube", "v3", credentials=creds)
    resp = yt.channels().list(part="snippet,contentDetails,statistics", mine=True).execute()
    for ch in resp.get("items", []):
        print(f"  Channel: {ch['snippet']['title']}")
        print(f"  ID:      {ch['id']}")
        print(f"  Subs:    {ch['statistics'].get('subscriberCount', '?')}")
        print(f"  Videos:  {ch['statistics'].get('videoCount', '?')}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true", help="Test by listing channels")
    p.add_argument("--reauth", action="store_true", help="Force re-authorization (new scopes)")
    args = p.parse_args()

    if args.reauth and TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print("[yt-auth] cleared old token — will re-authorize")

    creds = get_credentials()
    print("[yt-auth] authenticated successfully")

    if args.test:
        print("[yt-auth] testing YouTube API connection:")
        test_connection(creds)
