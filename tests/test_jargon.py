from __future__ import annotations

from scripts.podcast_lib.jargon import (
    CATEGORIES,
    all_terms,
    build_initial_prompt,
)


def test_categories_nonempty() -> None:
    assert len(CATEGORIES) >= 20
    for name, terms in CATEGORIES.items():
        assert isinstance(name, str)
        assert len(terms) > 0


def test_all_terms_includes_show_critical() -> None:
    terms = set(all_terms())
    for must in ["Elasticsearch", "Weaviate", "ClickHouse", "kNN", "RAG", "HNSW",
                 "Steve Mayzak", "Software in Blue", "Chad"]:
        assert must in terms, f"Missing: {must}"


def test_all_terms_dedupes() -> None:
    terms = all_terms()
    assert len(terms) == len(set(terms))


def test_build_initial_prompt_under_token_cap() -> None:
    prompt = build_initial_prompt(token_budget=200)
    assert len(prompt) < 200 * 5
    assert prompt.startswith("Glossary:")


def test_build_initial_prompt_deterministic() -> None:
    a = build_initial_prompt(token_budget=200)
    b = build_initial_prompt(token_budget=200)
    assert a == b


def test_build_initial_prompt_prioritizes_companies_and_products() -> None:
    prompt = build_initial_prompt(token_budget=200)
    assert "Elasticsearch" in prompt
    assert "Weaviate" in prompt
    assert "ClickHouse" in prompt
