"""
Realistic worksheet content for every worksheet type.

These mirror the JSON schemas the prompts in ``llm/prompts.py`` ask Claude to
return, so the document generators are exercised on the shape they actually
receive in production -- no API key and no network needed.

Keep these in step with the prompt schemas. If a prompt gains a field the
generators read, add it here too, or the tests will pass while production
breaks.
"""

_SUCCESS_CRITERIA = [
    "I can use interesting adjectives to describe a setting.",
    "I can punctuate my sentences correctly.",
    "I can read my work back and improve one word.",
]

CLOZE = {
    "title": "The Lost Planet",
    "sections": [
        {
            "title": "THE BEGINNING",
            "reminder": "Think about how your story starts!",
            "paragraphs": [
                [
                    {"type": "text", "text": "The rocket landed on the "},
                    {
                        "type": "blank",
                        "word_type": "adjective",
                        "answer": "dusty",
                        "hint": "a describing word about the surface",
                        "choices": ["dusty", "loud", "quickly"],
                    },
                    {"type": "text", "text": " surface of the planet."},
                ],
                [
                    {"type": "text", "text": "Aisha "},
                    {
                        "type": "blank",
                        "word_type": "verb",
                        "answer": "scrambled",
                        "hint": "a doing word",
                        "choices": ["scrambled", "silent", "bravely"],
                    },
                    {"type": "text", "text": " down the ladder."},
                ],
            ],
        }
    ],
    "word_bank": [
        {
            "word_type": "adjective",
            "label": "Describing word",
            "words": [
                {"word": "dusty", "definition": "covered in fine dry dirt"},
                {"word": "enormous", "definition": "very, very big"},
            ],
        },
        {
            "word_type": "verb",
            "label": "Doing word",
            "words": [
                {"word": "scrambled", "definition": "climbed quickly using hands and feet"},
            ],
        },
    ],
    "success_criteria": _SUCCESS_CRITERIA,
}

WORD_BANK = {
    "title": "Words for the Deep Ocean",
    "categories": [
        {
            "word_type": "noun",
            "label": "Naming word",
            "words": [
                {"word": "current", "definition": "water moving in one direction"},
                {"word": "reef", "definition": "a ridge of coral near the surface"},
            ],
        },
        {
            "word_type": "adjective",
            "label": "Describing word",
            "words": [{"word": "murky", "definition": "dark and hard to see through"}],
        },
    ],
    "activities": [
        {
            "title": "Fill in the Gaps",
            "instructions": "Choose the best word from the word bank for each gap.",
            "sentences": [
                {
                    "pieces": [
                        {"type": "text", "text": "The diver swam over the colourful "},
                        {
                            "type": "blank",
                            "word_type": "noun",
                            "answer": "reef",
                            "hint": "a naming word",
                            "choices": ["reef", "murky", "swam"],
                        },
                        {"type": "text", "text": "."},
                    ]
                }
            ],
        }
    ],
    "success_criteria": _SUCCESS_CRITERIA,
}

MATCHING = {
    "title": "Word Detective",
    "activities": [
        {
            "title": "Match the Words to Their Meanings",
            "instructions": "Draw a line to match each word to its meaning.",
            "pairs": [
                {"left": "ancient", "right": "very old"},
                {"left": "fragile", "right": "easily broken"},
                {"left": "vast", "right": "extremely large"},
            ],
        }
    ],
    "bonus_activity": {
        "title": "Challenge Time!",
        "instructions": "Choose three words from above and use each in your own sentence.",
        "lines": 3,
    },
    "success_criteria": _SUCCESS_CRITERIA,
}

SENTENCE_BUILDER = {
    "title": "Sentence Builders",
    "exercises": [
        {
            "title": "Build a Sentence",
            "instructions": "Arrange these words to make a sentence.",
            "sentence_parts": [
                {"part": "The explorer", "word_type": "noun"},
                {"part": "climbed", "word_type": "verb"},
                {"part": "carefully", "word_type": "adverb"},
                {"part": "up the steep cliff", "word_type": "preposition"},
                {"part": ".", "word_type": "punctuation"},
            ],
            "correct_sentence": "The explorer climbed carefully up the steep cliff.",
        }
    ],
    "extension": {
        "title": "Now Try Your Own!",
        "instructions": "Write your own sentence using a word of each kind.",
        "lines": 3,
    },
    "success_criteria": _SUCCESS_CRITERIA,
}

READING_COMPREHENSION = {
    "title": "The Lighthouse Keeper",
    "passage": {
        "title": "A Light in the Storm",
        "text": (
            "Every evening, Maren climbed the ninety-two steps to the lamp room.\n\n"
            "The lamp had burned without fail for sixty years, and she did not "
            "intend to be the keeper who let it go dark."
        ),
        "source_note": None,
    },
    "vocabulary": [
        {"word": "keeper", "definition": "a person who looks after something", "word_type": "noun"},
        {"word": "climbed", "definition": "went up", "word_type": "verb"},
    ],
    "questions": [
        {
            "number": 1,
            "question": "How many steps did Maren climb?",
            "question_type": "retrieval",
            "marks": 1,
            "lines": 1,
            "answer": "Ninety-two.",
            "word_bank": ["ninety-two"],
        },
        {
            "number": 2,
            "question": "Why do you think Maren felt the lamp mattered so much?",
            "question_type": "inference",
            "marks": 2,
            "lines": 3,
            "answer": "It had burned for sixty years and ships relied on it.",
            "word_bank": ["sixty", "ships"],
        },
    ],
    "success_criteria": _SUCCESS_CRITERIA,
}

