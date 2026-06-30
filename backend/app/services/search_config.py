"""Vietnamese -> English search mapping for the exercise pool.

This module centralises the bilingual search-expansion logic used by
``PoolService.search``. Vietnamese keywords (with or without tones) are
expanded into equivalent English terms so users can search the 1,324-item
English catalogue using their native language.

Kept dependency-free (only ``re``) so it can be unit-tested without a
database.
"""

import re
from typing import List

# ---------------------------------------------------------------------------
# Tone stripping
# ---------------------------------------------------------------------------
_ACCENT_MAP = [
    (r"[àáạảãâầấậẩẫăằắặẳẵ]", "a"),
    (r"[èéẹẻẽêềếệểễ]", "e"),
    (r"[ìíịỉĩ]", "i"),
    (r"[òóọỏõôồốộổỗơờớợởỡ]", "o"),
    (r"[ùúụủũưừứựửữ]", "u"),
    (r"[ỳýỵỷỹ]", "y"),
    (r"[đ]", "d"),
    (r"[ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴ]", "A"),
    (r"[ÈÉẸẺẼÊỀẾỆỂỄ]", "E"),
    (r"[ÌÍỊỈĨ]", "I"),
    (r"[ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ]", "O"),
    (r"[ÙÚỤỦŨƯỪỨỰỬỮ]", "U"),
    (r"[ỲÝỴỶỸ]", "Y"),
    (r"[Đ]", "D"),
]


def remove_vietnamese_tones(s: str) -> str:
    """Strip Vietnamese diacritics/tones from ``s``.

    Returns an empty string for ``None``/empty input so callers can use the
    result safely in SQL ``ILIKE`` patterns.
    """
    if not s:
        return ""
    for pattern, replacement in _ACCENT_MAP:
        s = re.sub(pattern, replacement, s)
    return s


# ---------------------------------------------------------------------------
# Vietnamese -> English keyword expansion
# ---------------------------------------------------------------------------
# Keys are lowercase, tone-stripped Vietnamese phrases. Values are English
# synonyms that should also be matched against the (English) pool catalogue.
VIETNAMESE_SEARCH_MAPPING = {
    "day nguc": [
        "bench press",
        "chest press",
        "chest fly",
        "pushdown",
        "push-up",
        "dip",
    ],
    "day nguc ngang": ["bench press"],
    "day nguc tren": ["incline press"],
    "day nguc duoi": ["decline press"],
    "day vai": [
        "overhead press",
        "shoulder press",
        "military press",
        "lateral raise",
        "front raise",
    ],
    "tay sau": ["tricep"],
    "tay truoc": ["bicep", "curl"],
    "cuon tay truoc": ["bicep curl"],
    "keo cap": ["cable pull", "cable row", "cable pushdown", "lat pulldown"],
    "keo xa": ["pull up", "pull-up", "chin up", "lat pulldown"],
    "xa don": ["pull-up", "chin-up"],
    "xa kep": ["dip"],
    "chong day": ["push-up", "pushup"],
    "hit dat": ["push-up", "pushup"],
    "ganh ta": ["squat"],
    "ganh ta don": ["barbell squat"],
    "dap dui": ["leg press"],
    "da dui": ["leg extension"],
    "moc dui": ["leg curl"],
    "dui sau": ["hamstring", "deadlift", "leg curl"],
    "dui truoc": ["quadricep", "leg extension", "squat"],
    "bap chuoi": ["calf", "calf raise"],
    "nhon got": ["calf raise"],
    "gap bung": ["crunch", "sit-up", "leg raise", "plank"],
    "bung": ["abs", "abdominal", "crunch", "plank"],
    "chay bo": ["treadmill", "run"],
    "dap xe": ["bike", "cycle", "bicycle"],
    "cheo thuyen": ["row", "rowing"],
    "lung": ["back", "row", "lat pulldown", "deadlift"],
    "xo": ["lat", "pulldown", "pull-up", "row"],
    "vai": ["shoulder", "delt", "press", "lateral raise"],
    "nguc": ["chest", "press", "fly", "bench press"],
    "mong": ["glute", "hip thrust"],
}


def expand_vietnamese_terms(cleaned_query: str) -> List[str]:
    """Return de-duplicated English expansion terms for a tone-stripped query.

    Any mapping key that is a substring of ``cleaned_query`` contributes its
    English synonyms. Insertion order is preserved; duplicates removed.
    """
    expanded: List[str] = []
    seen: set[str] = set()
    for vi_key, en_terms in VIETNAMESE_SEARCH_MAPPING.items():
        if vi_key in cleaned_query:
            for term in en_terms:
                if term not in seen:
                    seen.add(term)
                    expanded.append(term)
    return expanded
