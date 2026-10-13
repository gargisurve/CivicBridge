
"""
CivicBridge - Local Multilingual Complaint Extractor

This module is intentionally self-contained.

It extracts:
    - language
    - issue / issue_type
    - location
    - area
    - landmark
    - duration
    - frequency
    - time_of_occurrence
    - people_affected
    - cause
    - requested_action
    - ongoing
    - safety_risk
    - evidence_mentioned
    - additional_details

Design:
    1. Normalize English / Marathi / Marathi-English text.
    2. Detect specific civic issue using a civic vocabulary.
    3. Extract duration using multilingual patterns.
    4. Extract location using multilingual location phrases.
    5. Return the same dictionary-style interface expected by app.py.
"""

import re
from difflib import SequenceMatcher
from typing import Optional


# ============================================================
# NORMALIZATION
# ============================================================

MARATHI_DIGITS = str.maketrans(
    "०१२३४५६७८९",
    "0123456789"
)


def normalize_text(text: str) -> str:
    """Normalize spacing and common Marathi punctuation."""
    if not text:
        return ""

    text = str(text).translate(MARATHI_DIGITS)

    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u00a0": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text).strip()

    return text


def normalize_for_matching(text: str) -> str:
    """
    Lowercase Latin text while preserving Marathi characters.
    This lets us match Marathi and English/code-mixed phrases.
    """
    text = normalize_text(text).lower()

    # Common Hinglish spelling normalization.
    replacements = {
        "divasapasun": "divasapasun",
        "divasapasun": "divasapasun",
        "divas se": "divas se",
        "divas": "days",
        "divas": "days",
        "aathavda": "week",
        "aathavdyapasun": "week pasun",
        "mahina": "month",
        "mahinyapasun": "month pasun",
        "paani": "pani",
        "pany": "pani",
        "streetlights": "street lights",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


# ============================================================
# LANGUAGE
# ============================================================

def detect_language(text: str) -> str:
    """
    Simple deterministic language detection suitable for
    English / Marathi / Marathi-English civic complaints.
    """
    if not text:
        return "Unknown"

    text = normalize_text(text)

    devanagari = len(
        re.findall(r"[\u0900-\u097F]", text)
    )

    latin = len(
        re.findall(r"[A-Za-z]", text)
    )

    if devanagari == 0:

        # Roman Marathi / Hinglish detection.
        roman_marathi_terms = [
            "madhe",
            "madhye",
            "jawal",
            "javal",
            "pasun",
            "divas",
            "aathavda",
            "mahina",
            "paani",
            "pani",
            "nahi",
            "aahe",
            "ahe",
            "band",
            "kharab",
            "kachra",
            "rasta",
            "khadde",
            "khadda",
            "uchalla",
            "collect zala nahi",
            "yet nahi",
            "hot nahi",
        ]

        lower = text.lower()

        roman_hits = sum(
            1
            for term in roman_marathi_terms
            if term in lower
        )

        if roman_hits >= 1:
            return "Marathi-English"

        return "English"

    if latin == 0:
        return "Marathi"

    # Both scripts occur.
    if devanagari >= 5 and latin >= 5:
        return "Marathi-English"

    if devanagari > latin:
        return "Marathi"

    return "Marathi-English"


# ============================================================
# CIVIC ISSUE VOCABULARY
# ============================================================

ISSUE_PATTERNS = [
    # Most specific phrases first.

    (
        "No water supply",
        [
            "no water supply",
            "no water",
            "water supply stopped",
            "water supply is stopped",
            "water is not coming",
            "water not coming",
            "paani nahi",
            "pani nahi",
            "paani yet nahi",
            "pani yet nahi",
            "paani yet nahiye",
            "pani yet nahi",
            "pani yet nahiye",
            "paani puravatha band",
            "पाणी येत नाही",
            "पाणी येत नाहीये",
            "पाणीपुरवठा बंद",
            "पाणी पुरवठा बंद",
            "पाणी मिळत नाही",
        ],
    ),

    (
        "Water leakage",
        [
            "water leakage",
            "water leak",
            "leaking water",
            "pipeline leak",
            "pipe leakage",
            "paani leak",
            "pani leak",
            "पाण्याची गळती",
            "पाईपमधून पाणी",
            "पाईप गळत",
        ],
    ),

    (
        "Low water pressure",
        [
            "low water pressure",
            "water pressure is low",
            "paani pressure kami",
            "pani pressure kami",
            "पाण्याचा दाब कमी",
        ],
    ),

    (
        "Dirty or contaminated water",
        [
            "dirty water",
            "contaminated water",
            "muddy water",
            "unclean water",
            "paani ghan",
            "paani dirty",
            "पाणी घाण",
            "पाणी दूषित",
            "दूषित पाणी",
        ],
    ),

    (
        "Drain blockage",
        [
            "drain blockage",
            "blocked drain",
            "drain is blocked",
            "drain blocked",
            "nala blocked",
            "nala blockage",
            "नाला तुंबला",
            "नाला तुंबलेला",
            "गटार तुंबले",
            "गटार तुंबलेले",
            "गटार बंद",
        ],
    ),

    (
        "Sewage overflow",
        [
            "sewage overflow",
            "sewage is overflowing",
            "sewage overflow problem",
            "sewer overflow",
            "sewer is overflowing",
            "sewage coming out",
            "सांडपाणी रस्त्यावर",
            "सांडपाणी वाहत",
            "गटाराचे पाणी रस्त्यावर",
        ],
    ),

    (
        "Open or damaged manhole",
        [
            "open manhole",
            "broken manhole",
            "damaged manhole",
            "manhole is open",
            "manhole cover missing",
            "मॅनहोल उघडे",
            "मॅनहोलचे झाकण नाही",
            "मॅनहोल तुटले",
        ],
    ),

    (
        "Garbage collection failure",
        [
            "garbage not collected",
            "garbage collection not happening",
            "garbage has not been collected",
            "garbage collection stopped",
            "waste not collected",
            "kachra collect nahi",
            "kachra collect zala nahi",
            "kachra uchalla nahi",
            "kachra uchalat nahi",
            "kachra collect hot nahi",
            "garbage collect hot nahi",
            "garbage collect zala nahi",
            "garbage collected nahi",
            "कचरा उचलला नाही",
            "कचरा गोळा केला नाही",
            "कचरा संकलन होत नाही",
        ],
    ),

    (
        "Illegal waste dumping",
        [
            "illegal dumping",
            "garbage dumping",
            "waste dumping",
            "dumping garbage",
            "kachra taktat",
            "kachra dump",
            "कचरा टाकतात",
            "कचरा टाकला जातो",
        ],
    ),

    (
        "Street light failure",
        [
            "street light not working",
            "street lights not working",
            "street lights have not been working",
            "street light has not been working",
            "street light is not working",
            "streetlights are not working",
            "street light failure",
            "street light is off",
            "street lights are off",
            "street light not working",
            "street lights not working",
            "street lights off",
            "streetlight band",
            "street light band",
            "street lights band",
            "streetlights band",
            "light band",
            "light band aahe",
            "light band aahet",
            "रस्त्यावरील दिवे बंद",
            "रस्त्यावरील लाईट बंद",
            "स्ट्रीट लाईट बंद",
            "पथदिवे बंद",
        ],
    ),

    (
        "Potholes",
        [
            "pothole",
            "potholes",
            "many potholes",
            "road has potholes",
            "road full of potholes",
            "khadde",
            "khadda",
            "rastyavar khadde",
            "रस्त्यावर खड्डे",
            "रस्त्यावर खड्डा",
            "खड्ड्यांचा त्रास",
        ],
    ),

    (
        "Damaged road",
        [
            "damaged road",
            "broken road",
            "road is damaged",
            "road is broken",
            "bad road",
            "road damage",
            "rasta kharab",
            "rasta tutla",
            "रस्ता खराब",
            "रस्ता तुटला",
            "रस्ता खराब झाला",
        ],
    ),

    (
        "Footpath damage",
        [
            "broken footpath",
            "damaged footpath",
            "footpath is damaged",
            "footpath damage",
            "sidewalk damaged",
            "sidewalk broken",
            "फुटपाथ खराब",
            "फुटपाथ तुटला",
            "पदपथ खराब",
        ],
    ),

    (
        "Waterlogging",
        [
            "waterlogging",
            "water logging",
            "water logged",
            "flooded road",
            "road is flooded",
            "flooding on road",
            "paani sathlay",
            "paani sachla",
            "रस्त्यावर पाणी साचले",
            "पाणी साचले आहे",
            "पाणी साचलं आहे",
        ],
    ),

    (
        "Power outage",
        [
            "power outage",
            "power cut",
            "electricity outage",
            "electricity is out",
            "no electricity",
            "power is gone",
            "light nahi",
            "bijli nahi",
            "वीज नाही",
            "वीजपुरवठा बंद",
            "वीज गेली",
        ],
    ),

    (
        "Low voltage",
        [
            "low voltage",
            "voltage is low",
            "voltage kami",
            "व्होल्टेज कमी",
        ],
    ),

    (
        "Exposed electrical wire",
        [
            "exposed wire",
            "open electrical wire",
            "electric wire exposed",
            "loose electrical wire",
            "wire hanging",
            "वीज वायर उघडी",
            "विद्युत तार उघडी",
            "तार लोंबकळत",
        ],
    ),

    (
        "Mosquito breeding",
        [
            "mosquito breeding",
            "mosquitoes breeding",
            "mosquito problem",
            "too many mosquitoes",
            "mosquito infestation",
            "डासांची पैदास",
            "डासांचा त्रास",
            "डास खूप आहेत",
        ],
    ),

    (
        "Unhygienic conditions",
        [
            "unhygienic",
            "unhygienic conditions",
            "dirty surroundings",
            "filthy surroundings",
            "unclean surroundings",
            "अस्वच्छता",
            "अस्वच्छ परिसर",
            "घाण परिसर",
        ],
    ),

    (
        "Public toilet issue",
        [
            "public toilet",
            "toilet is dirty",
            "public toilet is dirty",
            "toilet not usable",
            "toilet not working",
            "सार्वजनिक शौचालय",
            "शौचालय अस्वच्छ",
            "शौचालय वापरण्यायोग्य नाही",
        ],
    ),

    (
        "Bus service issue",
        [
            "bus service issue",
            "bus not coming",
            "bus service not available",
            "bus is not coming",
            "bus frequency is low",
            "bus frequency low",
            "bus problem",
            "बस येत नाही",
            "बस सेवा बंद",
            "बससेवा उपलब्ध नाही",
        ],
    ),

    (
        "Damaged bus stop",
        [
            "damaged bus stop",
            "broken bus stop",
            "bus stop is damaged",
            "bus stop broken",
            "बस स्टॉप खराब",
            "बस थांबा खराब",
            "बस थांबा तुटला",
        ],
    ),

    (
        "Encroachment",
        [
            "encroachment",
            "illegal encroachment",
            "footpath encroachment",
            "road encroachment",
            "अतिक्रमण",
            "रस्त्यावर अतिक्रमण",
            "फुटपाथवर अतिक्रमण",
        ],
    ),

    (
        "Illegal construction",
        [
            "illegal construction",
            "unauthorized construction",
            "construction without permission",
            "बेकायदेशीर बांधकाम",
            "अनधिकृत बांधकाम",
        ],
    ),

    (
        "Traffic congestion",
        [
            "traffic congestion",
            "heavy traffic",
            "traffic jam",
            "traffic problem",
            "traffic is very heavy",
            "वाहतूक कोंडी",
            "ट्रॅफिक जाम",
            "वाहतूक समस्या",
        ],
    ),

    (
        "Stray animal issue",
        [
            "stray dogs",
            "stray animals",
            "stray dog problem",
            "animal nuisance",
            "कुत्र्यांचा त्रास",
            "भटक्या कुत्र्यांचा त्रास",
            "भटके प्राणी",
        ],
    ),

    (
        "Public park issue",
        [
            "park is damaged",
            "park maintenance",
            "park not maintained",
            "public park issue",
            "garden not maintained",
            "उद्यानाची देखभाल",
            "गार्डनची देखभाल",
            "उद्यान खराब",
        ],
    ),
]


def _phrase_present(text: str, phrase: str) -> bool:
    """
    Match phrases safely.
    For Latin phrases, use word boundaries.
    For Marathi phrases, normal substring matching is more reliable.
    """
    phrase = normalize_for_matching(phrase)
    text = normalize_for_matching(text)

    if re.search(r"[A-Za-z]", phrase):
        return bool(
            re.search(
                rf"(?<![A-Za-z]){re.escape(phrase)}(?![A-Za-z])",
                text
            )
        )

    return phrase in text


def extract_issue_type(text: str) -> str:
    """Return the most specific recognized civic issue."""

    normalized = normalize_for_matching(
        text
    )

    # Flexible street-light expressions.
    # These intentionally allow a location phrase between
    # "street light(s)" and the failure expression.
    street_light_regexes = [
        r"street\s+lights?.{0,100}?not\s+working",
        r"street\s+lights?.{0,100}?have\s+not\s+been\s+working",
        r"street\s+lights?.{0,100}?are\s+off",
        r"streetlight.{0,100}?not\s+working",
        r"streetlights?.{0,100}?band",
    ]

    for pattern in street_light_regexes:

        if re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE
        ):
            return "Street light failure"

    # 1) Exact phrase matching remains the most trusted signal.
    for issue, patterns in ISSUE_PATTERNS:
        for pattern in patterns:
            if _phrase_present(text, pattern):
                return issue

    # 2) Flexible matching for word-order changes, extra words and small typos.
    # This is deliberately a fallback: it cannot override a clear exact match.
    fuzzy_candidates = []
    normalized_text = normalize_for_matching(text)
    latin_words = re.findall(r"[a-z]+", normalized_text)
    devanagari_words = re.findall(r"[\\u0900-\\u097F]+", normalized_text)

    # Compare known issue phrases against nearby word windows so a complaint
    # like "supply water not coming" can match "water not coming".
    for issue, patterns in ISSUE_PATTERNS:
        best_score = 0.0
        for pattern in patterns:
            candidate = normalize_for_matching(pattern)

            if re.search(r"[A-Za-z]", candidate):
                target_words = re.findall(r"[a-z]+", candidate)
                if not target_words:
                    continue

                # Token overlap is robust to word order and harmless filler words.
                text_set = set(latin_words)
                target_set = set(target_words)
                meaningful = {w for w in target_set if len(w) > 2}
                if meaningful:
                    overlap = len(meaningful & text_set) / len(meaningful)
                    if overlap >= 0.80:
                        best_score = max(best_score, 0.82 + 0.15 * overlap)

                # Sliding windows handle extra location/time words between keywords.
                n = len(target_words)
                for start in range(max(1, len(latin_words) - n + 1)):
                    window = " ".join(latin_words[start:start + max(n + 2, 1)])
                    ratio = SequenceMatcher(None, candidate, window).ratio()
                    best_score = max(best_score, ratio * 0.92)

                # Whole complaint similarity catches minor misspellings in short inputs.
                if len(normalized_text) < 100:
                    best_score = max(
                        best_score,
                        SequenceMatcher(None, candidate, normalized_text).ratio() * 0.90
                    )
            else:
                # Marathi script: use character similarity only for reasonably long
                # phrases, avoiding weak matches on common short words.
                if len(candidate) >= 5:
                    ratio = SequenceMatcher(None, candidate, normalized_text).ratio()
                    if ratio >= 0.72:
                        best_score = max(best_score, ratio)

            # Strong signal combinations for common reordered civic descriptions.
            if candidate and candidate in normalized_text:
                best_score = max(best_score, 1.0)

        if best_score >= 0.80:
            fuzzy_candidates.append((best_score, issue))

    if fuzzy_candidates:
        fuzzy_candidates.sort(reverse=True)
        # Require a reasonably strong match; otherwise preserve "General civic issue".
        top_score, top_issue = fuzzy_candidates[0]
        if top_score >= 0.84:
            return top_issue

    # 3) Lightweight concept-based fallback for common paraphrases.
    concept_signals = [
        ("No water supply", ["water", "supply", "pani", "पाणी", "पाणीपुरवठा"], ["no", "not", "stopped", "nahi", "band", "येत नाही", "बंद"]),
        ("Water leakage", ["leak", "leaking", "गळती", "गळत"], ["water", "pipe", "pipeline", "pani", "पाणी", "नळ"]),
        ("Garbage collection failure", ["garbage", "waste", "kachra", "कचरा"], ["collect", "collection", "pickup", "picked up", "pick up", "removed", "uchalla", "उचलला", "गोळा"]),
        ("Potholes", ["pothole", "khadda", "khadde", "खड्डा", "खड्डे"], []),
        ("Street light failure", ["streetlight", "street light", "light", "पथदिवे", "दिवे"], ["off", "dark", "broken", "band", "बंद", "not working"]),
        ("Power outage", ["electricity", "power", "bijli", "वीज"], ["cut", "outage", "gone", "nahi", "नाही", "बंद"]),
        ("Waterlogging", ["water", "pani", "पाणी", "flood"], ["logged", "logging", "standing", "sachla", "साचले"]),
        ("Drainage blockage", ["drain", "sewage", "gutter", "नाला", "गटार", "सांडपाणी"], ["blocked", "overflow", "choked", "तुंबले", "भरले"]),
    ]
    normalized_lower = normalized_text.lower()
    for issue, subjects, symptoms in concept_signals:
        subject_hit = any(term in normalized_lower for term in subjects)
        symptom_hit = not symptoms or any(term in normalized_lower for term in symptoms)
        if subject_hit and symptom_hit:
            return issue

    return "General civic issue"


