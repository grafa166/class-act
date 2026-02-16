"""
Prompt templates for UK Primary School worksheet generation.

Contains detailed prompt templates for 5 worksheet types:
- CLOZE: Fill-in-the-blank passage with differentiated levels
- WORD_BANK: Vocabulary exploration activities
- MATCHING: Word-to-definition matching activities
- SENTENCE_BUILDER: Sentence construction exercises
- READING_COMPREHENSION: Reading passage with comprehension questions

Each prompt is designed to elicit structured JSON output from Claude
that matches the exact schema required by the worksheet generators.
"""

from typing import Dict, Callable


# =============================================================================
# 1. CLOZE PROMPT - Fill-in-the-blank passage
# =============================================================================

CLOZE_PROMPT = """You are an expert UK primary school teacher creating a cloze (fill-in-the-blank) worksheet for {year_group} pupils (aged {age_range}).

CURRICULUM CONTEXT:
- Subject/Topic: {topic}
- Learning Objective: {objective}
- Theme: {theme_name} {theme_icon}
- Differentiation Level: {level}

YOUR TASK:
Create an engaging cloze passage themed around "{theme_name}" that helps pupils work towards the learning objective. The passage should tell a coherent, imaginative story or explanation that weaves in vocabulary and grammar concepts from the curriculum objective.

DIFFERENTIATION LEVEL RULES - YOU MUST FOLLOW THESE EXACTLY:

If the level is "developing":
- Create 2-3 sections
- Include 4-6 blanks total across all sections
- Every blank MUST have a "choices" field with exactly 3 word options (the correct word plus 2 plausible distractors)
- Use simple, short sentences (6-10 words per sentence)
- Use common, everyday vocabulary appropriate for pupils who need extra support
- Word bank entries MUST include "definition" fields with child-friendly explanations
- Sections should have supportive "reminder" prompts

If the level is "expected":
- Create 3-4 sections
- Include 8-12 blanks total across all sections
- Every blank MUST have a "hint" field (a descriptive clue, e.g. "a describing word for size") but NO "choices" field
- Use moderate-length sentences (8-15 words per sentence)
- Use age-appropriate vocabulary that matches {year_group} expectations
- Word bank entries should NOT include "definition" fields
- Sections should have brief "reminder" prompts

If the level is "greater_depth":
- Create 4-5 sections
- Include 12-16 blanks total across all sections
- Some blanks should have a "hint" field, but at least 3-4 blanks MUST have word_type set to "open" (where the child writes their own creative word)
- Use longer, more complex sentences (10-20 words per sentence)
- Use rich, ambitious vocabulary appropriate for higher-ability {year_group} pupils
- Word bank entries should NOT include "definition" fields
- Keep "reminder" prompts minimal or omit them

WORD TYPES - Use these exact word_type values and corresponding labels:
- "time" with label "\\u23f0 When? (Time words)"
- "adjective" with label "\\u2b50 Describing Words (Adjectives)"
- "verb" with label "\\u26a1 Doing Words (Verbs)"
- "noun" with label "\\u25cf Things & Places (Nouns)"
- "name" with label "\\u2605 Names (Proper Nouns)"
- "open" with label "\\u270d Your Own Words" (ONLY for greater_depth level)

YOU MUST OUTPUT VALID JSON matching this EXACT schema. Do not include any text outside the JSON object.

{{
  "title": "<A creative, engaging title for the worksheet related to the theme>",
  "sections": [
    {{
      "title": "<SECTION HEADING IN CAPS, e.g. THE BEGINNING>",
      "reminder": "<A helpful tip for the pupil, e.g. Think about how your story starts! - or null if not needed>",
      "paragraphs": [
        [
          {{"type": "text", "text": "<text before the blank>"}},
          {{"type": "blank", "word_type": "<one of: time, adjective, verb, noun, name, open>", "answer": "<the correct word>", "hint": "<descriptive hint for expected/greater_depth>", "choices": ["<option1>", "<option2>", "<option3>"]}},
          {{"type": "text", "text": "<text after the blank>"}}
        ]
      ]
    }}
  ],
  "word_bank": [
    {{
      "word_type": "<matching word_type from above>",
      "label": "<matching label from above>",
      "words": [
        {{"word": "<the vocabulary word>", "definition": "<child-friendly definition - ONLY for developing level, omit for others>"}}
      ]
    }}
  ],
  "success_criteria": [
    "<criterion 1 starting with 'I can...' or 'I wrote...' or 'I used...'>",
    "<criterion 2>",
    "<criterion 3>"
  ]
}}

CRITICAL RULES FOR THE JSON:
1. Each paragraph is an array of segment objects. A segment is either {{"type": "text", "text": "..."}} or {{"type": "blank", ...}}.
2. For "developing" level: every blank MUST have "choices" (array of 3 strings). Do NOT include "hint".
3. For "expected" level: every blank MUST have "hint" (string). Do NOT include "choices".
4. For "greater_depth" level: blanks can have "hint" OR have word_type "open". Open blanks need no hint or choices.
5. The word_bank must contain ALL words used in blanks (except "open" type blanks).
6. Group words in the word_bank by their word_type. Each word_type should appear only once in the word_bank array.
7. success_criteria should have 3-5 pupil-friendly statements.
8. Make the content genuinely engaging and themed around {theme_name} {theme_icon}.
9. Ensure the passage makes narrative sense when all blanks are correctly filled.
10. The "definition" field in word_bank entries is ONLY included for "developing" level. For "expected" and "greater_depth", omit it entirely.
11. Every blank MUST include an "answer" field containing the single correct word that fills the blank.

Generate the JSON now:"""


