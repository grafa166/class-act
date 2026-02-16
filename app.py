"""
UK National Curriculum Lesson Planner & Worksheet Generator
A Streamlit app that generates themed, differentiated, dual-coded worksheets
for Primary School English (Year 1-6) using Claude AI.
"""

import io
import zipfile
import streamlit as st

from curriculum.english import ENGLISH_CURRICULUM
from generators.styles import THEMES, DIFF_LEVELS, YEAR_AGES
from llm.client import generate_worksheet_content
from llm.prompts import get_prompt
from generators.cloze import generate_cloze_worksheet
from generators.word_bank import generate_word_bank_worksheet
from generators.matching import generate_matching_worksheet
from generators.sentence_builder import generate_sentence_builder_worksheet
from generators.reading_comprehension import generate_reading_comprehension_worksheet


# ─── Page Configuration ────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Lesson Planner",
    page_icon="\U0001F3EB",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Session State Initialisation ─────────────────────────────────────────────

if 'generated_content' not in st.session_state:
    st.session_state.generated_content = {}
if 'generation_params' not in st.session_state:
    st.session_state.generation_params = {}
if 'preview_ready' not in st.session_state:
    st.session_state.preview_ready = False
if 'regenerate_requested' not in st.session_state:
    st.session_state.regenerate_requested = False

# ─── Custom CSS ────────────────────────────────────────────────────────────────

# Layer 1: Google Fonts — loaded via <link> (not @import) so it works mid-document
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

