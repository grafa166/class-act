"""
Shared font, palette, word-type marks and visual themes.

**Arial, black and blue** — decided 2026-09-01, applying to lesson plans and
worksheets alike. Two things went with that decision, and only the first is
obvious.

The six-colour word-type scheme is retired. It never did the job it was there
for: a colour distinction is gone the moment a sheet goes through the mono
photocopier in the corridor, and it was never available to a colour-blind
child at all. **The symbols and the labels stay** — they are what actually
carried the meaning, they survive a photocopier, and they are readable aloud.
So every entry below keeps its `symbol` and its `label`, and the three colour
keys are now the same everywhere: the dict shape is unchanged so no generator
had to move, and there is exactly one palette.

The themes keep their names, icons and section words — *Mission*, *Captain's
Log*, the rocket. That is language, and it is the part a Year 3 class responds
to. What they lose is seven separate palettes.

`FONT_NAME` was Comic Sans and is read by nine call sites. The joined
handwriting font used elsewhere in school is deliberately not offered
anywhere: children still decoding, and SEND children in particular, cannot
read it.
"""

from docx.shared import RGBColor

FONT_NAME = 'Arial'

# ─── The palette ───────────────────────────────────────────────────────────────
#
# Black and blue. Every colour any generator paints is one of these five, and
# `tests/test_worksheet_typography.py` renders all ten worksheet types and
# holds them to it.

INK_HEX = '000000'
BLUE_HEX = '14448C'
BLUE_SOFT_HEX = '4A72B5'
BLUE_FILL_HEX = 'F2F6FC'
RULE_HEX = 'C9D2DC'
PAPER_HEX = 'FFFFFF'

PALETTE = frozenset({INK_HEX, BLUE_HEX, BLUE_SOFT_HEX, BLUE_FILL_HEX, RULE_HEX, PAPER_HEX})

INK = RGBColor(0x00, 0x00, 0x00)
BLUE = RGBColor(0x14, 0x44, 0x8C)
BLUE_SOFT = RGBColor(0x4A, 0x72, 0xB5)


# ─── Colour Constants ──────────────────────────────────────────────────────────

COLOURS = {
    'title_bg': BLUE_FILL_HEX,
    'title_border': BLUE_HEX,
    'title_text': BLUE,
    'reminder_bg': BLUE_FILL_HEX,
    'reminder_border': BLUE_HEX,
    'reminder_text': BLUE,
    'criteria_bg': BLUE_FILL_HEX,
    'criteria_border': BLUE_HEX,
    'criteria_text': BLUE,
    'grey_text': INK,
    'hint_text': BLUE_SOFT,
    'black': INK,
    'white': RGBColor(0xFF, 0xFF, 0xFF),
}

# ─── Word Type Marks ─────────────────────────────────────────────────────────
# Each word type has a symbol and a label. The three colour keys are the same
# for every type -- kept only so the generators' shape did not have to change.

WORD_TYPES = {
    'time': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u23F0',   # ⏰
        'label': 'When?',
    },
    'adjective': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u2B50',   # ⭐
        'label': 'Describing word',
    },
    'verb': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u26A1',   # ⚡
        'label': 'Doing word',
    },
    'noun': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u25CF',   # ●
        'label': 'Naming word',
    },
    'name': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u2605',   # ★
        'label': 'Name',
    },
    'open': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u270D',   # ✍
        'label': 'Your idea',
    },
    'adverb': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u27A1',   # ➡
        'label': 'How word',
    },
    'connective': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u26D3',   # ⛓
        'label': 'Joining word',
    },
    'preposition': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u2194',   # ↔
        'label': 'Position word',
    },
    'punctuation': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u2702',   # ✂
        'label': 'Punctuation',
    },
    # ─── Maths Word Types ────────────────────────────────────────────────────
    'operation': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u2795',   # ➕
        'label': 'Operation',
    },
    'shape': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u25B3',   # △
        'label': 'Shape',
    },
    'measure': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\U0001F4CF',  # 📏
        'label': 'Measurement',
    },
    'number': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '#',
        'label': 'Number',
    },
    'vocabulary': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        # Was a star, like 'adjective'. With the colours gone the symbol is
        # the whole distinction inline, and Languages offers both at once.
        'symbol': '\U0001F511',   # 🔑
        'label': 'Key Word',
    },
    # ─── Science Word Types ──────────────────────────────────────────────────
    'process': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u2699',   # ⚙
        'label': 'Process',
    },
    'equipment': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\U0001F52C',  # 🔬
        'label': 'Equipment',
    },
    'organism': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\U0001F331',  # 🌱
        'label': 'Living Thing',
    },
    'material': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\U0001F9F1',  # 🧱
        'label': 'Material',
    },
    # ─── History Word Types ──────────────────────────────────────────────────
    'event': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\U0001F4C5',  # 📅
        'label': 'Event',
    },
    'person': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\U0001F464',  # 👤
        'label': 'Person',
    },
    'place': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\U0001F4CD',  # 📍
        'label': 'Place',
    },
    'date': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u23F3',   # ⏳
        'label': 'Date/Period',
    },
    # ─── Geography Word Types ────────────────────────────────────────────────
    'feature': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u26F0',   # ⛰
        'label': 'Feature',
    },
    'climate': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\U0001F321',  # 🌡
        'label': 'Climate/Weather',
    },
    # ─── Computing Word Types ────────────────────────────────────────────────
    'algorithm': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u2699',   # ⚙
        'label': 'Algorithm',
    },
    'data': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\U0001F4CA',  # 📊
        'label': 'Data',
    },
    'hardware': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\U0001F5A5',  # 🖥
        'label': 'Hardware',
    },
    'software': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\U0001F4BB',  # 💻
        'label': 'Software',
    },
    # ─── Languages Word Types ────────────────────────────────────────────────
    'phrase': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\U0001F4AC',  # 💬
        'label': 'Phrase',
    },
    # ─── RE (Religious Education) Word Types ─────────────────────────────────
    'scripture': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\U0001F4D6',  # 📖
        'label': 'Scripture',
    },
    'sacrament': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u2721',   # ✡ (sacred symbol)
        'label': 'Sacrament',
    },
    'saint': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\u2605',   # ★
        'label': 'Saint / Holy Person',
    },
    'prayer': {
        'bg': BLUE_FILL_HEX,
        'border': RULE_HEX,
        'text': INK,
        'symbol': '\U0001F54A',  # 🕊
        'label': 'Prayer / Worship',
    },
}