def extract_issue(text: str) -> str:
    """
    Keep issue and issue_type consistent.
    This is important because the router uses issue_type.
    """
    return extract_issue_type(text)


# ============================================================
# DURATION
# ============================================================

NUMBER_WORDS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "a": "1",
    "an": "1",
    "ek": "1",
    "eka": "1",
    "don": "2",
    "teen": "3",
    "tin": "3",
    "char": "4",
    "pach": "5",
}


def _canonical_number(value: str) -> str:
    value = value.strip().lower()

    if value in NUMBER_WORDS:
        return NUMBER_WORDS[value]

    return value


def _canonical_duration(value: str, unit: str) -> str:
    number = _canonical_number(value)

    unit = unit.lower()

    if unit.startswith("day") or unit in {
        "divas",
        "divasapasun",
        "divasapasun",
    }:
        return f"{number} day" + (
            "" if number == "1" else "s"
        )

    if unit.startswith("week") or unit in {
        "aathavda",
        "aathavdyapasun",
    }:
        return f"{number} week" + (
            "" if number == "1" else "s"
        )

    if unit.startswith("month") or unit in {
        "mahina",
        "mahinyapasun",
    }:
        return f"{number} month" + (
            "" if number == "1" else "s"
        )

    if unit.startswith("hour") or unit in {
        "taas",
        "tas",
    }:
        return f"{number} hour" + (
            "" if number == "1" else "s"
        )

    return f"{number} {unit}"