# Layer 2 + 3: Streamlit DOM overrides + custom components
st.markdown("""
<style>
    /* ═══════════════════════════════════════════════════════════════════
       LAYER 1: DESIGN TOKENS (CSS Custom Properties)
       ═══════════════════════════════════════════════════════════════════ */
    :root {
        --font: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        --primary: #1565C0;
        --primary-dark: #0D2137;
        --primary-light: #E3F2FD;
        --success: #2E7D32;
        --success-light: #E8F5E9;
        --warning: #E65100;
        --warning-light: #FFF3E0;
        --text-primary: #1F2937;
        --text-secondary: #6B7280;
        --text-muted: #9CA3AF;
        --border: #E5E7EB;
        --surface: #F8FAFC;
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.08);
        --shadow-md: 0 4px 12px rgba(0,0,0,0.1);
        --shadow-lg: 0 8px 24px rgba(0,0,0,0.12);
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
    }

    /* ═══════════════════════════════════════════════════════════════════
       LAYER 2: STREAMLIT DOM OVERRIDES
       ═══════════════════════════════════════════════════════════════════ */

    /* ── Global Typography ────────────────────────────────────────────── */
    html, body, .stApp, [data-testid="stAppViewContainer"],
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown h1,
    .stMarkdown h2, .stMarkdown h3, .stMarkdown h4,
    .stSelectbox label, .stTextInput label, .stTextArea label,
    .stCheckbox label, .stRadio label,
    div.stButton > button, .stDownloadButton > button,
    .stCaption, [data-testid="stSidebar"] p {
        font-family: var(--font) !important;
    }

    /* ── Main Container ──────────────────────────────────────────────── */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 1100px !important;
    }

    /* ── Hide Streamlit Chrome ────────────────────────────────────────── */
    header[data-testid="stHeader"] {
        background: transparent !important;
        backdrop-filter: none !important;
    }
    #MainMenu, footer, [data-testid="stDecoration"] {
        display: none !important;
    }

    /* ── Sidebar ─────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F0F4F8 0%, #E2E8F0 100%) !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.25rem !important;
    }
    [data-testid="stSidebar"] hr {
        margin: 0.5rem 0 !important;
        border-color: rgba(21,101,192,0.1) !important;
    }
    [data-testid="stSidebar"] h2 {
        font-family: var(--font) !important;
        color: var(--primary-dark) !important;
        font-size: 1.3rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }
    [data-testid="stSidebar"] h3 {
        font-family: var(--font) !important;
        color: var(--primary-dark) !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        margin-bottom: 0.25rem !important;
        padding-bottom: 0.35rem !important;
        border-bottom: 2px solid rgba(21,101,192,0.15) !important;
    }
    /* Sidebar inputs — rounded corners, subtle borders, blue focus */
    [data-testid="stSidebar"] .stSelectbox > div > div,
    [data-testid="stSidebar"] .stTextInput > div > div > input,
    [data-testid="stSidebar"] .stTextArea > div > div > textarea {
        font-family: var(--font) !important;
        border-radius: var(--radius-sm) !important;
        border-color: #CBD5E1 !important;
        font-size: 0.9rem !important;
    }
    [data-testid="stSidebar"] .stSelectbox > div > div:focus-within,
    [data-testid="stSidebar"] .stTextInput > div > div > input:focus,
    [data-testid="stSidebar"] .stTextArea > div > div > textarea:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(21,101,192,0.12) !important;
    }
    /* Sidebar generate button */
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        font-family: var(--font) !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        padding: 0.7rem 1rem !important;
        border-radius: 10px !important;
        letter-spacing: 0.02em !important;
        box-shadow: 0 3px 12px rgba(21,101,192,0.35) !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        box-shadow: 0 5px 18px rgba(21,101,192,0.45) !important;
        transform: translateY(-1px) !important;
    }
    /* Sidebar caption text */
    [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small {
        font-family: var(--font) !important;
        color: var(--text-secondary) !important;
    }

    /* ── Buttons (main area) ─────────────────────────────────────────── */
    .stButton > button, .stDownloadButton > button {
        font-family: var(--font) !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.25rem !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button[kind="primary"],
    .stDownloadButton > button[kind="primary"] {
        box-shadow: 0 2px 8px rgba(21,101,192,0.3) !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stDownloadButton > button[kind="primary"]:hover {
        box-shadow: 0 4px 16px rgba(21,101,192,0.4) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Expanders ───────────────────────────────────────────────────── */
    details[data-testid="stExpander"] {
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        box-shadow: var(--shadow-sm) !important;
        margin-bottom: 0.5rem !important;
        overflow: hidden !important;
    }
    details[data-testid="stExpander"] summary {
        font-family: var(--font) !important;
        font-weight: 600 !important;
        color: var(--primary-dark) !important;
        padding: 0.75rem 1rem !important;
    }

    /* ── Progress bar ────────────────────────────────────────────────── */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #1565C0, #42A5F5) !important;
        border-radius: var(--radius-sm) !important;
    }

    /* ── Streamlit alerts (st.info, st.success, st.error) ────────────── */
    .stAlert {
        border-radius: var(--radius-sm) !important;
        font-family: var(--font) !important;
    }

    /* ═══════════════════════════════════════════════════════════════════
       LAYER 3: CUSTOM COMPONENTS
       ═══════════════════════════════════════════════════════════════════ */

    /* ── Professional Header Banner ──────────────────────────────────── */
    .app-header {
        font-family: var(--font);
        background: linear-gradient(135deg, #0D2137 0%, #1565C0 60%, #1E88E5 100%);
        padding: 2.5rem 2.5rem 2rem;
        border-radius: var(--radius-lg);
        margin: -0.5rem 0 1.5rem;
        color: white;
        box-shadow: 0 4px 24px rgba(13,33,55,0.3);
        position: relative;
        overflow: hidden;
    }
    .app-header::before {
        content: '';
        position: absolute;
        top: -60%; right: -15%;
        width: 500px; height: 500px;
        background: radial-gradient(circle, rgba(255,255,255,0.07) 0%, transparent 65%);
        border-radius: 50%;
    }
    .app-header::after {
        content: '';
        position: absolute;
        bottom: -40%; left: -10%;
        width: 300px; height: 300px;
        background: radial-gradient(circle, rgba(30,136,229,0.15) 0%, transparent 70%);
        border-radius: 50%;
    }
    .app-header h1 {
        font-family: var(--font) !important;
        color: white !important;
        font-size: 2rem !important;
        font-weight: 800 !important;
        margin: 0 !important;
        line-height: 1.3 !important;
        position: relative;
        text-shadow: 0 2px 4px rgba(0,0,0,0.15);
        letter-spacing: -0.02em !important;
    }
    .app-header p {
        font-family: var(--font) !important;
        color: rgba(255,255,255,0.8) !important;
        font-size: 1.05rem !important;
        margin: 0.5rem 0 0 !important;
        position: relative;
        font-weight: 400;
    }

    /* ── Stat Cards ──────────────────────────────────────────────────── */
    .stat-card {
        font-family: var(--font);
        background: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 1rem 1.25rem;
        border-left: 4px solid var(--primary);
        box-shadow: var(--shadow-sm);
        transition: box-shadow 0.2s ease, transform 0.2s ease;
    }
    .stat-card:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-1px);
    }
    .stat-card-green { border-left-color: var(--success) !important; }
    .stat-card-amber { border-left-color: var(--warning) !important; }
    .stat-card-label {
        font-family: var(--font);
        font-size: 0.65rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
        margin-bottom: 0.3rem;
    }
    .stat-card-value {
        font-family: var(--font);
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--text-primary);
        line-height: 1.4;
    }

    /* ── Section Cards ───────────────────────────────────────────────── */
    .section-card {
        font-family: var(--font);
        background: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 1.5rem 1.75rem;
        box-shadow: var(--shadow-sm);
        margin-bottom: 0.75rem;
    }
    .section-card h4 {
        font-family: var(--font) !important;
        color: var(--primary-dark) !important;
        margin: 0 0 0.75rem !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
    }

    /* ── Pill Badges ─────────────────────────────────────────────────── */
    .badge {
        font-family: var(--font);
        display: inline-block;
        padding: 0.15rem 0.55rem;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        vertical-align: middle;
    }
    .badge-blue { background: var(--primary-light); color: var(--primary); }
    .badge-green { background: var(--success-light); color: var(--success); }
    .badge-amber { background: var(--warning-light); color: var(--warning); }

    /* ── Theme Cards ─────────────────────────────────────────────────── */
    .theme-card {
        font-family: var(--font);
        padding: 0.75rem 0.5rem;
        border-radius: var(--radius-md);
        text-align: center;
        font-weight: 700;
        font-size: 0.85rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        transition: all 0.2s ease;
    }
    .theme-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 14px rgba(0,0,0,0.2);
    }

    /* ── Feature Cards (Welcome Page) ────────────────────────────────── */
    .feature-card {
        font-family: var(--font);
        background: linear-gradient(160deg, #FFFFFF, var(--surface));
        border: 1px solid var(--border);
        border-top: 3px solid var(--primary);
        border-radius: var(--radius-md);
        padding: 1.75rem 1.25rem;
        text-align: center;
        height: 100%;
        box-shadow: var(--shadow-sm);
        transition: all 0.2s ease;
    }
    .feature-card:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-3px);
        border-top-color: #1E88E5;
    }
    .feature-card .fc-icon { font-size: 2.5rem; margin-bottom: 0.5rem; display: block; }
    .feature-card h4 {
        font-family: var(--font) !important;
        color: var(--primary-dark) !important;
        margin: 0.5rem 0 0.4rem !important;
        font-size: 1.05rem !important;
        font-weight: 700 !important;
    }
    .feature-card p {
        font-family: var(--font) !important;
        color: var(--text-secondary) !important;
        font-size: 0.85rem !important;
        margin: 0 !important;
        line-height: 1.5 !important;
    }

    /* ── Step Indicators ─────────────────────────────────────────────── */
    .step-row {
        display: flex;
        align-items: center;
        margin-bottom: 0.85rem;
        padding: 0.4rem 0;
    }
    .step-row:last-child { margin-bottom: 0; }
    .step-number {
        font-family: var(--font);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 32px; height: 32px;
        background: linear-gradient(135deg, var(--primary), #1E88E5);
        color: white;
        border-radius: 50%;
        font-weight: 800;
        font-size: 0.85rem;
        margin-right: 0.85rem;
        flex-shrink: 0;
        box-shadow: 0 2px 8px rgba(21,101,192,0.35);
    }
    .step-text {
        font-family: var(--font);
        color: var(--text-primary) !important;
        font-size: 0.95rem;
        line-height: 1.4;
    }

    /* ── Generation Status ───────────────────────────────────────────── */
    .generating {
        font-family: var(--font);
        padding: 1rem 1.25rem;
        background: linear-gradient(90deg, var(--primary-light), #BBDEFB);
        border-left: 4px solid var(--primary);
        border-radius: var(--radius-sm);
        margin: 0.75rem 0;
        font-weight: 500;
        animation: pulse 2s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }

    /* ── Download Section ────────────────────────────────────────────── */
    .download-card {
        font-family: var(--font);
        background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
        border: 2px solid #43A047;
        border-radius: var(--radius-lg);
        padding: 1.75rem;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 2px 12px rgba(46,125,50,0.15);
    }
    .download-card h4 {
        font-family: var(--font) !important;
        color: #1B5E20 !important;
        margin: 0 0 0.4rem !important;
        font-size: 1.2rem !important;
        font-weight: 700 !important;
    }
    .download-card p {
        font-family: var(--font) !important;
        color: var(--success) !important;
        font-size: 0.9rem !important;
        margin: 0 !important;
    }

    /* ── Footer ──────────────────────────────────────────────────────── */
    .app-footer {
        font-family: var(--font);
        text-align: center;
        color: var(--text-muted);
        font-size: 0.8rem;
        padding: 1.25rem 0 0.5rem;
        border-top: 1px solid var(--border);
        margin-top: 2rem;
        letter-spacing: 0.01em;
    }
</style>
""", unsafe_allow_html=True)


