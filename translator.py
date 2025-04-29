# add_strokes_and_tones.py
# -------------------------------------------------
# Add stroke counts (“strokes”) and tone numbers (“tones”)
# to every idiom in idioms.json, using char_strokes.json.
# -------------------------------------------------
# Usage:  python add_strokes_and_tones.py
# Result: idioms_with_strokes_tones.json
# -------------------------------------------------

import json
import re

IDIOMS_FILE  = "res/idiom_new.json"
STROKES_FILE = "res/strokes.json"
OUT_FILE     = "res/idioms_new.json"

# ---------- load source files ----------
with open(IDIOMS_FILE,  encoding="utf-8") as f:
    idioms = json.load(f)            # list[dict]

with open(STROKES_FILE, encoding="utf-8") as f:
    stroke_map = json.load(f)        # dict[str, int]

# ---------- pinyin‑tone helpers ----------
# diacritic → tone number
DIACRITIC_TONE = {
    "ā": 1, "ē": 1, "ī": 1, "ō": 1, "ū": 1, "ǖ": 1,
    "á": 2, "é": 2, "í": 2, "ó": 2, "ú": 2, "ǘ": 2,
    "ǎ": 3, "ě": 3, "ǐ": 3, "ǒ": 3, "ǔ": 3, "ǚ": 3,
    "à": 4, "è": 4, "ì": 4, "ò": 4, "ù": 4, "ǜ": 4,
}

def tone_of_syllable(syl: str) -> int:
    """Return 1‑5 tone for one pinyin syllable (diacritic or digit form)."""
    m = re.search(r"([1-5])$", syl)      # e.g. ma3
    if m:
        return int(m.group(1))
    for ch in syl:
        if ch in DIACRITIC_TONE:
            return DIACRITIC_TONE[ch]
    return 5                              # neutral tone

def tones_for(pinyin: str) -> list[int]:
    """Return tone list for a pinyin string split by space."""
    return [tone_of_syllable(syl) for syl in pinyin.split() if syl]

# ---------- enrich each idiom ----------
for entry in idioms:
    # strokes
    chars = [stroke_map.get(ch, 0) for ch in entry["word"] if not ch.isspace()]
    entry["strokes"]       = chars
    entry["total_strokes"] = sum(chars)
    # tones
    entry["tones"] = tones_for(entry["pinyin"])

# ---------- save result ----------
with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(idioms, f, ensure_ascii=False, indent=2)

print("✓ Done →", OUT_FILE)
