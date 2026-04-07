"""
Fraction practice worksheet generator.

Takes structured JSON data (from an LLM) and produces a themed,
differentiated Word document using python-docx via reusable components.
Children practise fractions with proper visual fraction rendering
(Unicode fraction characters and superscript/subscript notation).
"""

import io
import math
from generators.components import (
    create_base_document,
    add_title_area,
    add_learning_objective,
    add_section_header,
    add_success_criteria,
    add_eal_glossary_space,
    add_footer,
    set_run_font,
    set_no_spacing,
    set_cell_shading,
    set_cell_borders,
    set_cell_padding,
    set_table_full_width,
    remove_table_borders,
)
from generators.styles import COLOURS, DIFF_LEVELS, FONT_NAME, THEMES
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH


# ─── Unicode Fraction Mapping ────────────────────────────────────────────────
# Maps common fractions to their Unicode single-character equivalents.
# For fractions not in this map, we render numerator⁄denominator style.

UNICODE_FRACTIONS = {
    (1, 2): '\u00BD',     # ½
    (1, 3): '\u2153',     # ⅓
    (2, 3): '\u2154',     # ⅔
    (1, 4): '\u00BC',     # ¼
    (3, 4): '\u00BE',     # ¾
    (1, 5): '\u2155',     # ⅕
    (2, 5): '\u2156',     # ⅖
    (3, 5): '\u2157',     # ⅗
    (4, 5): '\u2158',     # ⅘
    (1, 6): '\u2159',     # ⅙
    (5, 6): '\u215A',     # ⅚
    (1, 7): '\u2150',     # ⅐
    (1, 8): '\u215B',     # ⅛
    (3, 8): '\u215C',     # ⅜
    (5, 8): '\u215D',     # ⅝
    (7, 8): '\u215E',     # ⅞
    (1, 9): '\u2151',     # ⅑
    (1, 10): '\u2152',    # ⅒
}

# Superscript and subscript digit maps for custom fraction rendering
_SUPERSCRIPT = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')
_SUBSCRIPT = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')
_FRACTION_SLASH = '\u2044'  # ⁄ (fraction slash)


def render_fraction_text(numerator, denominator):
    """
    Return a string that visually represents a fraction.

    Prefers Unicode fraction characters when available (½, ¼, ⅓ etc.),
    falls back to superscript-numerator⁄subscript-denominator style.

    Args:
        numerator: int or str — the top number
        denominator: int or str — the bottom number

    Returns:
        A string like '½' or '³⁄₇'
    """
    try:
        num = int(numerator)
        den = int(denominator)
    except (ValueError, TypeError):
        return f'{numerator}/{denominator}'

    # Check for Unicode single-character fraction
    unicode_char = UNICODE_FRACTIONS.get((num, den))
    if unicode_char:
        return unicode_char

    # Fallback: superscript numerator + fraction slash + subscript denominator
    sup = str(num).translate(_SUPERSCRIPT)
    sub = str(den).translate(_SUBSCRIPT)
    return f'{sup}{_FRACTION_SLASH}{sub}'


def _parse_fraction_from_text(text):
    """
    Attempt to detect and replace fraction notation in a text string.

    Looks for patterns like '3/4', '1/2', '7/10' and replaces them
    with proper Unicode fraction rendering.

    Returns the processed text string.
    """
    import re
    # Match patterns like 3/4, 12/100, etc. but not dates or file paths
    fraction_pattern = re.compile(r'(?<!\d)(\d{1,3})/(\d{1,3})(?!\d|/)')

    def replace_match(m):
        num = int(m.group(1))
        den = int(m.group(2))
        if den == 0:
            return m.group(0)  # Don't replace division by zero
        return render_fraction_text(num, den)

    return fraction_pattern.sub(replace_match, text)