def extract_duration(text: str) -> Optional[str]:
    """
    Extract duration from English, Marathi and common
    Marathi-English/Hinglish constructions.
    """

    original = normalize_text(text)
    lower = original.lower()

    # --------------------------------------------------------
    # English:
    # for 3 days / for three days
    # since 3 days
    # --------------------------------------------------------

    patterns = [
        (
            r"\bfor\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
            r"\s*(hours?|days?|weeks?|months?)\b",
            "standard"
        ),
        (
            r"\bsince\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
            r"\s*(hours?|days?|weeks?|months?)\b",
            "standard"
        ),
        (
            r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
            r"\s*(hours?|days?|weeks?|months?)\s+"
            r"(?:ago|now)\b",
            "standard"
        ),
    ]

    for pattern, _ in patterns:

        match = re.search(
            pattern,
            lower
        )

        if match:
            return _canonical_duration(
                match.group(1),
                match.group(2)
            )

    # --------------------------------------------------------
    # English relative phrases
    # --------------------------------------------------------

    relative_phrases = [
        (
            r"\bsince\s+yesterday\b",
            "Since yesterday"
        ),
        (
            r"\bsince\s+last\s+night\b",
            "Since last night"
        ),
        (
            r"\bsince\s+monday\b",
            "Since Monday"
        ),
        (
            r"\bsince\s+tuesday\b",
            "Since Tuesday"
        ),
        (
            r"\bsince\s+wednesday\b",
            "Since Wednesday"
        ),
        (
            r"\bsince\s+thursday\b",
            "Since Thursday"
        ),
        (
            r"\bsince\s+friday\b",
            "Since Friday"
        ),
        (
            r"\bsince\s+saturday\b",
            "Since Saturday"
        ),
        (
            r"\bsince\s+sunday\b",
            "Since Sunday"
        ),
        (
            r"\bfor\s+a\s+week\b",
            "1 week"
        ),
        (
            r"\bfor\s+the\s+past\s+week\b",
            "1 week"
        ),
        (
            r"\bfor\s+a\s+month\b",
            "1 month"
        ),
        (
            r"\bfor\s+the\s+past\s+month\b",
            "1 month"
        ),
    ]

    for pattern, result in relative_phrases:

        if re.search(pattern, lower):
            return result

    # --------------------------------------------------------
    # Marathi number words: गेल्या सहा दिवसांपासून, तीन दिवसांपासून
    # --------------------------------------------------------
    marathi_number_words = {
        "एक": "1", "एका": "1",
        "दोन": "2",
        "तीन": "3",
        "चार": "4",
        "पाच": "5",
        "सहा": "6",
        "सात": "7",
        "आठ": "8",
        "नऊ": "9",
        "दहा": "10",
    }
    marathi_word_duration = re.search(
        r"(?:गेल्या|मागील|मागच्या)?\s*"
        r"(एक|एका|दोन|तीन|चार|पाच|सहा|सात|आठ|नऊ|दहा)\s*"
        r"(दिवसांपासून|दिवस|आठवड्यांपासून|आठवडा|महिन्यांपासून|महिना)",
        original
    )
    if marathi_word_duration:
        number = marathi_number_words[marathi_word_duration.group(1)]
        unit_text = marathi_word_duration.group(2)
        unit = "days" if "दिवस" in unit_text else ("weeks" if "आठव" in unit_text else "months")
        return _canonical_duration(number, unit)

    # --------------------------------------------------------
    # Marathi:
    # गेल्या ३ दिवसांपासून
    # मागील २ आठवड्यांपासून
    # ३ दिवसांपासून
    # --------------------------------------------------------

    marathi_patterns = [
        r"(?:गेल्या|मागील|मागच्या)\s+"
        r"(\d+)\s+"
        r"(दिवस|दिवसांपासून|आठवडा|आठवड्यांपासून|महिना|महिन्यांपासून)"
        r"(?:पासून)?",

        r"(\d+)\s+"
        r"(दिवसांपासून|दिवस|आठवड्यांपासून|आठवडा|महिन्यांपासून|महिना)",
    ]

    for pattern in marathi_patterns:

        match = re.search(
            pattern,
            original
        )

        if match:

            unit = match.group(2)

            if "दिवस" in unit:
                unit = "days"

            elif "आठव" in unit:
                unit = "weeks"

            elif "महिन" in unit:
                unit = "months"

            return _canonical_duration(
                match.group(1),
                unit
            )

    # Marathi relative durations without explicit numbers.
    marathi_relative = [
        (
            r"(?:गेल्या|मागील|मागच्या)\s+"
            r"(?:आठवड्यापासून|आठवड्यांपासून)",
            "1 week"
        ),
        (
            r"(?:गेल्या|मागील|मागच्या)\s+"
            r"(?:महिन्यापासून|महिन्यांपासून)",
            "1 month"
        ),
        (
            r"(?:कालपासून|काल पासून)",
            "Since yesterday"
        ),
    ]

    for pattern, result in marathi_relative:

        if re.search(
            pattern,
            original
        ):
            return result

    # --------------------------------------------------------
    # Hinglish:
    # 3 divasapasun
    # 3 divas se
    # 1 week pasun
    # ek week pasun
    # --------------------------------------------------------

    hinglish_patterns = [
        (
            r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|ek|don|teen|tin|char|pach|saha|saat|aath|nau|daha)"
            r"\s*(divas|divasapasun|days?)"
            r"(?:\s*pasun)?\b",
            "days"
        ),
        (
            r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|ek|don|teen|tin|char|pach|saha|saat|aath|nau|daha)"
            r"\s*(?:divas)\s*se\b",
            "days"
        ),
        (
            r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|ek|don|teen|tin|char|pach|saha|saat|aath|nau|daha)"
            r"\s*(week|weeks?)\s*(?:pasun|se)?\b",
            "weeks"
        ),
        (
            r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|ek|don|teen|tin|char|pach|saha|saat|aath|nau|daha)"
            r"\s*(month|months?)\s*(?:pasun|se)?\b",
            "months"
        ),
    ]

    for pattern, unit in hinglish_patterns:

        match = re.search(
            pattern,
            lower
        )

        if match:

            return _canonical_duration(
                match.group(1),
                unit
            )

    # --------------------------------------------------------
    # "last 3 days", "past 2 weeks"
    # --------------------------------------------------------

    match = re.search(
        r"\b(?:last|past|previous)\s+"
        r"(\d+)\s*(days?|weeks?|months?)\b",
        lower
    )

    if match:

        return _canonical_duration(
            match.group(1),
            match.group(2)
        )

    return None


