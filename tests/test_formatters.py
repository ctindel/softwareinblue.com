from __future__ import annotations

from scripts.podcast_lib.formatters.md import render_md
from scripts.podcast_lib.formatters.srt import render_srt
from scripts.podcast_lib.formatters.txt import render_txt
from scripts.podcast_lib.formatters.vtt import render_vtt


def test_srt_header_and_indices(sample_transcript: dict) -> None:
    out = render_srt(sample_transcript)
    assert out.splitlines()[0] == "1"


def test_srt_no_mid_word_breaks(sample_transcript: dict) -> None:
    out = render_srt(sample_transcript)
    for block in out.strip().split("\n\n"):
        text_line = block.splitlines()[2]
        assert not text_line.endswith("-")


def test_srt_cues_under_three_seconds(sample_transcript: dict) -> None:
    out = render_srt(sample_transcript)
    for block in out.strip().split("\n\n"):
        time_line = block.splitlines()[1]
        start, end = time_line.split(" --> ")
        s_h, s_m, s_s = start.replace(",", ".").split(":")
        e_h, e_m, e_s = end.replace(",", ".").split(":")
        s_total = int(s_h) * 3600 + int(s_m) * 60 + float(s_s)
        e_total = int(e_h) * 3600 + int(e_m) * 60 + float(e_s)
        assert e_total - s_total <= 3.05


def test_vtt_starts_with_header(sample_transcript: dict) -> None:
    out = render_vtt(sample_transcript)
    assert out.splitlines()[0] == "WEBVTT"


def test_txt_has_no_timestamps(sample_transcript: dict) -> None:
    out = render_txt(sample_transcript)
    assert "-->" not in out
    assert "Welcome" in out
    assert "Elasticsearch" in out


def test_md_groups_consecutive_speakers(sample_transcript: dict) -> None:
    out = render_md(sample_transcript, speakers={})
    paragraphs = [p for p in out.split("\n\n") if p.strip()]
    assert len(paragraphs) == 2
    assert paragraphs[0].startswith("**SPEAKER_00:**")
    assert paragraphs[1].startswith("**SPEAKER_01:**")


def test_md_uses_human_names_when_provided(sample_transcript: dict) -> None:
    out = render_md(sample_transcript, speakers={"SPEAKER_00": "Chad", "SPEAKER_01": "Steve"})
    assert "**Chad:**" in out
    assert "**Steve:**" in out
    assert "SPEAKER_00" not in out
