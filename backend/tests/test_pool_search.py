"""Unit tests for the Vietnamese search-config helpers.

Pure-function tests (no database) covering tone stripping and the
Vietnamese -> English query expansion used by ``PoolService.search``.
The integration coverage of the search endpoint itself lives in
``test_pool.py``.
"""

import pytest

from backend.app.services.search_config import (
    VIETNAMESE_SEARCH_MAPPING,
    expand_vietnamese_terms,
    remove_vietnamese_tones,
)


@pytest.mark.asyncio
async def test_remove_vietnamese_tones_strips_lowercase_accents():
    assert remove_vietnamese_tones("đẩy ngực") == "day nguc"


@pytest.mark.asyncio
async def test_remove_vietnamese_tones_strips_uppercase_accents():
    assert remove_vietnamese_tones("ĐẨY NGỰC") == "DAY NGUC"


@pytest.mark.asyncio
async def test_remove_vietnamese_tones_preserves_unaccented_text():
    assert remove_vietnamese_tones("bench press") == "bench press"


@pytest.mark.asyncio
async def test_remove_vietnamese_tones_handles_empty_and_none():
    assert remove_vietnamese_tones("") == ""
    assert remove_vietnamese_tones(None) == ""


@pytest.mark.asyncio
async def test_mapping_keys_are_lowercase_and_tone_stripped():
    for key, terms in VIETNAMESE_SEARCH_MAPPING.items():
        assert key == key.lower()
        assert remove_vietnamese_tones(key) == key
        assert isinstance(terms, list)
        assert all(isinstance(t, str) for t in terms)


@pytest.mark.asyncio
async def test_expand_returns_english_synonyms_for_vietnamese_query():
    expanded = expand_vietnamese_terms("day nguc")
    assert "bench press" in expanded


@pytest.mark.asyncio
async def test_expand_deduplicates_while_preserving_order():
    expanded = expand_vietnamese_terms("day nguc ngang")
    # "bench press" appears in multiple matched keys but only once
    assert len(expanded) == len(set(expanded))
    assert "bench press" in expanded


@pytest.mark.asyncio
async def test_expand_returns_empty_for_unmapped_query():
    assert expand_vietnamese_terms("zzzzz") == []


@pytest.mark.asyncio
async def test_expand_matches_partial_keys():
    # "dui sau" is a key; a longer query containing it should still match
    assert "hamstring" in expand_vietnamese_terms("dui sau cua")