PROBLEM_SOLVING = {
    "title": "The Space Station Shop",
    "scenario": {
        "title": "The Space Station Shop",
        "text": "The crew shop sells supplies.\n\nUse the price list to answer the questions.",
        "data": [
            {"label": "Water pouch", "value": "£2.50"},
            {"label": "Ration pack", "value": "£4.20"},
            {"label": "Oxygen filter", "value": "£11.00"},
        ],
    },
    "questions": [
        {
            "number": 1,
            "question": "Sam buys two water pouches. How much does he spend?",
            "question_type": "calculate",
            "marks": 1,
            "lines": 2,
            "answer": "£5.00 (2 x £2.50)",
            "word_bank": ["double"],
        },
        {
            "number": 2,
            "question": "Explain how you could estimate the cost of three ration packs.",
            "question_type": "explain",
            "marks": 2,
            "lines": 3,
            "answer": "Round £4.20 to £4 and multiply by 3 to get about £12.",
            "word_bank": ["round", "estimate"],
        },
    ],
    "success_criteria": _SUCCESS_CRITERIA,
}

CALCULATION_PRACTICE = {
    "title": "Jungle Calculation Quest",
    "sections": [
        {
            "title": "Warm-Up Calculations",
            "instructions": "Calculate each answer. Show your working out.",
            "calculations": [
                {"question": "345 + 278 = ___", "answer": "623", "working_hint": "Use column addition."},
                {"question": "802 - 517 = ___", "answer": "285", "working_hint": None},
                {"question": "46 x 7 = ___", "answer": "322", "working_hint": None},
            ],
        }
    ],
    "challenge": {
        "title": "Brain Buster!",
        "instructions": "Find two three-digit numbers with a difference of 199.",
        "lines": 3,
    },
    "success_criteria": _SUCCESS_CRITERIA,
}

FRACTION_PRACTICE = {
    "title": "Fraction Space Mission",
    "sections": [
        {
            "title": "Equivalent Fractions",
            "instructions": "Find the missing number to make these fractions equal.",
            "type": "equivalent",
            "exercises": [
                {
                    "question": "1/2 = ___/8",
                    "answer": "4/8",
                    "visual_hint": "Think of a bar split into eight equal parts.",
                    "diagram": {"shaded": 4, "total": 8},
                },
                {
                    "question": "1/4 + 2/4 = ___",
                    "answer": "3/4",
                    "visual_hint": None,
                    "diagram": {"shaded": 3, "total": 4},
                },
            ],
        }
    ],
    "challenge": {
        "title": "Fraction Brain Buster!",
        "instructions": "Write three fractions equivalent to 2/3.",
        "lines": 3,
    },
    "success_criteria": _SUCCESS_CRITERIA,
}

TIMES_TABLES = {
    "title": "Jungle Times Tables Quest",
    "sections": [
        {
            "title": "The 4 Times Table",
            "instructions": "Answer each fact. Write your answer on the line.",
            "tables_focus": "4 times table",
            "facts": [
                {"question": "3 x 4 = ___", "answer": "12"},
                {"question": "7 x 4 = ___", "answer": "28"},
                {"question": "9 x 4 = ___", "answer": "36"},
            ],
        }
    ],
    "speed_challenge": {
        "title": "Final Sprint!",
        "instructions": "Answer as many as you can before the timer runs out!",
        "time_limit_seconds": 60,
        "facts": [
            {"question": "6 x 4 = ___", "answer": "24"},
            {"question": "8 x 4 = ___", "answer": "32"},
        ],
    },
    "success_criteria": _SUCCESS_CRITERIA,
}

INVESTIGATION = {
    "title": "Rolling Down the Ramp",
    "investigation": {
        "question": "How does the height of a ramp affect how far a ball rolls?",
        "prediction": "I predict that...",
        "prediction_choices": [
            "The ball will roll further from a higher ramp.",
            "The ball will roll the same distance every time.",
            "The ball will roll less far from a higher ramp.",
        ],
        "variables": {
            "change": "The height of the ramp",
            "measure": "How far the ball rolls",
            "keep_same": ["The same ball", "The same floor surface", "The same ramp"],
        },
    },
    "equipment": ["A ramp", "A tennis ball", "A metre stick", "Books to raise the ramp"],
    "method": [
        "Set the ramp to 10 cm high.",
        "Roll the ball from the top without pushing.",
        "Measure how far it travels and record the distance.",
        "Repeat with the ramp at 20 cm and 30 cm.",
    ],
    "results_table": {
        "columns": ["Ramp height", "Distance rolled", "Distance rolled (repeat)"],
        "rows": 4,
        "units": ["cm", "cm", "cm"],
    },
    "conclusion_prompts": [
        "What did you find out?",
        "Did your results match your prediction?",
        "What would you change if you did this again?",
    ],
    "success_criteria": [
        "I can make a prediction and explain my reasoning.",
        "I can identify what to change and what to keep the same.",
        "I can record my results clearly in a table.",
    ],
}

# Maps the worksheet type key (as used in app.py's GENERATOR_MAP) to its content.
ALL_CONTENT = {
    "cloze": CLOZE,
    "word_bank": WORD_BANK,
    "matching": MATCHING,
    "sentence_builder": SENTENCE_BUILDER,
    "reading_comprehension": READING_COMPREHENSION,
    "problem_solving": PROBLEM_SOLVING,
    "calculation_practice": CALCULATION_PRACTICE,
    "fraction_practice": FRACTION_PRACTICE,
    "times_tables": TIMES_TABLES,
    "investigation": INVESTIGATION,
}
