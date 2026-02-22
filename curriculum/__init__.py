"""
Subject registry for the UK National Curriculum worksheet generator.

Maps each subject to its curriculum data, available year groups,
allowed worksheet types, word type keys for colour-coding, and icon.
"""

from curriculum.english import ENGLISH_CURRICULUM
from curriculum.maths import MATHS_CURRICULUM
from curriculum.science import SCIENCE_CURRICULUM
from curriculum.history import HISTORY_CURRICULUM
from curriculum.geography import GEOGRAPHY_CURRICULUM
from curriculum.computing import COMPUTING_CURRICULUM
from curriculum.languages import LANGUAGES_CURRICULUM


SUBJECT_REGISTRY = {
    "English": {
        "curriculum": ENGLISH_CURRICULUM,
        "years": ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "worksheet_types": [
            "cloze", "word_bank", "matching",
            "sentence_builder", "reading_comprehension",
        ],
        "word_types": ["time", "adjective", "verb", "noun", "name", "open"],
        "icon": "\U0001F4D6",  # 📖
    },
    "Maths": {
        "curriculum": MATHS_CURRICULUM,
        "years": ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "worksheet_types": [
            "cloze", "word_bank", "matching",
            "reading_comprehension", "problem_solving", "calculation_practice",
        ],
        "word_types": ["operation", "shape", "measure", "number", "vocabulary", "open"],
        "icon": "\U0001F4D0",  # 📐
    },
    "Science": {
        "curriculum": SCIENCE_CURRICULUM,
        "years": ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "worksheet_types": [
            "cloze", "word_bank", "matching",
            "reading_comprehension", "investigation",
        ],
        "word_types": ["process", "equipment", "organism", "material", "vocabulary", "open"],
        "icon": "\U0001F52C",  # 🔬
    },
    "History": {
        "curriculum": HISTORY_CURRICULUM,
        "years": ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "worksheet_types": [
            "cloze", "word_bank", "matching",
            "sentence_builder", "reading_comprehension",
        ],
        "word_types": ["event", "person", "place", "date", "vocabulary", "open"],
        "icon": "\U0001F3DB",  # 🏛
    },
    "Geography": {
        "curriculum": GEOGRAPHY_CURRICULUM,
        "years": ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "worksheet_types": [
            "cloze", "word_bank", "matching",
            "sentence_builder", "reading_comprehension",
        ],
        "word_types": ["place", "feature", "process", "climate", "vocabulary", "open"],
        "icon": "\U0001F30D",  # 🌍
    },
    "Computing": {
        "curriculum": COMPUTING_CURRICULUM,
        "years": ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "worksheet_types": [
            "cloze", "word_bank", "matching",
            "sentence_builder", "reading_comprehension",
        ],
        "word_types": ["algorithm", "data", "hardware", "software", "vocabulary", "open"],
        "icon": "\U0001F4BB",  # 💻
    },
    "Languages": {
        "curriculum": LANGUAGES_CURRICULUM,
        "years": ["Year 3", "Year 4", "Year 5", "Year 6"],
        "worksheet_types": [
            "cloze", "word_bank", "matching",
            "sentence_builder", "reading_comprehension",
        ],
        "word_types": ["noun", "verb", "adjective", "phrase", "vocabulary", "open"],
        "icon": "\U0001F1EB\U0001F1F7",  # 🇫🇷
    },
}


# Display names for worksheet types (used in UI dropdowns)
WORKSHEET_TYPE_DISPLAY = {
    "cloze": "\U0001F4DD Cloze Passage (Fill in the Blanks)",
    "word_bank": "\U0001F4DA Word Bank Activities",
    "matching": "\U0001F517 Matching / Connecting",
    "sentence_builder": "\U0001F3D7 Sentence Builder",
    "reading_comprehension": "\U0001F4D6 Reading Comprehension",
    "problem_solving": "\U0001F9E9 Problem Solving (Word Problems)",
    "calculation_practice": "\U0001F522 Calculation Practice",
    "investigation": "\U0001F52C Investigation Planner",
}

# Map display names back to keys
WORKSHEET_TYPE_KEY_MAP = {v: k for k, v in WORKSHEET_TYPE_DISPLAY.items()}
