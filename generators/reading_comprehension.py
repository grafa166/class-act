"""
Reading comprehension worksheet generator.

Takes structured JSON data (from an LLM) and produces a themed,
differentiated Word document using python-docx via reusable components.
Children read a passage and answer tiered comprehension questions.
"""

import io
from generators.components import (
    create_base_document,
    add_title_area,
    add_learning_objective,
    add_reading_passage,
    add_vocabulary_box,
    add_comprehension_questions,
    add_success_criteria,
    add_eal_glossary_space,
    add_footer,
)


# Subtitle text varies by differentiation level
_SUBTITLES = {
    'developing': 'Read the passage carefully, then answer the questions!',
    'expected': 'Read the passage and answer the questions in full sentences!',
    'greater_depth': 'Read the passage closely and explain your thinking!',
}


def generate_reading_comprehension_worksheet(
    content: dict,
    theme_key: str = 'classic',
    level: str = 'expected',
    objective: str = '',
    extra_spacing: bool = False,
    eal_glossary: bool = False,
    show_answers: bool = False,
) -> io.BytesIO:
    """
    Generate a reading comprehension worksheet as a Word document.

    Args:
        content: Structured data from LLM with keys:
            - title: str
            - passage: {title, text, source_note}
            - vocabulary: list of {word, definition, word_type}
            - questions: list of {number, question, question_type, marks,
                                  lines, answer, word_bank}
            - success_criteria: list of str
        theme_key: Visual theme key (e.g. 'space', 'ocean', 'classic')
        level: Differentiation level ('developing', 'expected', 'greater_depth')
        objective: Learning objective text
        extra_spacing: Whether to add extra spacing for accessibility
        eal_glossary: Whether to include EAL glossary space
        show_answers: Whether to render as answer key (teacher edition)

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

    # 4. Add the reading passage
    add_reading_passage(doc, content['passage'], theme_key, level)

    # 5. Add vocabulary box if vocabulary is provided
    vocabulary = content.get('vocabulary', [])
    if vocabulary:
        add_vocabulary_box(doc, vocabulary, level)

    # 6. Add comprehension questions (with answer lines or model answers)
    add_comprehension_questions(
        doc, content['questions'], level, show_answers=show_answers
    )

    # 7. Add success criteria checklist
    add_success_criteria(doc, content['success_criteria'], theme_key, level)

    # 8. Add EAL glossary space if requested
    if eal_glossary:
        add_eal_glossary_space(doc)

    # 9. Add footer with differentiation level label
    add_footer(doc, level, 'Reading Comprehension')

    # 10. Save to BytesIO buffer and return
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