def get_cloze_prompt(
    year_group: str,
    topic: str,
    objective: str,
    age_range: str,
    theme_name: str,
    theme_icon: str,
    level: str,
) -> str:
    """
    Build a complete cloze worksheet prompt with all placeholders filled.

    Args:
        year_group: e.g. "Year 3"
        topic: e.g. "Writing - Myths & Legends"
        objective: e.g. "Plan, draft, and write narratives..."
        age_range: e.g. "7-8"
        theme_name: e.g. "Space Explorer"
        theme_icon: e.g. "rocket emoji"
        level: One of "developing", "expected", or "greater_depth"

    Returns:
        The fully formatted prompt string ready to send to Claude.
    """
    return CLOZE_PROMPT.format(
        year_group=year_group,
        topic=topic,
        objective=objective,
        age_range=age_range,
        theme_name=theme_name,
        theme_icon=theme_icon,
        level=level,
    )


# =============================================================================
# 2. WORD_BANK PROMPT - Vocabulary exploration activities
# =============================================================================

WORD_BANK_PROMPT = """You are an expert UK primary school teacher creating a vocabulary / word bank worksheet for {year_group} pupils (aged {age_range}).

CURRICULUM CONTEXT:
- Subject/Topic: {topic}
- Learning Objective: {objective}
- Theme: {theme_name} {theme_icon}
- Differentiation Level: {level}

YOUR TASK:
Create a vocabulary exploration worksheet themed around "{theme_name}" that builds pupils' word knowledge in line with the curriculum objective. The worksheet should include categorised word banks and engaging sentence-based activities.

DIFFERENTIATION LEVEL RULES - YOU MUST FOLLOW THESE EXACTLY:

If the level is "developing":
- Create 3-4 word categories
- Include 3-4 words per category
- Every word MUST have a "definition" field with a simple, child-friendly explanation
- Create 3-4 fill-in-the-gap sentences in the activities section
- Every blank in sentences MUST have a "choices" field with exactly 3 options
- Use simple, familiar vocabulary that pupils who need support can access
- Sentences should be short (6-10 words)

If the level is "expected":
- Create 4-5 word categories
- Include 5-6 words per category
- Words should NOT have a "definition" field
- Create 5-6 fill-in-the-gap sentences in the activities section
- Every blank in sentences MUST have a "hint" field (descriptive clue) but NO "choices"
- Use age-appropriate vocabulary matching {year_group} expectations
- Sentences should be moderate length (8-15 words)

If the level is "greater_depth":
- Create 5-6 word categories
- Include 7-8 words per category (include ambitious, challenging vocabulary)
- Words should NOT have a "definition" field
- Create 6-8 fill-in-the-gap sentences in the activities section
- Some blanks should have "hint", but at least 2-3 blanks should have word_type "open" (pupil chooses their own word)
- Use rich, sophisticated vocabulary that challenges higher-ability pupils
- Sentences should be longer and more complex (10-20 words)

WORD TYPES - Use these exact word_type values and labels:
- "noun" with label "\\u25cf Naming Words (Nouns)"
- "adjective" with label "\\u2b50 Describing Words (Adjectives)"
- "verb" with label "\\u26a1 Doing Words (Verbs)"
- "adverb" with label "\\u27a1 How Words (Adverbs)"
- "connective" with label "\\u26d3 Joining Words (Connectives)"
- "open" with label "\\u270d Your Own Words" (ONLY for greater_depth level)

YOU MUST OUTPUT VALID JSON matching this EXACT schema. Do not include any text outside the JSON object.

{{
  "title": "<A creative, engaging title for the vocabulary worksheet>",
  "categories": [
    {{
      "word_type": "<one of: noun, adjective, verb, adverb, connective>",
      "label": "<matching label from the word types list above>",
      "words": [
        {{"word": "<vocabulary word>", "definition": "<child-friendly definition - ONLY for developing level, omit key entirely for others>"}}
      ]
    }}
  ],
  "activities": [
    {{
      "title": "<Activity title, e.g. Fill in the Gaps>",
      "instructions": "<Clear instructions for the pupil>",
      "sentences": [
        {{
          "pieces": [
            {{"type": "text", "text": "<text before blank>"}},
            {{"type": "blank", "word_type": "<word_type>", "answer": "<the correct word>", "hint": "<descriptive hint - for expected/greater_depth>", "choices": ["<opt1>", "<opt2>", "<opt3>"]}},
            {{"type": "text", "text": "<text after blank>"}}
          ]
        }}
      ]
    }}
  ],
  "success_criteria": [
    "<criterion 1 starting with 'I can...' or 'I matched...' or 'I used...'>",
    "<criterion 2>",
    "<criterion 3>"
  ]
}}

CRITICAL RULES FOR THE JSON:
1. Each sentence in the activities is an object with a "pieces" array. Each piece is either {{"type": "text", "text": "..."}} or {{"type": "blank", ...}}.
2. For "developing" level: every blank MUST have "choices" (array of 3 strings). Do NOT include "hint". Word entries MUST have "definition".
3. For "expected" level: every blank MUST have "hint" (string). Do NOT include "choices". Word entries must NOT have "definition".
4. For "greater_depth" level: most blanks have "hint", some have word_type "open" (no hint or choices needed). Word entries must NOT have "definition".
5. All words used in sentence blanks should come from the categories word bank (except "open" type).
6. Each word_type should appear only once in the categories array.
7. success_criteria should have 3-5 pupil-friendly "I can..." statements.
8. Theme all content around {theme_name} {theme_icon} to make it engaging.
9. Ensure vocabulary is genuinely useful and connected to the learning objective.
10. The activities section can have 1-2 activity objects. Each activity has its own title, instructions, and sentences array.
11. Every blank MUST include an "answer" field containing the single correct word that fills the blank.

Generate the JSON now:"""


