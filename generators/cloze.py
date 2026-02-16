"""
Cloze passage worksheet generator.

Takes structured JSON data (from an LLM) and produces a themed,
differentiated Word document using python-docx via reusable components.
"""

import io
from generators.components import (
    create_base_document,
    add_title_area,
    add_learning_objective,
    add_word_bank,
    add_instructions,
    add_section_header,
    add_reminder_box,
    add_section_body,
    add_success_criteria,
    add_eal_glossary_space,
    add_footer,
)


# Subtitle text varies by differentiation level
_SUBTITLES = {
    'developing': 'Use the word bank and the choices to write your story!',
    'expected': 'Use your plan and the word bank to help you!',
    'greater_depth': 'Use the word bank for ideas, then add your own!',
}

# Instruction text varies by differentiation level
_INSTRUCTIONS = {
    'developing': 'Write the word you choose on the line. Match the colours!',
    'expected': (
        'Fill in the blanks below. Match the colour and symbol '
        'to find the right word in the word bank!'
    ),
    'greater_depth': (
        'Fill in the blanks below. Use the word bank for ideas, '
        'but feel free to use your own words too!'
    ),
}


def generate_cloze_worksheet(
    content: dict,
    theme_key: str = 'classic',
    level: str = 'expected',
    objective: str = '',
    extra_spacing: bool = False,
    eal_glossary: bool = False,
    show_answers: bool = False,
) -> io.BytesIO:
    """
    Generate a cloze passage worksheet as a Word document.

    Args:
        content: Structured data from LLM with keys:
            - title: str
            - sections: list of {title, reminder, paragraphs}
            - word_bank: list of {word_type, label, words}
            - success_criteria: list of str
        theme_key: Visual theme key (e.g. 'space', 'ocean', 'classic')
        level: Differentiation level ('developing', 'expected', 'greater_depth')
        objective: Learning objective text
        extra_spacing: Whether to add extra spacing for accessibility
        eal_glossary: Whether to include EAL glossary space

    Returns:
        BytesIO buffer containing the .docx file
    """
    # 1. Create the base document with standard margins and font
    doc = create_base_document(extra_spacing=extra_spacing)

    # 2. Add the themed title area with name/date fields
    subtitle = _SUBTITLES.get(level, _SUBTITLES['expected'])
    add_title_area(doc, content['title'], subtitle, theme_key, level,
                   is_answer_key=show_answers)

    # 3. Add learning objective if provided
    if objective:
        add_learning_objective(doc, objective, theme_key)

    # 4. Add the colour-coded word bank
    add_word_bank(doc, content['word_bank'], level)

    # 5. Add instructions with colour key
    instruction_text = _INSTRUCTIONS.get(level, _INSTRUCTIONS['expected'])
    add_instructions(doc, instruction_text, level)

    # 6. Add each section: header, reminder box, and cloze paragraphs
    for section_number, section in enumerate(content['sections'], start=1):
        add_section_header(doc, section_number, section['title'], theme_key)
        if section.get('reminder'):
            add_reminder_box(doc, section['reminder'], theme_key)
        add_section_body(doc, section['paragraphs'], theme_key, level,
                         show_answers=show_answers)

    # 7. Add success criteria checklist
    add_success_criteria(doc, content['success_criteria'], theme_key, level)

    # 8. Add EAL glossary space if requested
    if eal_glossary:
        add_eal_glossary_space(doc)

    # 9. Add footer with differentiation level label
    add_footer(doc, level, 'Cloze Passage')

    # 10. Save to BytesIO buffer and return
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
