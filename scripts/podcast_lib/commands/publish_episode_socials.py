"""`podcast publish-episode-socials EPISODE` — episode-launch
announcement post fanned out to LinkedIn / X / Instagram / TikTok /
Facebook.

Sibling to `publish-spotify` (which uploads the audio/video to the
hosting platform) and `publish-youtube` (which uploads the long-form
video). This command does the *announcement* — short text post linking
to the YT and Spotify URLs, with the SIB cover image attached. No
video is uploaded; existing posting templates carry the YT/Spotify
links inline.

Prereq: `episode.links.youtube_full` and `episode.links.spotify` must
already be filled in `SIB_E<NN>_metadata.yaml` (the renderer prints
`<TBD: …>` if not, and the post will go out with placeholders — refuse
to post when key links are missing unless `--allow-tbd` is set).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

from scripts.podcast_lib.postiz import (
    PostizClient,
    facebook_post,
    instagram_post,
    linkedin_post,
    tiktok_post,
    x_post,
)
from scripts.podcast_lib.posting import (
    load_metadata,
    render_full_episode_post,
)
from scripts.podcast_lib._publish_helpers import (
    SOCIAL_PLATFORMS,
    episode_cover_default,
)


def _required_links_present(meta: dict) -> tuple[bool, list[str]]:
    """The episode-launch post is meaningless without the YouTube and
    Spotify URLs — those drive listeners to the actual content. Return
    (ok, missing_keys)."""
    links = meta["episode"].get("links") or {}
    missing = [k for k in ("youtube_full", "spotify") if not links.get(k)]
    return not missing, missing


def run(
    episode: int = typer.Argument(..., help="Episode number, e.g. 45"),
    cover: Path = typer.Option(None, help="Override cover image path."),
    publish_at: str = typer.Option(
        None, "--publish-at",
        help="Schedule (ISO datetime). Omit to post immediately.",
    ),
    skip: list[str] = typer.Option(
        [], "--skip",
        help="Platform identifier(s) to skip (e.g. --skip tiktok).",
    ),
    allow_tbd: bool = typer.Option(
        False, "--allow-tbd",
        help="Post even if the YT/Spotify URLs aren't filled in. "
             "Templates render placeholders as `<TBD: key>`.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Build payload, verify integrations, skip uploads + POST.",
    ),
) -> None:
    console = Console()
    meta = load_metadata(episode)

    ok, missing = _required_links_present(meta)
    if not ok and not allow_tbd:
        console.print(
            f"[red]missing required links in metadata: {missing}.[/red] "
            "Fill in `episode.links.youtube_full` and `episode.links.spotify` "
            "in the metadata YAML, or pass --allow-tbd to post anyway."
        )
        raise typer.Exit(2)

    cover_path = cover or episode_cover_default(episode)
    if not cover_path.exists():
        console.print(f"[red]cover image not found: {cover_path}[/red]")
        raise typer.Exit(2)

    client = PostizClient.from_env()
    available = {i["identifier"]: i for i in client.list_integrations()}
    targets = [p for p in SOCIAL_PLATFORMS if p not in skip]
    not_connected = [p for p in targets if p not in available]
    if not_connected:
        console.print(
            f"[yellow]not connected in Postiz: {not_connected} — connect "
            "them in the UI or use --skip to suppress.[/yellow]"
        )

    long_body = render_full_episode_post(meta, short=False)
    tweet_body = render_full_episode_post(meta, short=True)
    when = datetime.fromisoformat(publish_at) if publish_at else None

    if dry_run:
        console.print(f"[dim]--dry-run: episode {episode}[/dim]")
        console.print(f"  cover image:  {cover_path}")
        console.print(f"  scheduled at: {when or 'now'}")
        console.print(f"  fan out to:   {[p for p in targets if p in available]}")
        console.print("  --- long body ---")
        console.print(long_body)
        console.print("  --- twitter body ---")
        console.print(tweet_body)
        raise typer.Exit(0)

    console.print(f"Uploading cover image ({cover_path.stat().st_size:,} bytes)…")
    media = client.upload(cover_path)

    integrations = []
    for ident in targets:
        if ident not in available:
            continue
        ig = available[ident]
        if ident == "linkedin":
            integrations.append(linkedin_post(ig["id"], long_body, media=[media]))
        elif ident == "linkedin-page":
            integrations.append(linkedin_post(ig["id"], long_body, media=[media], page=True))
        elif ident == "x":
            integrations.append(x_post(ig["id"], tweet_body, media=[media]))
        elif ident == "instagram":
            # Episode announcement uses the cover image as a static post,
            # not a Reel — no vertical video here.
            integrations.append(instagram_post(ig["id"], long_body, media=[media], reel=False))
        elif ident == "tiktok":
            # TikTok requires video for video posts; image-only posts route
            # through the photo-mode endpoint. Postiz handles the variant
            # internally based on the media type. We skip with a warning if
            # the cover is image-only and TikTok isn't accepting it — the
            # producer can re-run with --skip tiktok and post a dedicated
            # video later.
            console.print(
                "[yellow]TikTok requires a video to post; episode "
                "announcement uses an image. Skipping TikTok — re-run with "
                "--skip tiktok to suppress this warning, or use "
                "publish-clip-socials with a teaser clip instead.[/yellow]"
            )
            continue
        elif ident == "facebook":
            integrations.append(facebook_post(ig["id"], long_body, media=[media]))

    if not integrations:
        console.print(
            "[yellow]no connected target platforms — nothing to post.[/yellow]"
        )
        raise typer.Exit(0)

    console.print(f"Submitting {len(integrations)} per-platform posts to Postiz…")
    resp = client.create_post(integrations=integrations, when=when)
    console.print(f"[green]ok[/green]: {resp}")