def get_word_bank_prompt(
    year_group: str,
    topic: str,
    objective: str,
    age_range: str,
    theme_name: str,
    theme_icon: str,
    level: str,
) -> str:
    """
    Build a complete word bank worksheet prompt with all placeholders filled.

    Args:
        year_group: e.g. "Year 3"
        topic: e.g. "Writing - Myths & Legends"
        objective: e.g. "Plan, draft, and write narratives..."
        age_range: e.g. "7-8"
        theme_name: e.g. "Space Explorer"
        theme_icon: e.g. "rocket emoji"
        level: One of "developing", "expected", or "greater_depth"

    Returns:
        The fully formatted prompt string ready to send to Claude.
    """
    return WORD_BANK_PROMPT.format(
        year_group=year_group,
        topic=topic,
        objective=objective,
        age_range=age_range,
        theme_name=theme_name,
        theme_icon=theme_icon,
        level=level,
    )


# =============================================================================
# 3. MATCHING PROMPT - Word-to-definition matching activities
# =============================================================================

MATCHING_PROMPT = """You are an expert UK primary school teacher creating a matching / connecting worksheet for {year_group} pupils (aged {age_range}).

CURRICULUM CONTEXT:
- Subject/Topic: {topic}
- Learning Objective: {objective}
- Theme: {theme_name} {theme_icon}
- Differentiation Level: {level}

YOUR TASK:
Create a matching activity worksheet themed around "{theme_name}" where pupils draw lines to connect related items (words to definitions, synonyms, antonyms, sentence halves, etc.). The content should support the curriculum learning objective.

DIFFERENTIATION LEVEL RULES - YOU MUST FOLLOW THESE EXACTLY:

If the level is "developing":
- Create exactly 1 activity
- The activity should have 5-6 matching pairs
- Use simple, everyday vocabulary that pupils who need extra support can access
- Left-side items should be single words; right-side items should be very short, simple definitions or descriptions
- Do NOT include a bonus_activity (set it to null)
- Make the matches unambiguous - each left item should clearly match only one right item

If the level is "expected":
- Create exactly 2 activities (e.g. "Match the Words to Meanings" and "Match the Synonyms" or "Match Sentence Halves")
- Each activity should have 6-8 matching pairs
- Use age-appropriate vocabulary matching {year_group} expectations
- Include some pairs that require deeper thinking
- Include a simple bonus_activity with 2-3 lines for writing
- The bonus should ask pupils to use some of the matched words in short sentences

If the level is "greater_depth":
- Create 2-3 activities with varied matching types (definitions, synonyms, antonyms, sentence completion, etc.)
- Each activity should have 8-10 matching pairs
- Use ambitious, challenging vocabulary that stretches higher-ability pupils
- Include pairs that require inference or deeper understanding
- Include a challenging bonus_activity with 3-4 lines
- The bonus should ask pupils to write their own sentences using matched words, or to explain the relationship between pairs

YOU MUST OUTPUT VALID JSON matching this EXACT schema. Do not include any text outside the JSON object.

{{
  "title": "<A creative, engaging title for the matching worksheet, e.g. Word Detective>",
  "activities": [
    {{
      "title": "<Activity title, e.g. Match the Words to Their Meanings>",
      "instructions": "<Clear instructions, e.g. Draw a line to match each word on the left to its meaning on the right.>",
      "pairs": [
        {{"left": "<word, phrase, or sentence start>", "right": "<definition, synonym, or sentence end>"}}
      ]
    }}
  ],
  "bonus_activity": {{
    "title": "<Bonus/challenge activity title, e.g. Challenge Time!>",
    "instructions": "<Instructions for the bonus task, e.g. Choose three words from above and use each one in your own sentence.>",
    "lines": <number of writing lines to provide, e.g. 3>
  }},
  "success_criteria": [
    "<criterion 1 starting with 'I can...' or 'I matched...'>",
    "<criterion 2>",
    "<criterion 3>"
  ]
}}

CRITICAL RULES FOR THE JSON:
1. Each activity in the "activities" array has "title" (string), "instructions" (string), and "pairs" (array of objects with "left" and "right" string fields).
2. For "developing" level: set "bonus_activity" to null (the JSON value null, not the string "null").
3. For "expected" and "greater_depth" levels: "bonus_activity" must be an object with "title", "instructions", and "lines" fields.
4. The "lines" field in bonus_activity is an integer (number of writing lines for pupils).
5. Make sure left-side items are SHUFFLED relative to right-side items so the matching is not in order (i.e., the first left item should NOT match the first right item when read top to bottom).
6. success_criteria should have 3-5 pupil-friendly statements.
7. Theme all content around {theme_name} {theme_icon}.
8. Ensure vocabulary and concepts are directly connected to the learning objective: {objective}
9. Right-side definitions/descriptions should be genuinely helpful and accurate.
10. Vary the types of matching across activities when there are multiple activities (e.g., one could be word-to-definition, another could be synonym pairs or sentence halves).

Generate the JSON now:"""