# ============================================================
# LOCATION
# ============================================================

LOCATION_INTRO_PATTERNS = [
    # English
    r"\b(?:in|at|near|around|outside|opposite|behind|beside|"
    r"close to|next to)\s+"
    r"([A-Za-z][A-Za-z0-9 .,'&/\-]{1,80}?)"
    r"(?=\s+(?:for|since|from|has|have|there|is|are|"
    r"and|but|because|with|where|which)\b|[.!?,]|$)",

    # Hinglish
    r"\b(?:madhe|madhye|jawal|javal|samor|maghe|baher)\s+"
    r"([A-Za-z][A-Za-z0-9 .,'&/\-]{1,80}?)"
    r"(?=\s+(?:for|since|pasun|aahe|ahe|nahi|band|and|"
    r"pan|mule)\b|[.!?,]|$)",

    # Marathi
    r"(?:मध्ये|मधे|जवळ|समोर|मागे|बाहेर|येथे|इथे)\\s+"
    r"([\u0900-\u097F][\u0900-\u097F0-9 .,'&/\-]{1,80}?)"
    r"(?=\s+(?:गेल्या|मागील|पासून|आहे|नाही|बंद|"
    r"आणि|पण|मुळे)\b|[.!?,]|$)",
]


def _looks_like_duration_fragment(candidate: str) -> bool:
    candidate = normalize_text(candidate).lower()

    duration_words = [
        "दिवस",
        "दिवसांपासून",
        "आठवडा",
        "आठवड्यापासून",
        "आठवड्यांपासून",
        "महिना",
        "महिन्यापासून",
        "महिन्यांपासून",
        "गेल्या",
        "मागील",
        "मागच्या",
        "पासून",
    ]

    if any(
        word in candidate
        for word in duration_words
    ):
        if re.search(
            r"\d+",
            candidate
        ) or any(
            word in candidate
            for word in ["गेल्या", "मागील", "मागच्या"]
        ):
            return True

    return False