def generate_fraction_practice_worksheet(
    content: dict,
    theme_key: str = 'classic',
    level: str = 'expected',
    objective: str = '',
    extra_spacing: bool = False,
    eal_glossary: bool = False,
    show_answers: bool = False,
) -> io.BytesIO:
    """
    Generate a fraction practice worksheet as a Word document.

    All fractions are rendered using proper Unicode fraction characters
    (½, ¼, ⅓) or superscript/subscript notation (⁷⁄₁₂).

    Args:
        content: Structured data from LLM with keys:
            - title: str
            - sections: list of {title, instructions, type, exercises: [{question, answer, visual_hint}]}
            - challenge: {title, instructions, lines: int} (optional)
            - success_criteria: list of str
        theme_key: Visual theme key (e.g. 'space', 'ocean', 'classic')
        level: Differentiation level ('developing', 'expected', 'greater_depth')
        objective: Learning objective text
        extra_spacing: Whether to add extra spacing for accessibility
        eal_glossary: Whether to include EAL glossary space
        show_answers: Whether to display answers (teacher answer key mode)

    Returns:
        BytesIO buffer containing the .docx file
    """
    diff = DIFF_LEVELS[level]
    theme = THEMES[theme_key]

    # 1. Create the base document with standard margins and font
    doc = create_base_document(extra_spacing=extra_spacing)

    # 2. Add the themed title area with name/date fields
    add_title_area(
        doc,
        _parse_fraction_from_text(content['title']),
        'Work with fractions carefully — show your working!',
        theme_key,
        level,
        is_answer_key=show_answers,
    )

    # 3. Add learning objective if provided
    if objective:
        add_learning_objective(doc, _parse_fraction_from_text(objective), theme_key)

    # 4. Add each section
    for section_number, section in enumerate(content.get('sections', []), start=1):
        section_title = _parse_fraction_from_text(section.get('title', ''))
        add_section_header(doc, section_number, section_title, theme_key)

        # Section instruction paragraph
        instructions = section.get('instructions', '')
        if instructions:
            spacer = doc.add_paragraph()
            spacer.paragraph_format.space_before = Pt(4)
            spacer.paragraph_format.space_after = Pt(2)

            p_inst = doc.add_paragraph()
            set_no_spacing(p_inst)
            p_inst.paragraph_format.space_after = Pt(6)
            run_inst = p_inst.add_run(_parse_fraction_from_text(instructions))
            set_run_font(
                run_inst,
                size=Pt(diff['font_size'] - 2),
                italic=True,
                colour=COLOURS['grey_text'],
            )

        # Build the exercise grid (2-column layout)
        exercises = section.get('exercises', [])
        section_type = section.get('type', 'calculate')
        num_rows = math.ceil(len(exercises) / 2)

        if num_rows > 0:
            table = doc.add_table(rows=num_rows, cols=2)
            set_table_full_width(table)
            remove_table_borders(table)

            cell_bg = theme['body']
            cell_border = theme['accent']

            for idx, exercise in enumerate(exercises):
                row_idx = idx // 2
                col_idx = idx % 2
                cell = table.cell(row_idx, col_idx)

                set_cell_shading(cell, cell_bg)
                set_cell_borders(cell, cell_border, sz=6)
                set_cell_padding(cell, top=120, bottom=120, left=150, right=150)

                # Question text — render fractions properly
                question_text = _parse_fraction_from_text(
                    exercise.get('question', '')
                )
                p_q = cell.paragraphs[0]
                set_no_spacing(p_q)
                p_q.paragraph_format.space_after = Pt(4)

                # Question number prefix
                q_num = idx + 1
                run_num = p_q.add_run(f'{q_num}. ')
                set_run_font(
                    run_num,
                    size=Pt(diff['font_size']),
                    bold=True,
                    colour=RGBColor.from_string(theme['header']),
                )

                # Question content with large font for fraction visibility
                run_q = p_q.add_run(question_text)
                set_run_font(
                    run_q,
                    size=Pt(diff['font_size'] + 2),  # Slightly larger for fraction clarity
                    bold=True,
                    colour=COLOURS['black'],
                )

                # Visual hint for developing level (e.g. fraction diagram description)
                visual_hint = exercise.get('visual_hint')
                if visual_hint and not show_answers:
                    p_hint = cell.add_paragraph()
                    set_no_spacing(p_hint)
                    p_hint.paragraph_format.space_before = Pt(4)
                    run_hint = p_hint.add_run(
                        _parse_fraction_from_text(visual_hint)
                    )
                    set_run_font(
                        run_hint,
                        size=Pt(diff['font_size'] - 3),
                        italic=True,
                        colour=COLOURS['hint_text'],
                    )

                # Show answer in bold green if answer key mode
                if show_answers and exercise.get('answer'):
                    answer_text = _parse_fraction_from_text(
                        str(exercise['answer'])
                    )
                    p_ans = cell.add_paragraph()
                    set_no_spacing(p_ans)
                    p_ans.paragraph_format.space_before = Pt(4)
                    run_ans = p_ans.add_run(f'Answer: {answer_text}')
                    set_run_font(
                        run_ans,
                        size=Pt(diff['font_size']),
                        bold=True,
                        colour=COLOURS['criteria_text'],
                    )
                elif not show_answers:
                    # Blank answer line
                    p_ans = cell.add_paragraph()
                    set_no_spacing(p_ans)
                    p_ans.paragraph_format.space_before = Pt(8)
                    run_ans = p_ans.add_run('Answer: _______________')
                    set_run_font(
                        run_ans,
                        size=Pt(diff['font_size']),
                        colour=COLOURS['hint_text'],
                    )

            # Clear any leftover empty cells when odd number of exercises
            if len(exercises) % 2 == 1:
                empty_cell = table.cell(num_rows - 1, 1)
                empty_cell.paragraphs[0].clear()

    # 5. Add challenge section if present (skip for developing level)
    challenge = content.get('challenge')
    if challenge and level != 'developing':
        challenge_number = len(content.get('sections', [])) + 1
        add_section_header(doc, challenge_number, challenge['title'], theme_key)

        if challenge.get('instructions'):
            spacer = doc.add_paragraph()
            spacer.paragraph_format.space_before = Pt(4)
            spacer.paragraph_format.space_after = Pt(2)

            p_chal = doc.add_paragraph()
            set_no_spacing(p_chal)
            p_chal.paragraph_format.space_after = Pt(6)
            run_chal = p_chal.add_run(
                _parse_fraction_from_text(challenge['instructions'])
            )
            set_run_font(
                run_chal,
                size=Pt(diff['font_size'] - 2),
                italic=True,
                colour=COLOURS['grey_text'],
            )

        num_lines = challenge.get('lines', 3)
        for _ in range(num_lines):
            p_line = doc.add_paragraph()
            set_no_spacing(p_line)
            p_line.paragraph_format.space_before = Pt(6)
            p_line.paragraph_format.space_after = Pt(6)
            run_line = p_line.add_run('_' * 70)
            set_run_font(
                run_line,
                size=Pt(diff['font_size']),
                colour=COLOURS['hint_text'],
            )

    # 6. Add success criteria checklist
    add_success_criteria(doc, content.get('success_criteria', []), theme_key, level)

    # 7. Add EAL glossary space if requested
    if eal_glossary:
        add_eal_glossary_space(doc)

    # 8. Add footer with differentiation level label
    add_footer(doc, level, 'Fraction Practice')

    # 9. Save to BytesIO buffer and return
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