def get_matching_prompt(
    year_group: str,
    topic: str,
    objective: str,
    age_range: str,
    theme_name: str,
    theme_icon: str,
    level: str,
) -> str:
    """
    Build a complete matching worksheet prompt with all placeholders filled.

    Args:
        year_group: e.g. "Year 3"
        topic: e.g. "Writing - Myths & Legends"
        objective: e.g. "Plan, draft, and write narratives..."
        age_range: e.g. "7-8"
        theme_name: e.g. "Space Explorer"
        theme_icon: e.g. "rocket emoji"
        level: One of "developing", "expected", or "greater_depth"

    Returns:
        The fully formatted prompt string ready to send to Claude.
    """
    return MATCHING_PROMPT.format(
        year_group=year_group,
        topic=topic,
        objective=objective,
        age_range=age_range,
        theme_name=theme_name,
        theme_icon=theme_icon,
        level=level,
    )


# =============================================================================
# 4. SENTENCE_BUILDER PROMPT - Sentence construction exercises
# =============================================================================

SENTENCE_BUILDER_PROMPT = """You are an expert UK primary school teacher creating a sentence building worksheet for {year_group} pupils (aged {age_range}).

CURRICULUM CONTEXT:
- Subject/Topic: {topic}
- Learning Objective: {objective}
- Theme: {theme_name} {theme_icon}
- Differentiation Level: {level}

YOUR TASK:
Create a sentence construction worksheet themed around "{theme_name}" where pupils arrange given words/phrases into complete sentences. Each exercise provides word parts that pupils must reorder and write as a proper sentence. The content should reinforce the curriculum learning objective.

DIFFERENTIATION LEVEL RULES - YOU MUST FOLLOW THESE EXACTLY:

If the level is "developing":
- Create 3-4 exercises
- Each exercise should have 3-5 sentence parts (short words/phrases)
- Use very simple, common vocabulary that pupils who need extra support can access
- Sentences when assembled should be short and straightforward (6-10 words)
- Do NOT include an extension activity (set "extension" to null)
- Each sentence part should be a single word or very short phrase
- Word types should be simple: noun, verb, adjective

If the level is "expected":
- Create 4-6 exercises
- Each exercise should have 4-7 sentence parts
- Use age-appropriate vocabulary matching {year_group} expectations
- Sentences when assembled should be moderate length (8-15 words)
- Include an extension activity with 2-3 writing lines
- The extension should ask pupils to write 1-2 of their own sentences using similar patterns
- Include a mix of word types: noun, verb, adjective, adverb, connective

If the level is "greater_depth":
- Create 6-8 exercises
- Each exercise should have 5-8 sentence parts
- Use ambitious, sophisticated vocabulary that challenges higher-ability pupils
- Sentences when assembled should be longer and more complex (10-20 words)
- Include compound or complex sentences with connectives
- Include an extension activity with 3-4 writing lines
- The extension should challenge pupils to write their own complex sentences or to improve a given sentence
- Use varied word types: noun, verb, adjective, adverb, connective, preposition

WORD TYPES FOR COLOUR-CODING - Use these exact word_type values:
- "noun" - naming words (people, places, things)
- "verb" - doing/being words
- "adjective" - describing words
- "adverb" - words that describe how/when/where
- "connective" - joining words (and, but, because, although)
- "preposition" - position/direction words (in, on, through, beneath)
- "punctuation" - punctuation marks (. , ! ?)

YOU MUST OUTPUT VALID JSON matching this EXACT schema. Do not include any text outside the JSON object.

{{
  "title": "<A creative, engaging title for the sentence builder worksheet, e.g. Sentence Builders>",
  "exercises": [
    {{
      "title": "<Exercise title, e.g. Build a Sentence or Sentence 1>",
      "instructions": "<Clear instructions, e.g. Arrange these words to make a sentence. Don't forget your capital letter and full stop!>",
      "sentence_parts": [
        {{"part": "<a word or short phrase>", "word_type": "<one of: noun, verb, adjective, adverb, connective, preposition, punctuation>"}}
      ],
      "correct_sentence": "<The complete correctly ordered sentence with proper punctuation.>"
    }}
  ],
  "extension": {{
    "title": "<Extension activity title, e.g. Now Try Your Own!>",
    "instructions": "<Instructions for the extension, e.g. Write your own sentence using at least one word from each colour group.>",
    "lines": <number of writing lines to provide, e.g. 3>
  }},
  "success_criteria": [
    "<criterion 1 starting with 'I can...' or 'I built...' or 'I wrote...'>",
    "<criterion 2>",
    "<criterion 3>"
  ]
}}

CRITICAL RULES FOR THE JSON:
1. Each exercise has "title" (string), "instructions" (string), and "sentence_parts" (array of objects).
2. Each sentence_part has "part" (string - the word or phrase) and "word_type" (string - for colour-coding).
3. The sentence_parts should be listed in a SCRAMBLED order - NOT in the correct sentence order. Pupils need to rearrange them.
4. However, when rearranged correctly, the parts must form a grammatically correct, meaningful sentence.
5. For "developing" level: set "extension" to null (the JSON value null, not the string "null").
6. For "expected" and "greater_depth" levels: "extension" must be an object with "title", "instructions", and "lines" fields.
7. The "lines" field in extension is an integer (number of writing lines).
8. Do NOT include punctuation as a separate sentence_part unless it is useful for teaching (e.g., teaching where a comma goes in a list). Normally, the instructions should tell pupils to add their own capital letter and full stop.
9. success_criteria should have 3-5 pupil-friendly statements.
10. Theme all content around {theme_name} {theme_icon}.
11. Ensure the vocabulary and sentence structures align with the learning objective: {objective}
12. Each exercise should produce a DIFFERENT sentence (do not repeat the same sentence pattern).
13. Vary sentence structures across exercises - include statements, questions, exclamations, or commands as appropriate for {year_group}.
14. Each exercise MUST include a "correct_sentence" field containing the full, correctly ordered sentence with proper punctuation.

Generate the JSON now:"""