def _clean_location_candidate(candidate: str) -> str:
    candidate = normalize_text(candidate)

    # Remove common trailing filler.
    candidate = re.sub(
        r"\s+(?:for|since|from|because|and|but|with|where)\b.*$",
        "",
        candidate,
        flags=re.IGNORECASE
    )

    candidate = re.sub(
        r"\s+(?:पासून|आहे|नाही|आणि|पण|मुळे)\b.*$",
        "",
        candidate
    )

    candidate = candidate.strip(
        " .,:;!?-–—"
    )

    # Remove accidental generic starts.
    candidate = re.sub(
        r"^(?:the|my|our|near|at|in)\s+",
        "",
        candidate,
        flags=re.IGNORECASE
    )

    return candidate.strip()


def _location_quality(candidate: str) -> int:
    if not candidate:
        return -100

    score = 0

    words = candidate.split()

    if len(words) <= 8:
        score += 2

    if re.search(
        r"\b(?:sector|sec|road|rd|street|station|nagar|"
        r"colony|society|market|school|hospital|junction|"
        r"chowk|circle|gaon|village)\b",
        candidate,
        re.IGNORECASE
    ):
        score += 5

    if re.search(
        r"\b(?:panvel|kharghar|nerul|vashi|belapur|thane|"
        r"mumbai|navi mumbai|new panvel|ulwe|kamothe|kalamboli)\b",
        candidate,
        re.IGNORECASE
    ):
        score += 5

    if re.search(
        r"(?:सेक्टर|नगर|चौक|रस्ता|स्टेशन|वाडी|गाव|"
        r"शाळा|रुग्णालय|बाजार)",
        candidate
    ):
        score += 5

    # Don't accept a generic word as a location.
    generic = {
        "area",
        "location",
        "place",
        "my area",
        "our area",
        "the area",
        "there",
        "इथे",
        "येथे",
    }

    if candidate.lower() in generic:
        return -100

    return score