# ─── CAFOD Catholic Social Teaching Animals ──────────────────────────────────
# Each of the seven principles of Catholic Social Teaching is represented
# in CAFOD's primary school resources by an animal. Used by the RE
# generators to inject the correct emoji when a principle is mentioned.

CAFOD_ANIMALS = {
    'dignity': {
        'emoji': '\U0001F42C',   # 🐬 Dolphin
        'name': 'Dolphin',
        'principle': 'Dignity of the Human Person',
        'keywords': ['dignity', 'precious', 'image of god', 'human person', 'every person'],
    },
    'community': {
        'emoji': '\U0001F418',   # 🐘 Elephant
        'name': 'Elephant',
        'principle': 'Family and Community',
        'keywords': ['family', 'community', 'parish', 'together', 'belonging'],
    },
    'solidarity': {
        'emoji': '\U0001F41D',   # 🐝 Bee
        'name': 'Bee',
        'principle': 'Solidarity',
        'keywords': ['solidarity', 'sharing', 'one human family', 'unity'],
    },
    'rights': {
        'emoji': '\U0001F981',   # 🦁 Lion
        'name': 'Lion',
        'principle': 'Rights and Responsibilities',
        'keywords': ['rights', 'responsibilities', 'justice', 'fairness', 'stand up'],
    },
    'poor': {
        'emoji': '\U0001F985',   # 🦅 Eagle
        'name': 'Eagle',
        'principle': 'Option for the Poor',
        'keywords': ['poor', 'poverty', 'vulnerable', 'those in need', 'option for the poor'],
    },
    'workers': {
        'emoji': '\U0001F427',   # 🐧 Penguin
        'name': 'Penguin',
        'principle': 'Dignity of Workers',
        'keywords': ['workers', 'work', 'fair work', 'dignity of workers', 'employment'],
    },
    'creation': {
        'emoji': '\U0001F433',   # 🐳 Whale
        'name': 'Whale',
        'principle': 'Care for God\u2019s Creation',
        'keywords': ['creation', 'environment', 'stewardship', 'earth', 'planet', 'care for'],
    },
}

# ─── Themes ────────────────────────────────────────────────────────────────────
# The name, the icon and the section words are the theme now. The colours are
# the one palette, everywhere.

THEMES = {
    'space': {
        'name': 'Space Explorer',
        'icon': '\U0001F680',  # 🚀
        'section': 'Mission',
        'reminder': "Captain's Log",
        'criteria': 'Mission Checklist',
        'header': BLUE_HEX,
        'body': BLUE_FILL_HEX,
        'accent': BLUE_SOFT_HEX,
    },
    'ocean': {
        'name': 'Ocean Adventure',
        'icon': '\U0001F30A',  # 🌊
        'section': 'Dive',
        'reminder': "Explorer's Note",
        'criteria': 'Dive Log',
        'header': BLUE_HEX,
        'body': BLUE_FILL_HEX,
        'accent': BLUE_SOFT_HEX,
    },
    'jungle': {
        'name': 'Jungle Quest',
        'icon': '\U0001F334',  # 🌴
        'section': 'Trail',
        'reminder': "Ranger's Tip",
        'criteria': 'Quest Tracker',
        'header': BLUE_HEX,
        'body': BLUE_FILL_HEX,
        'accent': BLUE_SOFT_HEX,
    },
    'time_travel': {
        'name': 'Time Traveller',
        'icon': '\u231B',  # ⏳
        'section': 'Era',
        'reminder': "Traveller's Tip",
        'criteria': 'Journey Log',
        'header': BLUE_HEX,
        'body': BLUE_FILL_HEX,
        'accent': BLUE_SOFT_HEX,
    },
    'detective': {
        'name': 'Mystery Detective',
        'icon': '\U0001F50D',  # 🔍
        'section': 'Clue',
        'reminder': "Detective's Note",
        'criteria': 'Case File',
        'header': BLUE_HEX,
        'body': BLUE_FILL_HEX,
        'accent': BLUE_SOFT_HEX,
    },
    'superhero': {
        'name': 'Superhero Academy',
        'icon': '\U0001F9B8',  # 🦸
        'section': 'Power',
        'reminder': "Hero's Hint",
        'criteria': 'Hero Checklist',
        'header': BLUE_HEX,
        'body': BLUE_FILL_HEX,
        'accent': BLUE_SOFT_HEX,
    },
    'classic': {
        'name': 'Classic',
        'icon': '\U0001F4DA',  # 📚
        'section': 'Section',
        'reminder': 'Remember',
        'criteria': 'Success Criteria',
        'header': BLUE_HEX,
        'body': BLUE_FILL_HEX,
        'accent': BLUE_SOFT_HEX,
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