def get_sentence_builder_prompt(
    year_group: str,
    topic: str,
    objective: str,
    age_range: str,
    theme_name: str,
    theme_icon: str,
    level: str,
) -> str:
    """
    Build a complete sentence builder worksheet prompt with all placeholders filled.

    Args:
        year_group: e.g. "Year 3"
        topic: e.g. "Writing - Myths & Legends"
        objective: e.g. "Plan, draft, and write narratives..."
        age_range: e.g. "7-8"
        theme_name: e.g. "Space Explorer"
        theme_icon: e.g. "rocket emoji"
        level: One of "developing", "expected", or "greater_depth"

    Returns:
        The fully formatted prompt string ready to send to Claude.
    """
    return SENTENCE_BUILDER_PROMPT.format(
        year_group=year_group,
        topic=topic,
        objective=objective,
        age_range=age_range,
        theme_name=theme_name,
        theme_icon=theme_icon,
        level=level,
    )


# =============================================================================
# 5. READING_COMPREHENSION PROMPT - Reading passage with questions
# =============================================================================

READING_COMPREHENSION_PROMPT = """You are an expert UK primary school teacher creating a reading comprehension worksheet for {year_group} pupils (aged {age_range}).

CURRICULUM CONTEXT:
- Subject/Topic: {topic}
- Learning Objective: {objective}
- Theme: {theme_name} {theme_icon}
- Differentiation Level: {level}

YOUR TASK:
Create a reading comprehension worksheet themed around "{theme_name}" that includes a reading passage followed by comprehension questions. The passage and questions should help pupils work towards the learning objective and be appropriately differentiated.

DIFFERENTIATION LEVEL RULES - YOU MUST FOLLOW THESE EXACTLY:

If the level is "developing":
- Create a passage of 100-150 words
- Use simple, short sentences (6-10 words per sentence)
- Use common, everyday vocabulary appropriate for pupils who need extra support
- Include 4-5 questions, mostly "retrieval" type (answers found directly in the text)
- Every question MUST have a "word_bank" field with 2-3 hint words to help the pupil
- Questions should require only 1-2 answer lines
- Include 3-4 vocabulary words with definitions
- Marks should be 1 per question

If the level is "expected":
- Create a passage of 200-300 words
- Use moderate-length sentences (8-15 words per sentence)
- Use age-appropriate vocabulary matching {year_group} expectations
- Include 6-8 questions with a mix of types: retrieval, inference, vocabulary
- Do NOT include "word_bank" for any question (omit the field entirely)
- Questions should require 2-3 answer lines
- Include 4-6 vocabulary words with definitions
- Marks should be 1-2 per question

If the level is "greater_depth":
- Create a passage of 300-400 words
- Use longer, more complex sentences (10-20 words per sentence)
- Use rich, ambitious vocabulary appropriate for higher-ability {year_group} pupils
- Include 8-10 questions focusing on inference, author_intent, evaluation, and vocabulary
- Do NOT include "word_bank" for any question (omit the field entirely)
- Questions should require 3-4 answer lines
- Include 5-8 vocabulary words with definitions
- Marks should be 1-3 per question

QUESTION TYPES - Use these exact values:
- "retrieval" - answers found directly in the text
- "inference" - pupils must read between the lines and use clues from the text
- "vocabulary" - questions about the meaning or effect of specific words/phrases
- "author_intent" - why the author made specific choices (word choice, structure, etc.)
- "evaluation" - pupils give their opinion with evidence from the text

YOU MUST OUTPUT VALID JSON matching this EXACT schema. Do not include any text outside the JSON object.

{{
  "title": "<A creative, engaging title for the worksheet related to the theme>",
  "passage": {{
    "title": "<Title of the reading passage>",
    "text": "<The full reading passage text. Use \\n\\n for paragraph breaks.>",
    "source_note": "<e.g. 'Adapted from...' or null if original>"
  }},
  "vocabulary": [
    {{
      "word": "<a vocabulary word from the passage>",
      "definition": "<child-friendly definition>",
      "word_type": "<one of: noun, verb, adjective, adverb>"
    }}
  ],
  "questions": [
    {{
      "number": <question number starting from 1>,
      "question": "<the comprehension question>",
      "question_type": "<one of: retrieval, inference, vocabulary, author_intent, evaluation>",
      "marks": <number of marks 1-3>,
      "lines": <number of answer lines 1-4>,
      "answer": "<model answer for teacher edition>",
      "word_bank": ["<hint word 1>", "<hint word 2>"]
    }}
  ],
  "success_criteria": [
    "<criterion 1 starting with 'I can...' or 'I found...' or 'I explained...'>",
    "<criterion 2>",
    "<criterion 3>"
  ]
}}

CRITICAL RULES FOR THE JSON:
1. The "passage" object must have "title" (string), "text" (string), and "source_note" (string or null).
2. Use "\\n\\n" within the passage text to separate paragraphs.
3. The "vocabulary" array should contain words that appear in the passage and are important for comprehension.
4. Each question must have: "number" (int), "question" (string), "question_type" (string), "marks" (int), "lines" (int), "answer" (string).
5. For "developing" level: every question MUST have a "word_bank" field (array of 2-3 hint strings).
6. For "expected" and "greater_depth" levels: do NOT include "word_bank" in questions.
7. The "answer" field should contain a complete model answer suitable for a teacher marking guide.
8. Questions should progress from easier (retrieval) to harder (inference, evaluation).
9. success_criteria should have 3-5 pupil-friendly statements.
10. Make the passage genuinely engaging and themed around {theme_name} {theme_icon}.
11. Ensure the passage is self-contained and provides enough information to answer all questions.
12. For vocabulary questions, the word being asked about must appear in the passage.

Generate the JSON now:"""


