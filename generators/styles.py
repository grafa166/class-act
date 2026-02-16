"""
Shared colour constants, font settings, word type definitions, and visual themes.
Extracted and expanded from create_myth_worksheet.py.
"""

from docx.shared import RGBColor


FONT_NAME = 'Comic Sans MS'

# ─── Colour Constants ──────────────────────────────────────────────────────────

COLOURS = {
    'title_bg': 'FFF8E1',
    'title_border': 'F9A825',
    'title_text': RGBColor(0x1B, 0x3A, 0x5C),
    'reminder_bg': 'E0F2F1',
    'reminder_border': '0D7377',
    'reminder_text': RGBColor(0x0D, 0x73, 0x77),
    'criteria_bg': 'E8F5E9',
    'criteria_border': '2E7D32',
    'criteria_text': RGBColor(0x2E, 0x7D, 0x32),
    'grey_text': RGBColor(0x33, 0x33, 0x33),
    'hint_text': RGBColor(0x66, 0x66, 0x66),
    'black': RGBColor(0x00, 0x00, 0x00),
    'white': RGBColor(0xFF, 0xFF, 0xFF),
}

# ─── Word Type Colour Coding ──────────────────────────────────────────────────
# Each word type has its own colour, background, symbol, and label.
# Used in word banks AND in blank hints so children can visually match.

WORD_TYPES = {
    'time': {
        'bg': 'FFF9C4',
        'border': 'F57F17',
        'text': RGBColor(0xE6, 0x5C, 0x00),
        'symbol': '\u23F0',   # ⏰
        'label': 'When?',
    },
    'adjective': {
        'bg': 'E8F5E9',
        'border': '388E3C',
        'text': RGBColor(0x2E, 0x7D, 0x32),
        'symbol': '\u2B50',   # ⭐
        'label': 'Describing word',
    },
    'verb': {
        'bg': 'E3F2FD',
        'border': '1565C0',
        'text': RGBColor(0x15, 0x65, 0xC0),
        'symbol': '\u26A1',   # ⚡
        'label': 'Doing word',
    },
    'noun': {
        'bg': 'FFF3E0',
        'border': 'E65100',
        'text': RGBColor(0xBF, 0x36, 0x0C),
        'symbol': '\u25CF',   # ●
        'label': 'Naming word',
    },
    'name': {
        'bg': 'FCE4EC',
        'border': 'C62828',
        'text': RGBColor(0xC6, 0x28, 0x28),
        'symbol': '\u2605',   # ★
        'label': 'Name',
    },
    'open': {
        'bg': 'F3E5F5',
        'border': '7B1FA2',
        'text': RGBColor(0x6A, 0x1B, 0x9A),
        'symbol': '\u270D',   # ✍
        'label': 'Your idea',
    },
    'adverb': {
        'bg': 'E0F7FA',
        'border': '00838F',
        'text': RGBColor(0x00, 0x69, 0x78),
        'symbol': '\u27A1',   # ➡
        'label': 'How word',
    },
    'connective': {
        'bg': 'FFF8E1',
        'border': 'FF8F00',
        'text': RGBColor(0xE6, 0x6A, 0x00),
        'symbol': '\u26D3',   # ⛓
        'label': 'Joining word',
    },
    'preposition': {
        'bg': 'F1F8E9',
        'border': '558B2F',
        'text': RGBColor(0x33, 0x69, 0x1E),
        'symbol': '\u2194',   # ↔
        'label': 'Position word',
    },
    'punctuation': {
        'bg': 'ECEFF1',
        'border': '546E7A',
        'text': RGBColor(0x45, 0x5A, 0x64),
        'symbol': '\u2702',   # ✂
        'label': 'Punctuation',
    },
}

# ─── Fun Visual Themes ─────────────────────────────────────────────────────────
# Each theme transforms the look and feel of worksheets.

THEMES = {
    'space': {
        'name': 'Space Explorer',
        'icon': '\U0001F680',  # 🚀
        'section': 'Mission',
        'reminder': "Captain's Log",
        'criteria': 'Mission Checklist',
        'header': '1A237E',
        'body': 'E8EAF6',
        'accent': '7C4DFF',
    },
    'ocean': {
        'name': 'Ocean Adventure',
        'icon': '\U0001F30A',  # 🌊
        'section': 'Dive',
        'reminder': "Explorer's Note",
        'criteria': 'Dive Log',
        'header': '006064',
        'body': 'E0F7FA',
        'accent': '00BCD4',
    },
    'jungle': {
        'name': 'Jungle Quest',
        'icon': '\U0001F334',  # 🌴
        'section': 'Trail',
        'reminder': "Ranger's Tip",
        'criteria': 'Quest Tracker',
        'header': '1B5E20',
        'body': 'E8F5E9',
        'accent': '66BB6A',
    },
    'time_travel': {
        'name': 'Time Traveller',
        'icon': '\u231B',  # ⏳
        'section': 'Era',
        'reminder': "Traveller's Tip",
        'criteria': 'Journey Log',
        'header': '4A148C',
        'body': 'F3E5F5',
        'accent': 'AB47BC',
    },
    'detective': {
        'name': 'Mystery Detective',
        'icon': '\U0001F50D',  # 🔍
        'section': 'Clue',
        'reminder': "Detective's Note",
        'criteria': 'Case File',
        'header': 'B71C1C',
        'body': 'FFEBEE',
        'accent': 'EF5350',
    },
    'superhero': {
        'name': 'Superhero Academy',
        'icon': '\U0001F9B8',  # 🦸
        'section': 'Power',
        'reminder': "Hero's Hint",
        'criteria': 'Hero Checklist',
        'header': 'E65100',
        'body': 'FFF3E0',
        'accent': 'FF9800',
    },
    'classic': {
        'name': 'Classic',
        'icon': '\U0001F4DA',  # 📚
        'section': 'Section',
        'reminder': 'Remember',
        'criteria': 'Success Criteria',
        'header': '1565C0',
        'body': 'E3F2FD',
        'accent': '42A5F5',
    },
}

# ─── Differentiation Settings ──────────────────────────────────────────────────

DIFF_LEVELS = {
    'developing': {
        'label': 'Developing (Maximum Support)',
        'font_size': 16,
        'line_spacing': 32,
        'padding': 150,
    },
    'expected': {
        'label': 'Expected (Moderate Support)',
        'font_size': 14,
        'line_spacing': 26,
        'padding': 120,
    },
    'greater_depth': {
        'label': 'Greater Depth (Minimal Support)',
        'font_size': 12,
        'line_spacing': 22,
        'padding': 100,
    },
}

# ─── Year Group Age Ranges ─────────────────────────────────────────────────────

YEAR_AGES = {
    'Year 1': '5-6',
    'Year 2': '6-7',
    'Year 3': '7-8',
    'Year 4': '8-9',
    'Year 5': '9-10',
    'Year 6': '10-11',
}