def _extract_sector_location(text: str) -> Optional[str]:
    patterns = [
        r"\bsector[-\s]?(\d+[A-Za-z]?)\b",
        r"\bsec[-\s]?(\d+[A-Za-z]?)\b",
        r"सेक्टर[-\s]?(\d+[A-Za-z]?)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            normalize_text(text),
            flags=re.IGNORECASE
        )

        if match:
            return f"Sector {match.group(1)}"

    return None


def extract_location(text: str) -> Optional[str]:
    """
    Extract a human-readable location phrase.
    This does not geocode it; app.py already handles Nominatim.
    """

    original = normalize_text(text)

    candidates = []

    sector = _extract_sector_location(
        original
    )

    if sector:
        candidates.append(
            (
                _location_quality(sector),
                sector
            )
        )

    for pattern in LOCATION_INTRO_PATTERNS:

        for match in re.finditer(
            pattern,
            original,
            flags=re.IGNORECASE
        ):

            candidate = _clean_location_candidate(
                match.group(1)
            )

            if not candidate:
                continue

            # Don't let a duration fragment become a location.
            if _looks_like_duration_fragment(candidate):
                continue

            # Don't let a duration become a location.
            if re.fullmatch(
                r"\d+\s+(?:days?|weeks?|months?|hours?)",
                candidate,
                flags=re.IGNORECASE
            ):
                continue

            score = _location_quality(
                candidate
            )

            if score > -100:
                candidates.append(
                    (
                        score + min(len(candidate), 40) // 10,
                        candidate
                    )
                )

    # Common Marathi named-place candidates.
    marathi_named_patterns = [
        r"(न्यू\s+पनवेल(?:\s+(?:पूर्व|पश्चिम))?)",
        r"(पनवेल(?:\s+(?:पूर्व|पश्चिम))?)",
        r"(खारघर(?:\s+स्टेशन)?)",
        r"(नेरुळ(?:\s+स्टेशन)?)",
        r"(वाशी(?:\s+स्टेशन)?)",
        r"(बेलापूर(?:\s+स्टेशन)?)",
        r"(उलवे)",
        r"(कामोठे)",
        r"(कळंबोली)",
        r"(ठाणे(?:\s+(?:पूर्व|पश्चिम))?)",
    ]

    for pattern in marathi_named_patterns:

        for match in re.finditer(
            pattern,
            original,
            flags=re.IGNORECASE
        ):

            candidate = _clean_location_candidate(
                match.group(1)
            )

            if candidate:
                candidates.append(
                    (
                        _location_quality(candidate) + 5,
                        candidate
                    )
                )

    # Named-place patterns without an intro word.
    named_patterns = [
        r"\b(Borivali(?:\s+(?:East|West))?)\b",
        r"\b(Borivli(?:\s+(?:East|West))?)\b",
        r"\b(Andheri(?:\s+(?:East|West))?)\b",
        r"\b(Dahisar(?:\s+(?:East|West))?)\b",
        r"\b(Malad(?:\s+(?:East|West))?)\b",
        r"\b(Kandivali(?:\s+(?:East|West))?)\b",
        r"\b(Goregaon(?:\s+(?:East|West))?)\b",
        r"\b(Bandra(?:\s+(?:East|West))?)\b",
        r"\b(New Panvel(?:\s+(?:East|West))?)\b",
        r"\b(Panvel(?:\s+(?:East|West))?)\b",
        r"\b(Kharghar(?:\s+(?:station|sector[-\s]?\d+))?)\b",
        r"\b(Nerul(?:\s+(?:East|West|station))?)\b",
        r"\b(Vashi(?:\s+(?:station|sector[-\s]?\d+))?)\b",
        r"\b(Belapur(?:\s+(?:station|CBD))?)\b",
        r"\b(Kamothe(?:\s+(?:sector[-\s]?\d+))?)\b",
        r"\b(Kalamboli(?:\s+(?:sector[-\s]?\d+))?)\b",
        r"\b(Ulwe(?:\s+(?:sector[-\s]?\d+))?)\b",
        r"\b(Thane(?:\s+(?:East|West))?)\b",
    ]

    for pattern in named_patterns:

        for match in re.finditer(
            pattern,
            original,
            flags=re.IGNORECASE
        ):

            candidate = _clean_location_candidate(
                match.group(1)
            )

            if candidate:
                candidates.append(
                    (
                        _location_quality(candidate) + 4,
                        candidate
                    )
                )

    if not candidates:
        return None

    # Prefer the highest-quality candidate.
    candidates.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return candidates[0][1]


def extract_area(text: str) -> Optional[str]:
    location = extract_location(text)

    if not location:
        return None

    if re.search(
        r"\bsector[-\s]?\d+",
        location,
        flags=re.IGNORECASE
    ):
        return location

    if re.search(
        r"(?:सेक्टर|नगर|वाडी|गाव|गांव)",
        location
    ):
        return location

    return None