def get_reading_comprehension_prompt(
    year_group: str,
    topic: str,
    objective: str,
    age_range: str,
    theme_name: str,
    theme_icon: str,
    level: str,
) -> str:
    """Build a complete reading comprehension prompt with all placeholders filled."""
    return READING_COMPREHENSION_PROMPT.format(
        year_group=year_group,
        topic=topic,
        objective=objective,
        age_range=age_range,
        theme_name=theme_name,
        theme_icon=theme_icon,
        level=level,
    )


# =============================================================================
# PROMPT REGISTRY - Maps worksheet type names to their prompt functions
# =============================================================================

_PROMPT_REGISTRY: Dict[str, Callable[..., str]] = {
    "cloze": get_cloze_prompt,
    "word_bank": get_word_bank_prompt,
    "matching": get_matching_prompt,
    "sentence_builder": get_sentence_builder_prompt,
    "reading_comprehension": get_reading_comprehension_prompt,
}

# Also accept alternative naming conventions
_PROMPT_ALIASES: Dict[str, str] = {
    "cloze": "cloze",
    "cloze_passage": "cloze",
    "fill_in_the_blank": "cloze",
    "fill_in_the_blanks": "cloze",
    "word_bank": "word_bank",
    "wordbank": "word_bank",
    "vocabulary": "word_bank",
    "vocab": "word_bank",
    "matching": "matching",
    "match": "matching",
    "connecting": "matching",
    "sentence_builder": "sentence_builder",
    "sentence_building": "sentence_builder",
    "sentences": "sentence_builder",
    "reading_comprehension": "reading_comprehension",
    "reading_comp": "reading_comprehension",
    "comprehension": "reading_comprehension",
    "reading": "reading_comprehension",
}


