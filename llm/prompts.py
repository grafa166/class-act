"""
Prompt templates for UK Primary School worksheet generation.

Contains detailed prompt templates for 8 worksheet types:
- CLOZE: Fill-in-the-blank passage with differentiated levels
- WORD_BANK: Vocabulary exploration activities
- MATCHING: Word-to-definition matching activities
- SENTENCE_BUILDER: Sentence construction exercises
- READING_COMPREHENSION: Reading passage with comprehension questions
- PROBLEM_SOLVING: Maths word problems with structured questions
- CALCULATION_PRACTICE: Maths calculation exercises with working space
- INVESTIGATION: Science investigation planning template

Each prompt is designed to elicit structured JSON output from Claude
that matches the exact schema required by the worksheet generators.

Prompts are subject-aware: word types and context are injected based
on the selected subject (English, Maths, Science, History, etc.).
"""

from typing import Dict, Callable


# =============================================================================
# SUBJECT-SPECIFIC WORD TYPES AND CONTEXT
# =============================================================================

SUBJECT_WORD_TYPES = {
    "English": """WORD TYPES - Use these exact word_type values and corresponding labels:
- "time" with label "\\u23f0 When? (Time words)"
- "adjective" with label "\\u2b50 Describing Words (Adjectives)"
- "verb" with label "\\u26a1 Doing Words (Verbs)"
- "noun" with label "\\u25cf Things & Places (Nouns)"
- "name" with label "\\u2605 Names (Proper Nouns)"
- "open" with label "\\u270d Your Own Words" (ONLY for greater_depth level)""",

    "Maths": """WORD TYPES - Use these exact word_type values for colour-coding mathematical concepts:
- "operation" with label "\\u2795 Operations (+, -, \\u00d7, \\u00f7)"
- "shape" with label "\\u25b3 Shape & Space"
- "measure" with label "\\U0001f4cf Measurement"
- "number" with label "# Number & Place Value"
- "vocabulary" with label "\\u2b50 Maths Vocabulary"
- "open" with label "\\u270d Your Own Words" (ONLY for greater_depth level)""",

    "Science": """WORD TYPES - Use these exact word_type values for colour-coding scientific concepts:
- "process" with label "\\u2699 Scientific Processes"
- "equipment" with label "\\U0001f52c Equipment & Tools"
- "organism" with label "\\U0001f331 Living Things"
- "material" with label "\\U0001f9f1 Materials & Properties"
- "vocabulary" with label "\\u2b50 Science Vocabulary"
- "open" with label "\\u270d Your Own Words" (ONLY for greater_depth level)""",

    "History": """WORD TYPES - Use these exact word_type values for colour-coding historical concepts:
- "event" with label "\\U0001f4c5 Events"
- "person" with label "\\U0001f464 People"
- "place" with label "\\U0001f4cd Places"
- "date" with label "\\u23f3 Dates & Periods"
- "vocabulary" with label "\\u2b50 History Vocabulary"
- "open" with label "\\u270d Your Own Words" (ONLY for greater_depth level)""",

    "Geography": """WORD TYPES - Use these exact word_type values for colour-coding geographical concepts:
- "place" with label "\\U0001f4cd Places"
- "feature" with label "\\u26f0 Physical Features"
- "process" with label "\\u2699 Geographical Processes"
- "climate" with label "\\U0001f321 Climate & Weather"
- "vocabulary" with label "\\u2b50 Geography Vocabulary"
- "open" with label "\\u270d Your Own Words" (ONLY for greater_depth level)""",

    "Computing": """WORD TYPES - Use these exact word_type values for colour-coding computing concepts:
- "algorithm" with label "\\u2699 Algorithms"
- "data" with label "\\U0001f4ca Data"
- "hardware" with label "\\U0001f5a5 Hardware"
- "software" with label "\\U0001f4bb Software"
- "vocabulary" with label "\\u2b50 Computing Vocabulary"
- "open" with label "\\u270d Your Own Words" (ONLY for greater_depth level)""",

    "Languages": """WORD TYPES - Use these exact word_type values for colour-coding language learning:
- "noun" with label "\\u25cf Naming Words (Nouns)"
- "verb" with label "\\u26a1 Doing Words (Verbs)"
- "adjective" with label "\\u2b50 Describing Words (Adjectives)"
- "phrase" with label "\\U0001f4ac Phrases & Expressions"
- "vocabulary" with label "\\u2b50 Key Vocabulary"
- "open" with label "\\u270d Your Own Words" (ONLY for greater_depth level)""",
}