def extract_landmark(text: str) -> Optional[str]:
    original = normalize_text(text)

    # Capture named-place + landmark combinations in code-mixed Marathi.
    named_station = re.search(
        r"\b((?:Borivali|Borivli|Andheri|Dahisar|Malad|Kandivali|Goregaon|"
        r"Bandra|Thane|Panvel|Kharghar|Nerul|Vashi|Belapur)"
        r"(?:\\s+(?:East|West))?)\\s+"
        r"(?:madhlya|madhla|madhye|madhe|javalchya|jawalchya|"
        r"jawalcha|javalcha|jawal|javal)?\\s*"
        r"((?:railway\\s+)?station)",
        original,
        flags=re.IGNORECASE
    )
    if named_station:
        return f"{named_station.group(1).title()} {named_station.group(2).title()}"

    patterns = [
        # Roman Marathi/code-mixed: "railway station jawalcha", "school javal"
        r"\b((?:railway\s+)?station|school|hospital|market|temple|chowk|junction|circle)"
        r"\s+(?:jawalcha|javalcha|jawal|javal|samor)\b",
        r"\bnear\s+([A-Za-z][A-Za-z0-9 .'-]{2,50}?"
        r"(?:station|school|hospital|market|temple|chowk|"
        r"junction|circle))\b",

        r"\bopposite\s+([A-Za-z][A-Za-z0-9 .'-]{2,50}?"
        r"(?:station|school|hospital|market|temple|chowk|"
        r"junction|circle))\b",

        r"(?:जवळ|जवळी|जवळील|समोर)\\s*"
        r"([\u0900-\u097F][\u0900-\u097F .'-]{2,50}?"
        r"(?:स्टेशन|शाळा|रुग्णालय|बाजार|मंदिर|चौक))",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            original,
            flags=re.IGNORECASE
        )

        if match:
            return _clean_location_candidate(
                match.group(1)
            )

    return None


# ============================================================
# OTHER INFORMATION
# ============================================================

def extract_frequency(text: str) -> Optional[str]:
    lower = normalize_text(text).lower()

    patterns = [
        (r"\bevery\s+day\b", "Daily"),
        (r"\bdaily\b", "Daily"),
        (r"\bevery\s+night\b", "Every night"),
        (r"\bevery\s+week\b", "Weekly"),
        (r"\bfrequently\b", "Frequently"),
        (r"\boften\b", "Frequently"),
        (r"\boccasionally\b", "Occasionally"),
        (r"दररोज", "Daily"),
        (r"रोज", "Daily"),
        (r"वारंवार", "Frequently"),
        (r"नेहमी", "Frequently"),
    ]

    for pattern, result in patterns:

        if re.search(
            pattern,
            lower
        ):
            return result

    return None


def extract_time_of_occurrence(
    text: str
) -> Optional[str]:

    original = normalize_text(text)
    lower = original.lower()

    patterns = [
        (
            r"\b(?:at|around)\s+"
            r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b",
            1
        ),
        (
            r"\b(?:during|in)\s+"
            r"(morning|afternoon|evening|night)\b",
            1
        ),
        (
            r"(?:सकाळी|दुपारी|संध्याकाळी|रात्री|रात्रीच्या वेळी)",
            0
        ),
        (
            r"\b(ratri|raat|ratri|night time)\b",
            1
        ),
    ]

    for pattern, group in patterns:

        match = re.search(
            pattern,
            original if "सकाळ" in pattern else lower,
            flags=re.IGNORECASE
        )

        if match:

            if group == 0:
                return match.group(0)

            return match.group(group)

    return None


def extract_people_affected(text: str) -> Optional[str]:
    original = normalize_text(text)
    lower = original.lower()

    patterns = [
        (
            r"\b(\d+)\s+(?:people|persons|residents|families)"
            r"\s+(?:are\s+)?affected\b",
            1
        ),
        (
            r"\b(?:many|several)\s+(?:people|residents|families)"
            r"\s+(?:are\s+)?affected\b",
            0
        ),
        (
            r"(\d+)\s+लोकांना",
            1
        ),
        (
            r"(\d+)\s+कुटुंबांना",
            1
        ),
    ]

    for pattern, group in patterns:

        match = re.search(
            pattern,
            original if "लोक" in pattern or "कुटुंब" in pattern
            else lower,
            flags=re.IGNORECASE
        )

        if match:

            if group == 0:
                return "Many people"

            return f"{match.group(group)} people"

    if re.search(
        r"\b(?:many|several)\s+(?:people|residents)\b",
        lower
    ):
        return "Many people"

    if "अनेक रहिवासी" in original:
        return "Many residents"

    return None


