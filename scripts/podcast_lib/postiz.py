"""Postiz public-API client for the SIB publishing pipeline.

Postiz documentation: https://docs.postiz.com/public-api
Endpoint base: `${POSTIZ_BASE_URL}/api/public/v1/`

Auth header: `Authorization: <token>` — the token is sent **bare**, not
`Bearer <token>`. Sending `Bearer` returns 401.

Tailnet prereq: the SIB Postiz instance lives on the EvoGyms Tailscale
tailnet. The base URL is reachable only when Tailscale is connected. The
client surfaces a clear error when the host is unreachable so callers
know to fix the network rather than retrying blindly.

Provider settings: each platform has its own `settings.__type` schema.
This module exposes one helper per platform that fills the platform-
specific defaults for SIB. Callers pass post text + media; the helper
emits the per-platform `settings` block.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


# ---------------------------------------------------------------------------
# Config + low-level client
# ---------------------------------------------------------------------------

class PostizError(RuntimeError):
    """Anything Postiz-related that wasn't a 2xx — surfaces the body so the
    caller can see what the server complained about."""


@dataclass
class PostizClient:
    base_url: str
    token: str
    timeout: float = 60.0

    @classmethod
    def from_env(cls) -> "PostizClient":
        base = os.environ.get("POSTIZ_BASE_URL", "").rstrip("/")
        token = os.environ.get("POSTIZ_TOKEN", "")
        if not base or not token:
            raise PostizError(
                "POSTIZ_BASE_URL and POSTIZ_TOKEN must be set "
                "(see scripts/podcast_lib/.env.example)."
            )
        return cls(base_url=base, token=token)

    def _req(self, method: str, path: str, **kw) -> httpx.Response:
        url = f"{self.base_url}/api/public/v1{path}"
        headers = kw.pop("headers", {}) or {}
        headers.setdefault("Authorization", self.token)
        try:
            with httpx.Client(timeout=self.timeout) as c:
                resp = c.request(method, url, headers=headers, **kw)
        except httpx.ConnectError as e:
            raise PostizError(
                f"Cannot reach Postiz at {self.base_url} — is Tailscale "
                f"connected? ({e})"
            ) from e
        if resp.status_code >= 400:
            raise PostizError(
                f"Postiz {method} {path} -> {resp.status_code}: {resp.text[:500]}"
            )
        return resp

    # ---- integrations --------------------------------------------------
    def list_integrations(self) -> list[dict]:
        """Return the connected social accounts (LinkedIn, YT, etc.)."""
        return self._req("GET", "/integrations").json()

    def integration_by(self, *, identifier: str, profile: str | None = None) -> dict:
        """Find a single connected integration by identifier (e.g. 'linkedin-page')
        and optionally profile (e.g. 'softwareinblue'). Errors clearly if
        no match — the caller almost always wants exactly one."""
        matches = [
            i for i in self.list_integrations()
            if i["identifier"] == identifier
            and (profile is None or i.get("profile") == profile)
        ]
        if not matches:
            raise PostizError(
                f"No connected integration matching identifier={identifier!r} "
                f"profile={profile!r}. Connect it in the Postiz UI first."
            )
        if len(matches) > 1:
            raise PostizError(
                f"Multiple integrations match identifier={identifier!r} "
                f"profile={profile!r}: {[m['id'] for m in matches]}. "
                "Disambiguate by passing profile=."
            )
        return matches[0]

    # ---- media uploads -------------------------------------------------
    def upload(self, path: str | Path) -> dict:
        """POST /upload — multipart upload returns {id, path} for use
        in a subsequent post body. `path` may be image or video."""
        p = Path(path)
        if not p.exists():
            raise PostizError(f"Upload source not found: {p}")
        with p.open("rb") as f:
            files = {"file": (p.name, f, _guess_mime(p))}
            return self._req("POST", "/upload", files=files).json()

    # ---- posts ---------------------------------------------------------
    def create_post(
        self,
        *,
        integrations: list[dict[str, Any]],
        when: datetime | None = None,
        short_link: bool = False,
        tags: list[str] | None = None,
    ) -> dict:
        """POST /posts. `integrations` is a list of per-platform post specs,
        each shaped as Postiz expects:

            {
              "integration": {"id": "<integration_id>"},
              "value": [{"content": "...", "image": [{"id": ..., "path": ...}]}],
              "settings": {"__type": "<provider>"}
            }

        `when=None` → post now; otherwise schedule to that datetime (UTC if
        naive). Returns the API response body."""
        if not integrations:
            raise PostizError("create_post requires at least one integration.")
        if when is None:
            payload_type = "now"
            iso_date = datetime.now(timezone.utc).isoformat()
        else:
            payload_type = "schedule"
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            iso_date = when.astimezone(timezone.utc).isoformat()
        body = {
            "type": payload_type,
            "date": iso_date,
            "shortLink": short_link,
            "tags": tags or [],
            "posts": integrations,
        }
        return self._req(
            "POST", "/posts",
            json=body,
            headers={"Content-Type": "application/json"},
        ).json()

    def delete_post(self, post_id: str) -> dict:
        return self._req("DELETE", f"/posts/{post_id}").json()


def _guess_mime(p: Path) -> str:
    s = p.suffix.lower()
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp",
        ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
    }.get(s, "application/octet-stream")


# ---------------------------------------------------------------------------
# Per-provider helpers — produce the integration block for create_post()
# ---------------------------------------------------------------------------
#
# Each helper returns the dict-shaped element for the `posts:` array in
# create_post(). Callers stack them up to fan out the same content to
# many platforms in one API call.

def _value_block(content: str, media: list[dict] | None) -> list[dict]:
    block: dict = {"content": content}
    if media:
        block["image"] = media
    return [block]


def linkedin_post(integration_id: str, content: str,
                  media: list[dict] | None = None,
                  *, page: bool = False) -> dict:
    """LinkedIn personal profile (default) or company page (`page=True`)."""
    return {
        "integration": {"id": integration_id},
        "value": _value_block(content, media),
        "settings": {"__type": "linkedin-page" if page else "linkedin"},
    }


def x_post(integration_id: str, content: str,
           media: list[dict] | None = None) -> dict:
    return {
        "integration": {"id": integration_id},
        "value": _value_block(content, media),
        "settings": {"__type": "x", "who_can_reply_post": "everyone"},
    }


def youtube_post(
    integration_id: str,
    description: str,
    *,
    video: dict,
    title: str,
    tags: list[str] | None = None,
    thumbnail: dict | None = None,
    made_for_kids: bool = False,
    visibility: str = "public",
) -> dict:
    """YouTube long-form (and Shorts — same endpoint; the YT side decides
    based on aspect ratio and duration). `video` and `thumbnail` are
    upload() responses."""
    settings: dict[str, Any] = {
        "__type": "youtube",
        "title": title,
        "type": visibility,           # "public" | "private" | "unlisted"
        "selfDeclaredMadeForKids": made_for_kids,
        "tags": tags or [],
    }
    if thumbnail:
        settings["thumbnail"] = thumbnail
    return {
        "integration": {"id": integration_id},
        "value": [{"content": description, "image": [video]}],
        "settings": settings,
    }


def instagram_post(integration_id: str, content: str,
                   media: list[dict],
                   *, reel: bool = False) -> dict:
    return {
        "integration": {"id": integration_id},
        "value": _value_block(content, media),
        "settings": {
            "__type": "instagram",
            "post_type": "reels" if reel else "post",
            "collaborators": [],
        },
    }


def tiktok_post(integration_id: str, content: str,
                video: dict,
                *,
                privacy_level: str = "PUBLIC_TO_EVERYONE",
                allow_duet: bool = True,
                allow_stitch: bool = True,
                allow_comment: bool = True,
                auto_add_music: bool = False) -> dict:
    return {
        "integration": {"id": integration_id},
        "value": [{"content": content, "image": [video]}],
        "settings": {
            "__type": "tiktok",
            "privacy_level": privacy_level,
            "duet": allow_duet,
            "stitch": allow_stitch,
            "comment": allow_comment,
            "autoAddMusic": auto_add_music,
        },
    }


def facebook_post(integration_id: str, content: str,
                  media: list[dict] | None = None) -> dict:
    return {
        "integration": {"id": integration_id},
        "value": _value_block(content, media),
        "settings": {"__type": "facebook"},
    }


# ---------------------------------------------------------------------------
# CLI smoke test — `python3 -m scripts.podcast_lib.postiz integrations`
# ---------------------------------------------------------------------------

def _main(argv: list[str]) -> int:
    import json
    import sys
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(
            "Usage:\n"
            "  python3 -m scripts.podcast_lib.postiz integrations\n"
            "      List connected integrations.\n"
            "  python3 -m scripts.podcast_lib.postiz upload PATH\n"
            "      Upload a media file; print {id, path}.\n",
            file=sys.stderr,
        )
        return 2
    client = PostizClient.from_env()
    cmd = argv[1]
    if cmd == "integrations":
        print(json.dumps(client.list_integrations(), indent=2))
        return 0
    if cmd == "upload":
        if len(argv) < 3:
            print("upload: PATH required", file=sys.stderr)
            return 2
        print(json.dumps(client.upload(argv[2]), indent=2))
        return 0
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv))