# ─── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## \U0001F3EB Lesson Planner")
    st.markdown("---")

    # Year Group
    year_groups = list(ENGLISH_CURRICULUM.keys())
    year_group = st.selectbox(
        "\U0001F393 Year Group",
        year_groups,
        index=2,  # Default to Year 3
        help="Select the year group for this worksheet",
    )

    # Subject (English only for now)
    st.selectbox(
        "\U0001F4D6 Subject",
        ["English"],
        disabled=True,
        help="More subjects coming soon!",
    )

    # Strand
    strands = list(ENGLISH_CURRICULUM[year_group].keys())
    strand = st.selectbox(
        "\U0001F4CB Strand",
        strands,
        help="Select the English strand",
    )

    # Topic
    topics = ENGLISH_CURRICULUM[year_group][strand]["topics"]
    topic = st.selectbox(
        "\U0001F4CC Topic",
        topics,
        help="Select the specific topic",
    )

    # Get objectives for display
    objectives = ENGLISH_CURRICULUM[year_group][strand]["objectives"]
    objective_text = objectives[0] if objectives else ""

    # Custom Topic Override
    st.markdown("---")
    st.markdown("### \u270F\uFE0F Custom Topic (Optional)")
    custom_topic = st.text_input(
        "Override with your own topic",
        value="",
        placeholder="e.g. The Great Fire of London",
        help="Type a custom topic to override the curriculum dropdown. Leave blank to use the selected topic.",
    )
    custom_objective = st.text_area(
        "Custom learning objective",
        value="",
        placeholder="e.g. Pupils can use descriptive language to write about historical events",
        help="Provide your own objective, or leave blank for the curriculum default.",
        height=80,
    )

    st.markdown("---")

    # Worksheet Type
    worksheet_types = {
        "Cloze Passage": {
            "icon": "\u270D\uFE0F",
            "desc": "Fill-in-the-blank passages with scaffolded support",
        },
        "Word Bank Activity": {
            "icon": "\U0001F4DA",
            "desc": "Vocabulary sheets with colour-coded word types",
        },
        "Matching Activity": {
            "icon": "\U0001F517",
            "desc": "Connect terms to definitions with visual scaffolding",
        },
        "Sentence Builder": {
            "icon": "\U0001F9E9",
            "desc": "Construct sentences from word/phrase cards",
        },
        "Reading Comprehension": {
            "icon": "\U0001F4D6",
            "desc": "Passage with tiered comprehension questions",
        },
    }

    worksheet_type = st.selectbox(
        "\U0001F4DD Worksheet Type",
        list(worksheet_types.keys()),
        format_func=lambda x: f"{worksheet_types[x]['icon']} {x}",
    )
    st.caption(worksheet_types[worksheet_type]["desc"])

    # Theme
    theme_options = {k: f"{v['icon']} {v['name']}" for k, v in THEMES.items()}
    theme_key = st.selectbox(
        "\U0001F3A8 Theme",
        list(theme_options.keys()),
        format_func=lambda x: theme_options[x],
        help="Choose a fun visual theme for the worksheet",
    )

    st.markdown("---")

    # Differentiation
    st.markdown("### Differentiation")
    generate_all = st.checkbox("Generate all 3 levels", value=True)

    if not generate_all:
        level_options = {k: v['label'] for k, v in DIFF_LEVELS.items()}
        selected_level = st.selectbox(
            "Select level",
            list(level_options.keys()),
            format_func=lambda x: level_options[x],
            index=1,
        )

    st.markdown("---")

    # Accessibility Options
    st.markdown("### \u267F Accessibility")
    extra_spacing = st.checkbox(
        "Extra-large spacing",
        value=False,
        help="Increases line height and paragraph gaps",
    )
    eal_glossary = st.checkbox(
        "EAL glossary space",
        value=False,
        help="Adds an empty box for first-language translations",
    )

    st.markdown("---")

    # Teacher Tools
    st.markdown("### \U0001F4CB Teacher Tools")
    include_answer_key = st.checkbox(
        "Include Answer Key",
        value=False,
        help="Generate a filled-in answer key alongside each student worksheet",
    )

    st.markdown("---")

    # Generate Button
    generate_btn = st.button(
        "\U0001F3A8 Generate Worksheets",
        use_container_width=True,
        type="primary",
        key="generate_btn",
    )


