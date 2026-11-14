"""
Heuristic detectors for programming language and error type. These are
fast, offline, regex/keyword based first-pass filters that feed the Code
Extraction Agent and Error Analysis Agent; the LLM refines/confirms afterwards.
"""
import re

LANGUAGE_SIGNATURES = {
    "Python": [
        r"\bdef\s+\w+\s*\(", r"\bimport\s+\w+", r"\bprint\s*\(",
        r"Traceback \(most recent call last\)", r":\s*$", r"\bself\b",
        r"\belif\b", r"\bNone\b",
    ],
    "Java": [
        r"\bpublic\s+class\b", r"\bSystem\.out\.println", r"\bpublic static void main",
        r"\bnew\s+\w+\s*\(", r";\s*$", r"\bimport\s+java\.",
    ],
    "JavaScript": [
        r"\bconst\s+\w+\s*=", r"\blet\s+\w+\s*=", r"\bfunction\s*\(",
        r"console\.log\(", r"=>\s*\{", r"\brequire\(", r"\bexport\s+default\b",
        r"\.jsx?:\d+", r"at\s+\w+\s*\(.*\.jsx?", r"Cannot read propert",
        r"is not a function", r"undefined is not",
    ],
    "C++": [
        r"#include\s*<\w+>", r"\bstd::", r"\bcout\s*<<", r"\bint\s+main\s*\(",
        r"\bnamespace\s+\w+",
    ],
    "C": [
        r"#include\s*<stdio\.h>", r"\bprintf\s*\(", r"\bint\s+main\s*\(",
        r"\bmalloc\s*\(",
    ],
    "SQL": [
        r"\bSELECT\b.*\bFROM\b", r"\bINSERT\s+INTO\b", r"\bCREATE\s+TABLE\b",
        r"\bWHERE\b", r"\bJOIN\b",
    ],
    "HTML/CSS": [
        r"<html", r"<div", r"</\w+>", r"\{\s*[\w-]+\s*:\s*[^;]+;\s*\}",
    ],
}

# Ordered roughly by specificity so we can pick the strongest match first.
ERROR_PATTERNS = {
    "Python": [
        "SyntaxError", "NameError", "TypeError", "ValueError", "IndexError",
        "KeyError", "ImportError", "ModuleNotFoundError", "RuntimeError",
        "AttributeError", "ZeroDivisionError", "IndentationError",
        "FileNotFoundError", "RecursionError",
    ],
    "Java": [
        "NullPointerException", "ArrayIndexOutOfBoundsException",
        "ClassNotFoundException", "ClassCastException", "NumberFormatException",
        "StackOverflowError", "compilation error",
    ],
    "JavaScript": [
        "TypeError", "ReferenceError", "SyntaxError", "RangeError",
        "is not a function", "is not defined", "Cannot read propert",
        "UnhandledPromiseRejection",
    ],
    "C++": ["segmentation fault", "undefined reference", "error:", "terminate called"],
    "C": ["segmentation fault", "undefined reference", "error:"],
    "SQL": ["syntax error at or near", "no such table", "ORA-", "SQLSTATE"],
    "Generic": ["Error:", "Exception:", "failed", "Fatal error"],
}

# Distinctive phrasing that disambiguates error names shared across languages
# (e.g. "TypeError" exists in both Python and JavaScript).
DISAMBIGUATORS = [
    (r"Cannot read propert", "TypeError", "JavaScript"),
    (r"is not a function", "TypeError", "JavaScript"),
    (r"undefined is not", "TypeError", "JavaScript"),
    (r"NoneType", "TypeError", "Python"),
    (r"unsupported operand type", "TypeError", "Python"),
]


def detect_language(text: str) -> str:
    scores = {}
    for lang, patterns in LANGUAGE_SIGNATURES.items():
        score = sum(1 for p in patterns if re.search(p, text, re.MULTILINE))
        if score:
            scores[lang] = score
    if not scores:
        return "Unknown"
    return max(scores, key=scores.get)


def detect_error(text: str, language_hint: str = None):
    """Returns (error_type, matched_language) or (None, None) if no error found."""
    for pattern, err, lang in DISAMBIGUATORS:
        if re.search(pattern, text, re.IGNORECASE):
            return err, lang

    search_order = [language_hint] if language_hint in ERROR_PATTERNS else []
    search_order += [l for l in ERROR_PATTERNS if l != language_hint]

    for lang in search_order:
        for err in ERROR_PATTERNS[lang]:
            if re.search(re.escape(err), text, re.IGNORECASE):
                return err, lang
    return None, None


def looks_like_code_or_error(text: str) -> bool:
    """Quick gate used by the live monitor to decide whether to bother the
    AI pipeline at all (avoid burning API calls on e.g. a browser tab)."""
    if not text or len(text.strip()) < 5:
        return False
    signal_words = ["def ", "class ", "function", "error", "exception",
                    "traceback", "{", "}", ";", "import ", "SELECT ", "print("]
    return any(s.lower() in text.lower() for s in signal_words)
