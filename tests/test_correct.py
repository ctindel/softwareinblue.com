from __future__ import annotations

from scripts.podcast_lib.correct import correct_transcript


def test_corrects_misheard_elastic_search() -> None:
    transcript = {
        "segments": [
            {
                "start": 0.0, "end": 1.0, "text": "We use elastic search.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"word": "We", "start": 0.0, "end": 0.1},
                    {"word": "use", "start": 0.1, "end": 0.3},
                    {"word": "elastic", "start": 0.3, "end": 0.6},
                    {"word": "search.", "start": 0.6, "end": 1.0},
                ],
            }
        ]
    }
    corrected, log = correct_transcript(transcript)
    seg = corrected["segments"][0]
    assert "Elasticsearch" in seg["text"]
    assert any("Elasticsearch" in entry["after"] for entry in log)


def test_corrects_misheard_clickhouse() -> None:
    transcript = {
        "segments": [
            {
                "start": 0.0, "end": 1.0, "text": "We picked Click House.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"word": "We", "start": 0.0, "end": 0.1},
                    {"word": "picked", "start": 0.1, "end": 0.4},
                    {"word": "Click", "start": 0.4, "end": 0.6},
                    {"word": "House.", "start": 0.6, "end": 1.0},
                ],
            }
        ]
    }
    corrected, log = correct_transcript(transcript)
    assert "ClickHouse" in corrected["segments"][0]["text"]


def test_no_change_when_already_correct() -> None:
    transcript = {
        "segments": [
            {
                "start": 0.0, "end": 1.0, "text": "ClickHouse is fast.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"word": "ClickHouse", "start": 0.0, "end": 0.5},
                    {"word": "is", "start": 0.5, "end": 0.7},
                    {"word": "fast.", "start": 0.7, "end": 1.0},
                ],
            }
        ]
    }
    corrected, log = correct_transcript(transcript)
    assert corrected["segments"][0]["text"] == "ClickHouse is fast."
    assert log == []


def test_does_not_corrupt_unrelated_words() -> None:
    transcript = {
        "segments": [
            {
                "start": 0.0, "end": 1.0, "text": "The quick brown fox.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"word": "The", "start": 0.0, "end": 0.1},
                    {"word": "quick", "start": 0.1, "end": 0.3},
                    {"word": "brown", "start": 0.3, "end": 0.6},
                    {"word": "fox.", "start": 0.6, "end": 1.0},
                ],
            }
        ]
    }
    corrected, log = correct_transcript(transcript)
    assert corrected["segments"][0]["text"] == "The quick brown fox."
    assert log == []