SUBJECT_CONTEXT = {
    "English": "This is an English language and literacy worksheet focusing on grammar, vocabulary, reading, or writing skills.",
    "Maths": "This is a mathematics worksheet. Use age-appropriate mathematical language and notation. Problems should involve real-world contexts where appropriate. Use UK spelling (e.g. 'centre' not 'center', 'colour' not 'color').",
    "Science": "This is a science worksheet. Use proper scientific terminology appropriate for the year group. Include observational and investigative thinking where appropriate.",
    "History": "This is a history worksheet. Use historically accurate content. Include dates, key figures, and cause-and-effect relationships. Help pupils understand chronology and historical significance.",
    "Geography": "This is a geography worksheet. Use correct geographical terminology. Include references to real places, features, and processes. Help pupils develop spatial awareness and understanding of human-environment interactions.",
    "Computing": "This is a computing worksheet. Use correct computing terminology (algorithm, variable, debug, etc.). Content should be practical and relate to real-world technology use where appropriate.",
    "Languages": "This is a foreign language learning worksheet. Include the target language words/phrases alongside English translations. Focus on building vocabulary, simple grammar patterns, and communication skills.",
}


# =============================================================================
# 1. CLOZE PROMPT - Fill-in-the-blank passage
# =============================================================================

CLOZE_PROMPT = """You are an expert UK primary school teacher creating a cloze (fill-in-the-blank) worksheet for {year_group} pupils (aged {age_range}).

CURRICULUM CONTEXT:
- Subject: {subject}
- Topic: {topic}
- Learning Objective: {objective}
- Theme: {theme_name} {theme_icon}
- Differentiation Level: {level}

{subject_context}

YOUR TASK:
Create an engaging cloze passage themed around "{theme_name}" that helps pupils work towards the learning objective. The passage should tell a coherent, imaginative story or explanation that weaves in key vocabulary and concepts from the curriculum objective.

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

{word_types_section}

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
          {{"type": "blank", "word_type": "<one of the word_type values listed above>", "answer": "<the correct word>", "hint": "<descriptive hint for expected/greater_depth>", "choices": ["<option1>", "<option2>", "<option3>"]}},
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
    subject: str = "English",
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
        subject: The curriculum subject (e.g. "English", "Maths", "Science")

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
        subject=subject,
        subject_context=SUBJECT_CONTEXT.get(subject, ""),
        word_types_section=SUBJECT_WORD_TYPES.get(subject, SUBJECT_WORD_TYPES["English"]),
    )


# =============================================================================
# 2. WORD_BANK PROMPT - Vocabulary exploration activities
# =============================================================================

WORD_BANK_PROMPT = """You are an expert UK primary school teacher creating a vocabulary / word bank worksheet for {year_group} pupils (aged {age_range}).

CURRICULUM CONTEXT:
- Subject: {subject}
- Topic: {topic}
- Learning Objective: {objective}
- Theme: {theme_name} {theme_icon}
- Differentiation Level: {level}

{subject_context}

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

{word_types_section}

YOU MUST OUTPUT VALID JSON matching this EXACT schema. Do not include any text outside the JSON object.