# ─── Main Content Area ─────────────────────────────────────────────────────────

# Resolve effective topic and objective (custom overrides curriculum)
effective_topic = custom_topic.strip() if custom_topic.strip() else f"{strand} - {topic}"
effective_objective = custom_objective.strip() if custom_objective.strip() else objective_text

# Header — professional gradient banner
theme = THEMES[theme_key]
st.markdown(
    f'<div class="app-header">'
    f'<h1>{theme["icon"]} UK National Curriculum Worksheet Generator</h1>'
    f'<p>Generate creative, differentiated, dual-coded worksheets powered by AI</p>'
    f'</div>',
    unsafe_allow_html=True,
)

# Stat cards row
display_topic = custom_topic.strip() if custom_topic.strip() else f"{strand} \u2192 {topic}"
topic_card_class = "stat-card stat-card-amber" if custom_topic.strip() else "stat-card stat-card-green"
topic_badge = '<span class="badge badge-amber">Custom</span> ' if custom_topic.strip() else ''

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        '<div class="stat-card">'
        '<div class="stat-card-label">Year Group</div>'
        f'<div class="stat-card-value">{year_group} &middot; English</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f'<div class="{topic_card_class}">'
        '<div class="stat-card-label">Topic</div>'
        f'<div class="stat-card-value">{topic_badge}{display_topic}</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        '<div class="stat-card">'
        '<div class="stat-card-label">Worksheet</div>'
        f'<div class="stat-card-value">{worksheet_types[worksheet_type]["icon"]} {worksheet_type} '
        f'<span class="badge badge-blue">{theme["icon"]} {theme["name"]}</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )

# Learning Objectives
with st.expander("\U0001F4CB Curriculum Objectives", expanded=False):
    if custom_objective.strip():
        st.markdown(f"**Custom:** {custom_objective.strip()}")
        st.markdown("---")
    for obj in objectives:
        st.markdown(f"- {obj}")

# Theme Preview
with st.expander(f"{theme['icon']} Theme Preview: {theme['name']}", expanded=False):
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        st.markdown(
            f'<div class="theme-card" style="background: #{theme["header"]}; color: white;">'
            f'{theme["icon"]} {theme["section"]} 1: Header</div>',
            unsafe_allow_html=True,
        )
    with tc2:
        st.markdown(
            f'<div class="theme-card" style="background: #{theme["body"]}; color: #{theme["header"]};">'
            f'{theme["reminder"]}: Tip text here</div>',
            unsafe_allow_html=True,
        )
    with tc3:
        st.markdown(
            f'<div class="theme-card" style="background: #E8F5E9; color: #2E7D32;">'
            f'{theme["icon"]} {theme["criteria"]}</div>',
            unsafe_allow_html=True,
        )

# ─── Maps ─────────────────────────────────────────────────────────────────────

WORKSHEET_TYPE_MAP = {
    "Cloze Passage": "cloze",
    "Word Bank Activity": "word_bank",
    "Matching Activity": "matching",
    "Sentence Builder": "sentence_builder",
    "Reading Comprehension": "reading_comprehension",
}

GENERATOR_MAP = {
    "cloze": generate_cloze_worksheet,
    "word_bank": generate_word_bank_worksheet,
    "matching": generate_matching_worksheet,
    "sentence_builder": generate_sentence_builder_worksheet,
    "reading_comprehension": generate_reading_comprehension_worksheet,
}


# ─── Preview Helpers ──────────────────────────────────────────────────────────


def _pieces_to_preview_text(pieces):
    """Convert a pieces array to readable preview text with blanks shown inline."""
    parts = []
    for piece in pieces:
        if piece.get('type') == 'text':
            parts.append(piece.get('text', ''))
        elif piece.get('type') == 'blank':
            hint = piece.get('hint', '')
            choices = piece.get('choices', [])
            answer = piece.get('answer', '')
            if answer:
                parts.append(f"**[{answer}]**")
            elif choices:
                parts.append(f"[{'/'.join(choices)}]")
            elif hint:
                parts.append(f"[__{hint}__]")
            else:
                parts.append(f"[__{'_' * 8}__]")
    return ''.join(parts)