def get_prompt(worksheet_type: str, **kwargs) -> str:
    """
    Get the appropriate prompt for the given worksheet type.

    This is a convenience function that dispatches to the correct
    prompt-building function based on the worksheet type name.

    Args:
        worksheet_type: The type of worksheet to generate. Accepts:
            - "cloze", "cloze_passage", "fill_in_the_blank", "fill_in_the_blanks"
            - "word_bank", "wordbank", "vocabulary", "vocab"
            - "matching", "match", "connecting"
            - "sentence_builder", "sentence_building", "sentences"
        **kwargs: Keyword arguments passed to the prompt function:
            - year_group (str): e.g. "Year 3"
            - topic (str): e.g. "Writing - Myths & Legends"
            - objective (str): e.g. "Plan, draft, and write narratives..."
            - age_range (str): e.g. "7-8"
            - theme_name (str): e.g. "Space Explorer"
            - theme_icon (str): e.g. "rocket emoji"
            - level (str): One of "developing", "expected", or "greater_depth"

    Returns:
        The fully formatted prompt string ready to send to Claude.

    Raises:
        ValueError: If the worksheet_type is not recognised.
    """
    # Normalise the worksheet type to lowercase with underscores
    normalised = worksheet_type.strip().lower().replace("-", "_").replace(" ", "_")

    # Look up the canonical name via aliases
    canonical = _PROMPT_ALIASES.get(normalised)
    if canonical is None:
        valid_types = sorted(set(_PROMPT_ALIASES.values()))
        raise ValueError(
            f"Unknown worksheet type: '{worksheet_type}'. "
            f"Valid types are: {valid_types}. "
            f"Also accepted: {sorted(_PROMPT_ALIASES.keys())}"
        )

    # Get and call the prompt function
    prompt_fn = _PROMPT_REGISTRY[canonical]
    return prompt_fn(**kwargs)


def list_worksheet_types() -> list:
    """
    Return a list of the canonical worksheet type names.

    Returns:
        List of strings: ["cloze", "matching", "sentence_builder", "word_bank"]
    """
    return sorted(_PROMPT_REGISTRY.keys())


def list_all_aliases() -> Dict[str, str]:
    """
    Return the complete alias mapping from alternative names to canonical names.

    Returns:
        Dictionary mapping alias strings to their canonical worksheet type names.
    """
    return dict(_PROMPT_ALIASES)