def extract_cause(text: str) -> Optional[str]:
    original = normalize_text(text)
    lower = original.lower()

    patterns = [
        r"\bbecause\s+(.+?)(?:\.|$)",
        r"\bdue\s+to\s+(.+?)(?:\.|$)",
        r"\bbecause\s+of\s+(.+?)(?:\.|$)",
        r"कारण\s+(.+?)(?:\.|$)",
        r"मुळे\s+(.+?)(?:\.|$)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            original if "कारण" in pattern or "मुळे" in pattern else lower,
            flags=re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

    return None


def extract_requested_action(text: str) -> Optional[str]:
    original = normalize_text(text)
    lower = original.lower()

    patterns = [
        (
            r"\b(?:please|kindly)\s+"
            r"(repair|fix|restore|clean|remove|resolve|"
            r"inspect|replace|collect)\b",
            1
        ),
        (
            r"\b(?:requesting|request)\s+"
            r"(?:you\s+to\s+)?"
            r"(repair|fix|restore|clean|remove|resolve|"
            r"inspect|replace|collect)\b",
            1
        ),
        (
            r"(?:कृपया|कृपया त्वरित)\s*(.+?)(?:\.|$)",
            1
        ),
    ]

    for pattern, group in patterns:

        search_text = (
            original
            if "कृपया" in pattern
            else lower
        )

        match = re.search(
            pattern,
            search_text,
            flags=re.IGNORECASE
        )

        if match:
            return match.group(group).strip()

    return None


def extract_ongoing(text: str) -> Optional[bool]:
    original = normalize_text(text)
    lower = original.lower()

    positive = [
        "still",
        "still happening",
        "continues",
        "continuing",
        "ongoing",
        "yet not",
        "ajun",
        "अजून",
        "सुरू आहे",
        "अजूनही",
    ]

    negative = [
        "was fixed",
        "has been fixed",
        "resolved",
        "solved",
        "ठीक झाले",
        "निराकरण झाले",
    ]

    if any(
        phrase in lower
        for phrase in positive
    ) or any(
        phrase in original
        for phrase in positive
    ):
        return True

    if any(
        phrase in lower
        for phrase in negative
    ) or any(
        phrase in original
        for phrase in negative
    ):
        return False

    return None


def extract_safety_risk(text: str) -> Optional[str]:
    original = normalize_text(text)
    lower = original.lower()

    high_risk = [
        "dangerous",
        "danger",
        "risk to life",
        "electrocution",
        "accident risk",
        "bhiti vatate",
        "bhiti vatte",
        "travel karayla bhiti",
        "road var andhar",
        "andhar asto",
        "रात्री अंधार",
        "अंधार असतो",
        "लोकांना भीती",
        "open manhole",
        "exposed wire",
        "गंभीर धोका",
        "जीवाला धोका",
        "अपघाताचा धोका",
        "धोकादायक",
    ]

    if any(
        phrase in lower
        for phrase in high_risk
    ) or any(
        phrase in original
        for phrase in high_risk
    ):
        return "High"

    return None


def extract_evidence_mentioned(
    text: str
) -> Optional[str]:

    original = normalize_text(text)
    lower = original.lower()

    if any(
        phrase in lower
        for phrase in [
            "photo",
            "photos",
            "photograph",
            "video",
            "image",
            "attached",
            "proof",
        ]
    ):
        return "Yes"

    if any(
        phrase in original
        for phrase in [
            "फोटो",
            "व्हिडिओ",
            "पुरावा",
            "छायाचित्र",
        ]
    ):
        return "Yes"

    return None


# ============================================================
# ADDITIONAL DETAILS
# ============================================================

def extract_additional_details(
    text: str,
    issue: Optional[str],
    location: Optional[str],
    duration: Optional[str],
) -> Optional[str]:
    """
    Keep the original complaint available as additional context,
    but remove nothing aggressively. This avoids accidentally
    deleting meaningful Marathi/code-mixed information.
    """
    cleaned = normalize_text(text)

    if not cleaned:
        return None

    # If the complaint is very short, it is itself the detail.
    if len(cleaned) <= 180:
        return cleaned

    # Preserve the full original complaint for context.
    return cleaned


# ============================================================
# MAIN LOCAL EXTRACTOR
# ============================================================

def extract_with_local_rules(
    complaint: str
) -> dict:

    text = normalize_text(
        complaint
    )

    if not text:
        return {
            "language": "Unknown",
            "issue": "General civic issue",
            "issue_type": "General civic issue",
            "location": None,
            "area": None,
            "landmark": None,
            "duration": None,
            "frequency": None,
            "time_of_occurrence": None,
            "people_affected": None,
            "cause": None,
            "requested_action": None,
            "ongoing": None,
            "safety_risk": None,
            "evidence_mentioned": None,
            "additional_details": None,
        }

    issue = extract_issue(
        text
    )

    location = extract_location(
        text
    )

    duration = extract_duration(
        text
    )

    return {
        "language":
            detect_language(text),

        "issue":
            issue,

        "issue_type":
            issue,

        "location":
            location,

        "area":
            extract_area(text),

        "landmark":
            extract_landmark(text),

        "duration":
            duration,

        "frequency":
            extract_frequency(text),

        "time_of_occurrence":
            extract_time_of_occurrence(text),

        "people_affected":
            extract_people_affected(text),

        "cause":
            extract_cause(text),

        "requested_action":
            extract_requested_action(text),

        "ongoing":
            extract_ongoing(text),

        "safety_risk":
            extract_safety_risk(text),

        "evidence_mentioned":
            extract_evidence_mentioned(text),

        "additional_details":
            extract_additional_details(
                text,
                issue,
                location,
                duration
            ),
    }


# Backwards-compatible alias.
extract_complaint = extract_with_local_rules


# ============================================================
# SIMPLE LOCAL TEST
# ============================================================

if __name__ == "__main__":

    tests = [
        (
            "There has been no water supply in "
            "New Panvel East for three days."
        ),
        (
            "New Panvel East madhe 3 divasapasun "
            "paani nahi."
        ),
        (
            "न्यू पनवेलमध्ये गेल्या ३ दिवसांपासून "
            "पाणी येत नाही."
        ),
        (
            "The street lights near Kharghar station "
            "have not been working since Monday."
        ),
        (
            "Kharghar station jawal street lights "
            "band aahet."
        ),
        (
            "खारघर स्टेशनजवळील रस्त्यावरील दिवे बंद आहेत."
        ),
        (
            "Garbage has not been collected in Sector 10 "
            "for one week."
        ),
        (
            "Sector 10 madhe ek week pasun garbage "
            "collect zala nahi."
        ),
        (
            "सेक्टर १० मध्ये गेल्या आठवड्यापासून "
            "कचरा उचलला नाही."
        ),
        (
            "There are many potholes near Panvel station "
            "for 2 weeks."
        ),
    ]

    print("=" * 70)
    print("CIVICBRIDGE EXTRACTOR TEST")
    print("=" * 70)

    for index, complaint in enumerate(
        tests,
        start=1
    ):

        result = extract_with_local_rules(
            complaint
        )

        print()
        print(f"TEST {index}")
        print("Complaint :", complaint)
        print("Language  :", result["language"])
        print("Issue     :", result["issue"])
        print("Location  :", result["location"])
        print("Duration  :", result["duration"])

    print()
    print("=" * 70)
    print("TEST COMPLETED")
    print("=" * 70)