def render_content_preview(content, ws_type):
    """Render a structured Streamlit preview of LLM-generated content."""
    st.markdown(f"**Title:** {content.get('title', 'Untitled')}")

    if ws_type == 'cloze':
        for section in content.get('sections', []):
            st.markdown(f"**{section['title']}**")
            if section.get('reminder'):
                st.caption(f"Reminder: {section['reminder']}")
            for para in section.get('paragraphs', []):
                st.markdown(_pieces_to_preview_text(para))
        if content.get('word_bank'):
            st.markdown("**Word Bank:**")
            for cat in content['word_bank']:
                words = [w['word'] if isinstance(w, dict) else w for w in cat.get('words', [])]
                st.markdown(f"- {cat.get('label', '')}: {', '.join(words)}")

    elif ws_type == 'word_bank':
        if content.get('categories'):
            st.markdown("**Categories:**")
            for cat in content['categories']:
                words = [w['word'] if isinstance(w, dict) else w for w in cat.get('words', [])]
                st.markdown(f"- {cat.get('label', '')}: {', '.join(words)}")
        for activity in content.get('activities', []):
            st.markdown(f"**Activity:** {activity.get('title', '')}")
            for sentence in activity.get('sentences', []):
                pieces = sentence.get('pieces', sentence) if isinstance(sentence, dict) else sentence
                if isinstance(pieces, list):
                    st.markdown(_pieces_to_preview_text(pieces))

    elif ws_type == 'matching':
        for activity in content.get('activities', []):
            st.markdown(f"**{activity.get('title', '')}**")
            for pair in activity.get('pairs', []):
                st.markdown(f"- {pair['left']} \u2192 {pair['right']}")
        bonus = content.get('bonus_activity')
        if bonus:
            st.markdown(f"**Bonus:** {bonus.get('title', '')} \u2014 {bonus.get('instructions', '')}")

    elif ws_type == 'sentence_builder':
        for exercise in content.get('exercises', []):
            st.markdown(f"**{exercise.get('title', '')}**")
            parts = [p['part'] for p in exercise.get('sentence_parts', [])]
            st.markdown(f"Parts: {' | '.join(parts)}")
            if exercise.get('correct_sentence'):
                st.caption(f"Answer: {exercise['correct_sentence']}")
        ext = content.get('extension')
        if ext:
            st.markdown(f"**Extension:** {ext.get('title', '')} \u2014 {ext.get('instructions', '')}")

    elif ws_type == 'reading_comprehension':
        passage = content.get('passage', {})
        st.markdown(f"**Passage:** {passage.get('title', '')}")
        text = passage.get('text', '')
        preview_text = text[:400] + '...' if len(text) > 400 else text
        st.markdown(preview_text)
        if content.get('vocabulary'):
            st.markdown("**Key Vocabulary:**")
            for v in content['vocabulary']:
                st.markdown(f"- **{v.get('word', '')}** ({v.get('word_type', '')}): {v.get('definition', '')}")
        st.markdown("**Questions:**")
        for q in content.get('questions', []):
            marks = q.get('marks', 1)
            st.markdown(
                f"{q.get('number', '?')}. [{q.get('question_type', '')}] "
                f"{q.get('question', '')} ({marks} mark{'s' if marks > 1 else ''})"
            )

    # Success criteria (common to all types)
    criteria = content.get('success_criteria', [])
    if criteria:
        st.markdown("**Success Criteria:**")
        for c in criteria:
            st.markdown(f"- {c}")


def generate_for_level(ws_type_key, content, level, theme_key, objective_text,
                       extra_spacing, eal_glossary, show_answers=False):
    """Generate a single worksheet for one differentiation level."""
    generator = GENERATOR_MAP[ws_type_key]
    return generator(
        content=content,
        theme_key=theme_key,
        level=level,
        objective=objective_text,
        extra_spacing=extra_spacing,
        eal_glossary=eal_glossary,
        show_answers=show_answers,
    )


def build_and_download(params):
    """Phase 3: Build Word documents from stored content and show download buttons."""
    generated_files = {}

    progress_bar = st.progress(0)
    status_text = st.empty()
    items = list(st.session_state.generated_content.items())
    total = len(items) * (2 if params['include_answer_key'] else 1)
    step = 0

    for level, content in items:
        level_label = DIFF_LEVELS[level]['label']

        # Build student worksheet
        status_text.markdown(
            f'<div class="generating">\U0001F4C4 Building <b>{level_label}</b> worksheet...</div>',
            unsafe_allow_html=True,
        )
        step += 1
        progress_bar.progress(step / total)

        doc_buffer = generate_for_level(
            params['ws_type_key'], content, level,
            params['theme_key'], params['effective_objective'],
            params['extra_spacing'], params['eal_glossary'],
        )
        if doc_buffer:
            filename = (
                f"{params['year_group']}_{params['topic_for_filename']}"
                f"_{params['worksheet_type']}_{level}.docx"
            ).replace(" ", "_")
            generated_files[level] = {
                'buffer': doc_buffer,
                'filename': filename,
                'label': level_label,
            }

        # Build answer key if requested
        if params['include_answer_key']:
            status_text.markdown(
                f'<div class="generating">\U0001F4CB Building <b>{level_label}</b> answer key...</div>',
                unsafe_allow_html=True,
            )
            step += 1
            progress_bar.progress(step / total)

            answer_buffer = generate_for_level(
                params['ws_type_key'], content, level,
                params['theme_key'], params['effective_objective'],
                params['extra_spacing'], params['eal_glossary'],
                show_answers=True,
            )
            if answer_buffer:
                answer_filename = (
                    f"{params['year_group']}_{params['topic_for_filename']}"
                    f"_{params['worksheet_type']}_{level}_ANSWER_KEY.docx"
                ).replace(" ", "_")
                generated_files[f'{level}_answer'] = {
                    'buffer': answer_buffer,
                    'filename': answer_filename,
                    'label': f'{level_label} - Answer Key',
                }

    progress_bar.progress(1.0)
    status_text.empty()

    if not generated_files:
        st.error("No worksheets were generated. Please check your settings and try again.")
        return

    # Download section — professional card
    st.markdown(
        f'<div class="download-card">'
        f'<h4>\u2713 Generated {len(generated_files)} Document{"s" if len(generated_files) != 1 else ""} Successfully</h4>'
        f'<p>Your worksheets are ready to download</p></div>',
        unsafe_allow_html=True,
    )

    if len(generated_files) > 1:
        # Create ZIP of all files
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_info in generated_files.values():
                file_info['buffer'].seek(0)
                zf.writestr(file_info['filename'], file_info['buffer'].read())
        zip_buffer.seek(0)

        zip_filename = (
            f"{params['year_group']}_{params['topic_for_filename']}"
            f"_{params['worksheet_type']}_All.zip"
        ).replace(" ", "_")
        st.download_button(
            label=f"\U0001F4E6 Download All ({len(generated_files)} documents as ZIP)",
            data=zip_buffer,
            file_name=zip_filename,
            mime="application/zip",
            use_container_width=True,
            type="primary",
            key="download_all",
        )

        st.markdown("**Or download individually:**")

    # Individual download buttons — group into rows of 3
    file_items = list(generated_files.items())
    for row_start in range(0, len(file_items), 3):
        row_items = file_items[row_start:row_start + 3]
        cols = st.columns(len(row_items))
        for col, (key, file_info) in zip(cols, row_items):
            with col:
                file_info['buffer'].seek(0)
                level_icons = {
                    'developing': '\U0001F7E2',
                    'expected': '\U0001F7E1',
                    'greater_depth': '\U0001F534',
                }
                # Extract base level from key (e.g. 'expected_answer' -> 'expected')
                base_level = key.replace('_answer', '')
                icon = '\U0001F4CB' if '_answer' in key else level_icons.get(base_level, '\U0001F4C4')
                st.download_button(
                    label=f"{icon} {file_info['label']}",
                    data=file_info['buffer'],
                    file_name=file_info['filename'],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )


# ─── Generation Flow ──────────────────────────────────────────────────────────

# Phase 1: Generate content with LLM (triggered by Generate button or Regenerate)
_regenerating = st.session_state.regenerate_requested
if generate_btn or _regenerating:
    st.session_state.regenerate_requested = False

    if _regenerating and st.session_state.generation_params:
        # Regeneration — reuse stored params from last generation
        params = st.session_state.generation_params
        ws_type_key = params['ws_type_key']
        levels_to_generate = params['levels']
    else:
        # Fresh generation — build params from sidebar
        ws_type_key = WORKSHEET_TYPE_MAP[worksheet_type]
        age_range = YEAR_AGES[year_group]

        if generate_all:
            levels_to_generate = list(DIFF_LEVELS.keys())
        else:
            levels_to_generate = [selected_level]

        # Store params for later phases
        topic_for_filename = custom_topic.strip() if custom_topic.strip() else topic
        st.session_state.generation_params = {
            'ws_type_key': ws_type_key,
            'year_group': year_group,
            'effective_topic': effective_topic,
            'effective_objective': effective_objective,
            'topic_for_filename': topic_for_filename,
            'age_range': age_range,
            'theme_key': theme_key,
            'theme_name': theme['name'],
            'theme_icon': theme['icon'],
            'worksheet_type': worksheet_type,
            'extra_spacing': extra_spacing,
            'eal_glossary': eal_glossary,
            'include_answer_key': include_answer_key,
            'levels': levels_to_generate,
        }

    params = st.session_state.generation_params

    # Clear previous content
    st.session_state.generated_content = {}
    st.session_state.preview_ready = False

    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        for i, level in enumerate(levels_to_generate):
            level_label = DIFF_LEVELS[level]['label']

            status_text.markdown(
                f'<div class="generating">\U0001F916 Generating content for <b>{level_label}</b>... '
                f'(asking Claude to create {params["worksheet_type"].lower()} content)</div>',
                unsafe_allow_html=True,
            )
            progress_bar.progress((i + 1) / len(levels_to_generate))

            prompt = get_prompt(
                worksheet_type=params['ws_type_key'],
                year_group=params['year_group'],
                topic=params['effective_topic'],
                objective=params['effective_objective'],
                age_range=params['age_range'],
                theme_name=params['theme_name'],
                theme_icon=params['theme_icon'],
                level=level,
            )

            # Reading comprehension needs more tokens for passage + questions + answers
            max_tok = 6144 if params['ws_type_key'] == 'reading_comprehension' else 4096
            content = generate_worksheet_content(prompt, max_tokens=max_tok)

            if content:
                st.session_state.generated_content[level] = content
            else:
                st.error(f"Failed to generate content for {level_label}. Please try again.")

        progress_bar.progress(1.0)
        status_text.empty()

        if st.session_state.generated_content:
            st.session_state.preview_ready = True
            st.rerun()
        else:
            st.error("No content was generated. Please check your API key and try again.")

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"An error occurred: {str(e)}")
        st.info("Please check that your Anthropic API key is set correctly in the .env file.")