{{
  "title": "<A creative, engaging title for the vocabulary worksheet>",
  "categories": [
    {{
      "word_type": "<one of the word_type values listed above>",
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
    subject: str = "English",
) -> str:
    """Build a complete word bank worksheet prompt with all placeholders filled."""
    return WORD_BANK_PROMPT.format(
        year_group=year_group,
        topic=topic,
        objective=objective,
        age_range=age_range,
        theme_name=theme_name,
        theme_icon=theme_icon,
        level=level,
        subject=subject,
        subject_context=SUBJECT_CONTEXT.get(subject, ""),
        word_types_section=SUBJECT_WORD_TYPES.get(subject, SUBJECT_WORD_TYPES["English"]),
    )


# =============================================================================
# 3. MATCHING PROMPT - Word-to-definition matching activities
# =============================================================================

MATCHING_PROMPT = """You are an expert UK primary school teacher creating a matching / connecting worksheet for {year_group} pupils (aged {age_range}).

CURRICULUM CONTEXT:
- Subject: {subject}
- Topic: {topic}
- Learning Objective: {objective}
- Theme: {theme_name} {theme_icon}
- Differentiation Level: {level}

{subject_context}

YOUR TASK:
Create a matching activity worksheet themed around "{theme_name}" where pupils draw lines to connect related items (words to definitions, terms to explanations, concepts to examples, etc.). The content should support the curriculum learning objective.

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
    subject: str = "English",
) -> str:
    """Build a complete matching worksheet prompt with all placeholders filled."""
    return MATCHING_PROMPT.format(
        year_group=year_group,
        topic=topic,
        objective=objective,
        age_range=age_range,
        theme_name=theme_name,
        theme_icon=theme_icon,
        level=level,
        subject=subject,
        subject_context=SUBJECT_CONTEXT.get(subject, ""),
    )


# =============================================================================
# 4. SENTENCE_BUILDER PROMPT - Sentence construction exercises
# =============================================================================

SENTENCE_BUILDER_PROMPT = """You are an expert UK primary school teacher creating a sentence building worksheet for {year_group} pupils (aged {age_range}).

CURRICULUM CONTEXT:
- Subject: {subject}
- Topic: {topic}
- Learning Objective: {objective}
- Theme: {theme_name} {theme_icon}
- Differentiation Level: {level}

{subject_context}

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
    subject: str = "English",
) -> str:
    """Build a complete sentence builder worksheet prompt with all placeholders filled."""
    return SENTENCE_BUILDER_PROMPT.format(
        year_group=year_group,
        topic=topic,
        objective=objective,
        age_range=age_range,
        theme_name=theme_name,
        theme_icon=theme_icon,
        level=level,
        subject=subject,
        subject_context=SUBJECT_CONTEXT.get(subject, ""),
    )


# =============================================================================
# 5. READING_COMPREHENSION PROMPT - Reading passage with questions
# =============================================================================

READING_COMPREHENSION_PROMPT = """You are an expert UK primary school teacher creating a reading comprehension worksheet for {year_group} pupils (aged {age_range}).

CURRICULUM CONTEXT:
- Subject: {subject}
- Topic: {topic}
- Learning Objective: {objective}
- Theme: {theme_name} {theme_icon}
- Differentiation Level: {level}

{subject_context}

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
    subject: str = "English",
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
        subject=subject,
        subject_context=SUBJECT_CONTEXT.get(subject, ""),
    )


# =============================================================================
# 6. PROBLEM_SOLVING PROMPT - Maths word problems (Maths-specific)
# =============================================================================

PROBLEM_SOLVING_PROMPT = """You are an expert UK primary school teacher creating a maths problem solving worksheet for {year_group} pupils (aged {age_range}).

CURRICULUM CONTEXT:
- Subject: Maths
- Topic: {topic}
- Learning Objective: {objective}
- Theme: {theme_name} {theme_icon}
- Differentiation Level: {level}

{subject_context}

YOUR TASK:
Create a problem solving worksheet themed around "{theme_name}" that presents a real-world scenario followed by structured mathematical questions. The scenario should provide data and context that pupils use to answer questions of increasing difficulty.

DIFFERENTIATION LEVEL RULES - YOU MUST FOLLOW THESE EXACTLY:

If the level is "developing":
- Create a simple scenario with straightforward data (a table or list of 3-4 items with simple numbers)
- Include 4-5 questions, mostly "calculate" type with single-step operations
- Use small, manageable numbers appropriate for pupils who need extra support
- Each question should have a "word_bank" field with 1-2 hint words
- Questions should require 1-2 answer lines
- Marks should be 1 per question

If the level is "expected":
- Create a scenario with moderate data (a table or list of 4-6 items)
- Include 6-8 questions mixing "calculate", "explain", and "estimate" types
- Use age-appropriate numbers matching {year_group} expectations
- Do NOT include "word_bank" for any question
- Questions should require 2-3 answer lines
- Marks should be 1-2 per question

If the level is "greater_depth":
- Create a richer scenario with more complex data (a table with 5-8 items, multiple data points)
- Include 8-10 questions including "calculate", "explain", "estimate", and "prove" types
- Use challenging numbers and multi-step problems
- Do NOT include "word_bank" for any question
- Questions should require 2-4 answer lines
- Marks should be 1-3 per question

QUESTION TYPES - Use these exact values:
- "calculate" - perform a calculation and show working
- "explain" - explain reasoning or method
- "estimate" - make a reasonable estimate
- "prove" - prove or show that a statement is true/false

YOU MUST OUTPUT VALID JSON matching this EXACT schema. Do not include any text outside the JSON object.

{{
  "title": "<A creative, engaging title for the worksheet related to the theme>",
  "scenario": {{
    "title": "<Title of the scenario, e.g. The Space Station Shop>",
    "text": "<Description of the scenario. Use \\n\\n for paragraph breaks.>",
    "data": [
      {{"label": "<item name>", "value": "<number or amount, e.g. £2.50 or 24 kg>"}}
    ]
  }},
  "questions": [
    {{
      "number": 1,
      "question": "<the maths question>",
      "question_type": "<one of: calculate, explain, estimate, prove>",
      "marks": 1,
      "lines": 2,
      "answer": "<model answer with working shown>",
      "word_bank": ["<hint word>"]
    }}
  ],
  "success_criteria": [
    "<criterion 1 starting with 'I can...'>",
    "<criterion 2>",
    "<criterion 3>"
  ]
}}

CRITICAL RULES FOR THE JSON:
1. The "scenario" object must have "title" (string), "text" (string), and "data" (array of label/value objects).
2. For "developing" level: every question MUST have a "word_bank" field (array of 1-2 hint strings).
3. For "expected" and "greater_depth" levels: do NOT include "word_bank" in questions.
4. The "answer" field should contain a complete model answer showing working out.
5. Questions should progress from easier to harder.
6. success_criteria should have 3-5 pupil-friendly statements.
7. Make the scenario genuinely engaging and themed around {theme_name} {theme_icon}.
8. Ensure all questions can be answered using the data provided in the scenario.
9. Use UK currency (£ and p) and metric units where appropriate.

Generate the JSON now:"""


def get_problem_solving_prompt(
    year_group: str,
    topic: str,
    objective: str,
    age_range: str,
    theme_name: str,
    theme_icon: str,
    level: str,
    subject: str = "Maths",
) -> str:
    """Build a complete problem solving worksheet prompt with all placeholders filled."""
    return PROBLEM_SOLVING_PROMPT.format(
        year_group=year_group,
        topic=topic,
        objective=objective,
        age_range=age_range,
        theme_name=theme_name,
        theme_icon=theme_icon,
        level=level,
        subject_context=SUBJECT_CONTEXT.get("Maths", ""),
    )


# =============================================================================
# 7. CALCULATION_PRACTICE PROMPT - Maths calculation exercises (Maths-specific)
# =============================================================================

CALCULATION_PRACTICE_PROMPT = """You are an expert UK primary school teacher creating a calculation practice worksheet for {year_group} pupils (aged {age_range}).

CURRICULUM CONTEXT:
- Subject: Maths
- Topic: {topic}
- Learning Objective: {objective}
- Theme: {theme_name} {theme_icon}
- Differentiation Level: {level}

{subject_context}

YOUR TASK:
Create a calculation practice worksheet themed around "{theme_name}" with sections of progressively harder calculations. Each section should have clear instructions and space for working out.

DIFFERENTIATION LEVEL RULES - YOU MUST FOLLOW THESE EXACTLY:

If the level is "developing":
- Create 2-3 sections with 4-5 calculations each
- Use single-step calculations with small, manageable numbers
- Include visual hints or partially completed examples where appropriate
- Do NOT include a challenge section (set "challenge" to null)

If the level is "expected":
- Create 3-4 sections with 5-6 calculations each
- Use age-appropriate numbers matching {year_group} expectations
- Progress from simpler to more complex within each section
- Include a challenge section with 1-2 extension questions

If the level is "greater_depth":
- Create 4-5 sections with 6-8 calculations each
- Use challenging numbers and multi-step calculations
- Include reasoning questions (e.g. "What is the missing number?")
- Include a challenge section with 2-3 open-ended extension problems

YOU MUST OUTPUT VALID JSON matching this EXACT schema. Do not include any text outside the JSON object.

{{
  "title": "<A creative, engaging title for the worksheet related to the theme>",
  "sections": [
    {{
      "title": "<Section title, e.g. Warm-Up Calculations>",
      "instructions": "<Clear instructions, e.g. Calculate each answer. Show your working out.>",
      "calculations": [
        {{
          "question": "<The calculation, e.g. 345 + 278 = ___>",
          "answer": "<The correct answer, e.g. 623>",
          "working_hint": "<Optional hint for developing level, e.g. Use column addition. null for others>"
        }}
      ]
    }}
  ],
  "challenge": {{
    "title": "<Challenge section title, e.g. Brain Buster!>",
    "instructions": "<Instructions for the challenge>",
    "lines": 3
  }},
  "success_criteria": [
    "<criterion 1 starting with 'I can...'>",
    "<criterion 2>",
    "<criterion 3>"
  ]
}}

CRITICAL RULES FOR THE JSON:
1. Each section has "title" (string), "instructions" (string), and "calculations" (array).
2. Each calculation has "question" (string), "answer" (string), and "working_hint" (string or null).
3. For "developing" level: include "working_hint" for each calculation. Set "challenge" to null.
4. For "expected" and "greater_depth" levels: set "working_hint" to null. Include "challenge" object.
5. The "challenge" object has "title" (string), "instructions" (string), and "lines" (int).
6. Use the correct mathematical notation: + - x or \\u00d7 for multiplication, \\u00f7 for division.
7. Ensure all calculations are correctly solvable and age-appropriate.
8. success_criteria should have 3-5 pupil-friendly statements.
9. Theme section titles around {theme_name} {theme_icon} to make it engaging.

Generate the JSON now:"""


def get_calculation_practice_prompt(
    year_group: str,
    topic: str,
    objective: str,
    age_range: str,
    theme_name: str,
    theme_icon: str,
    level: str,
    subject: str = "Maths",
) -> str:
    """Build a complete calculation practice worksheet prompt with all placeholders filled."""
    return CALCULATION_PRACTICE_PROMPT.format(
        year_group=year_group,
        topic=topic,
        objective=objective,
        age_range=age_range,
        theme_name=theme_name,
        theme_icon=theme_icon,
        level=level,
        subject_context=SUBJECT_CONTEXT.get("Maths", ""),
    )


# =============================================================================
# 8. INVESTIGATION PROMPT - Science investigation planner (Science-specific)
# =============================================================================

INVESTIGATION_PROMPT = """You are an expert UK primary school teacher creating a science investigation planning worksheet for {year_group} pupils (aged {age_range}).

CURRICULUM CONTEXT:
- Subject: Science
- Topic: {topic}
- Learning Objective: {objective}
- Theme: {theme_name} {theme_icon}
- Differentiation Level: {level}

{subject_context}

YOUR TASK:
Create a science investigation planner worksheet themed around "{theme_name}" that guides pupils through planning and recording a scientific investigation. The investigation should be linked to the curriculum topic and learning objective.

DIFFERENTIATION LEVEL RULES - YOU MUST FOLLOW THESE EXACTLY:

If the level is "developing":
- Provide the investigation question, prediction, and variable identification pre-filled or with multiple choice
- Include 3-4 simple method steps
- Provide a results table with 2-3 columns and 3-4 rows
- Include 2-3 simple conclusion prompts with sentence starters
- Use simple, accessible language

If the level is "expected":
- Provide the investigation question but let pupils write their own prediction
- Include guidance for identifying variables (what to change, measure, keep the same)
- Include 4-6 method steps
- Provide a results table with 3-4 columns and 4-5 rows
- Include 3-4 conclusion prompts
- Use age-appropriate scientific language

If the level is "greater_depth":
- Provide context but let pupils formulate their own question and prediction
- Expect pupils to identify variables independently (with prompts)
- Include 5-7 method steps with emphasis on fair testing
- Provide a results table with 4-5 columns and 5-6 rows
- Include 4-5 conclusion prompts requiring analysis and evaluation
- Use ambitious scientific vocabulary

YOU MUST OUTPUT VALID JSON matching this EXACT schema. Do not include any text outside the JSON object.

{{
  "title": "<A creative, engaging title for the investigation worksheet>",
  "investigation": {{
    "question": "<The investigation question, e.g. How does the height affect how far a ball rolls?>",
    "prediction": "<A sentence starter for prediction, e.g. I predict that... OR a full prediction for developing>",
    "prediction_choices": ["<choice 1>", "<choice 2>", "<choice 3>"],
    "variables": {{
      "change": "<What we will change (independent variable)>",
      "measure": "<What we will measure (dependent variable)>",
      "keep_same": ["<control variable 1>", "<control variable 2>", "<control variable 3>"]
    }}
  }},
  "equipment": ["<item 1>", "<item 2>", "<item 3>"],
  "method": ["<Step 1>", "<Step 2>", "<Step 3>"],
  "results_table": {{
    "columns": ["<Column 1 heading>", "<Column 2 heading>", "<Column 3 heading>"],
    "rows": 4,
    "units": ["<unit for col 1 or empty>", "<unit for col 2>", "<unit for col 3>"]
  }},
  "conclusion_prompts": [
    "<Prompt or sentence starter, e.g. I found out that...>",
    "<Prompt, e.g. My prediction was correct/incorrect because...>",
    "<Prompt, e.g. If I did this investigation again, I would...>"
  ],
  "success_criteria": [
    "<criterion 1 starting with 'I can...'>",
    "<criterion 2>",
    "<criterion 3>"
  ]
}}

CRITICAL RULES FOR THE JSON:
1. For "developing" level: include "prediction_choices" (array of 3 strings) for multiple choice. Pre-fill "prediction" with a complete prediction.
2. For "expected" and "greater_depth" levels: set "prediction_choices" to null. "prediction" should be a sentence starter (e.g. "I predict that...").
3. The "variables" object must have "change" (string), "measure" (string), and "keep_same" (array of strings).
4. "equipment" is an array of strings listing what pupils need.
5. "method" is an array of strings, each being a numbered step.
6. "results_table" has "columns" (array of column heading strings), "rows" (integer - number of data rows), and "units" (array of unit strings matching columns).
7. "conclusion_prompts" is an array of sentence starters or guided questions.
8. success_criteria should have 3-5 pupil-friendly statements.
9. Make the investigation practical, safe, and achievable in a classroom setting.
10. Theme the investigation around {theme_name} {theme_icon} where possible.
11. Ensure the investigation genuinely tests the curriculum learning objective.

Generate the JSON now:"""


def get_investigation_prompt(
    year_group: str,
    topic: str,
    objective: str,
    age_range: str,
    theme_name: str,
    theme_icon: str,
    level: str,
    subject: str = "Science",
) -> str:
    """Build a complete investigation planner prompt with all placeholders filled."""
    return INVESTIGATION_PROMPT.format(
        year_group=year_group,
        topic=topic,
        objective=objective,
        age_range=age_range,
        theme_name=theme_name,
        theme_icon=theme_icon,
        level=level,
        subject_context=SUBJECT_CONTEXT.get("Science", ""),
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
    "problem_solving": get_problem_solving_prompt,
    "calculation_practice": get_calculation_practice_prompt,
    "investigation": get_investigation_prompt,
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
    "problem_solving": "problem_solving",
    "word_problems": "problem_solving",
    "problems": "problem_solving",
    "calculation_practice": "calculation_practice",
    "calculations": "calculation_practice",
    "calc_practice": "calculation_practice",
    "investigation": "investigation",
    "investigation_planner": "investigation",
    "science_investigation": "investigation",
}


def get_prompt(worksheet_type: str, **kwargs) -> str:
    """
    Get the appropriate prompt for the given worksheet type.

    This is a convenience function that dispatches to the correct
    prompt-building function based on the worksheet type name.

    Args:
        worksheet_type: The type of worksheet to generate.
        **kwargs: Keyword arguments passed to the prompt function:
            - year_group (str): e.g. "Year 3"
            - topic (str): e.g. "Writing - Myths & Legends"
            - objective (str): e.g. "Plan, draft, and write narratives..."
            - age_range (str): e.g. "7-8"
            - theme_name (str): e.g. "Space Explorer"
            - theme_icon (str): e.g. "rocket emoji"
            - level (str): One of "developing", "expected", or "greater_depth"
            - subject (str): e.g. "English", "Maths", "Science" (default: "English")

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