# Phase 2: Preview content and offer Build / Regenerate
elif st.session_state.preview_ready and st.session_state.generated_content:
    params = st.session_state.generation_params

    st.markdown(
        '<div class="section-card">'
        '<h4>\U0001F50D Content Preview</h4>'
        '<p style="color: #6B7280; font-size: 0.9rem; margin: 0;">'
        'Review the generated content below. Click <b>Build Documents</b> to create Word files, '
        'or <b>Regenerate</b> to generate new content.</p></div>',
        unsafe_allow_html=True,
    )

    for level, content in st.session_state.generated_content.items():
        level_label = DIFF_LEVELS[level]['label']
        with st.expander(
            f"{level_label}",
            expanded=(len(st.session_state.generated_content) == 1),
        ):
            render_content_preview(content, params['ws_type_key'])

    # Action buttons
    col_regen, col_build = st.columns(2)
    with col_regen:
        if st.button("\U0001F504 Regenerate", use_container_width=True, key="regenerate_btn"):
            st.session_state.preview_ready = False
            st.session_state.generated_content = {}
            st.session_state.regenerate_requested = True
            st.rerun()
    with col_build:
        if st.button("\U0001F4C4 Build Documents", use_container_width=True, type="primary", key="build_btn"):
            build_and_download(params)


# Welcome state
else:
    # Feature highlight cards
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        st.markdown(
            '<div class="feature-card">'
            '<div class="fc-icon">\U0001F3A8</div>'
            '<h4>Themed & Differentiated</h4>'
            '<p>7 visual themes &times; 3 differentiation levels for every learner</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    with fc2:
        st.markdown(
            '<div class="feature-card">'
            '<div class="fc-icon">\u2728</div>'
            '<h4>Dual-Coded</h4>'
            '<p>Colour + symbol word types for accessible, research-backed design</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    with fc3:
        st.markdown(
            '<div class="feature-card">'
            '<div class="fc-icon">\U0001F4CB</div>'
            '<h4>Teacher Tools</h4>'
            '<p>Answer keys, preview & regenerate, EAL glossary support</p>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    # How it works — step indicators
    st.markdown(
        '<div class="section-card"><h4>How It Works</h4>'
        '<div class="step-row"><span class="step-number">1</span>'
        '<span class="step-text">Configure your lesson in the sidebar &mdash; year group, strand, topic, and theme</span></div>'
        '<div class="step-row"><span class="step-number">2</span>'
        '<span class="step-text">Click <b>Generate Worksheets</b> to create content with AI</span></div>'
        '<div class="step-row"><span class="step-number">3</span>'
        '<span class="step-text">Preview and refine the generated content</span></div>'
        '<div class="step-row"><span class="step-number">4</span>'
        '<span class="step-text">Build and download your professionally formatted Word documents</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Available themes — wrapped in section card
    st.markdown('<div class="section-card"><h4>\U0001F3A8 Available Themes</h4></div>',
                unsafe_allow_html=True)
    theme_cols = st.columns(len(THEMES))
    for col, (key, t) in zip(theme_cols, THEMES.items()):
        with col:
            st.markdown(
                f'<div class="theme-card" style="background: #{t["header"]}; color: white;">'
                f'{t["icon"]}<br>{t["name"]}</div>',
                unsafe_allow_html=True,
            )

    st.markdown("")

    # Dual coding preview — wrapped in section card
    st.markdown(
        '<div class="section-card"><h4>\u2728 Dual Coding System</h4>'
        '<p style="color: #6B7280; font-size: 0.9rem; margin: 0;">'
        'Every word type is identified by <b>both</b> a colour <b>and</b> a symbol</p></div>',
        unsafe_allow_html=True,
    )

    from generators.styles import WORD_TYPES
    wt_items = list(WORD_TYPES.items())
    for row_start in range(0, len(wt_items), 6):
        row_items = wt_items[row_start:row_start + 6]
        cols = st.columns(len(row_items))
        for col, (key, wt) in zip(cols, row_items):
            with col:
                st.markdown(
                    f'<div style="background: #{wt["bg"]}; border: 2px solid #{wt["border"]}; '
                    f'padding: 0.5rem; border-radius: 6px; text-align: center; font-weight: 600;">'
                    f'{wt["symbol"]}<br>{wt["label"]}</div>',
                    unsafe_allow_html=True,
                )


# ─── Footer ────────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="app-footer">'
    'UK National Curriculum Worksheet Generator &middot; English (Year 1\u20136) &middot; '
    'Powered by Claude AI</div>',
    unsafe_allow_html=True,
)
