"""Separate fictional speech from quotations attributed to real thinkers.

This is an attribution guard, not a quotation-authenticity verifier. Named attributions
need source verification; quotation marks alone never make narration invalid.
"""
import re

# Explicitly recognized people, not arbitrary capitalized character names.
PEOPLE = (
    r"Marcus\s+Aurelius|Simone\s+de\s+Beauvoir|William\s+James|"
    r"Viktor\s+Frankl|Carl\s+Jung|Sigmund\s+Freud|"
    r"Socrates|Plato|Aristotle|Epictetus|Seneca|Nietzsche|"
    r"Kierkegaard|Schopenhauer|Descartes|Spinoza|Kant|"
    r"Camus|Sartre|Freud|Jung|Confucius|Lao\s+Tzu"
)
PERSON = rf"(?:{PEOPLE})"
QUOTE = r'''(?:"[^"\n]+"|“[^”\n]+”|‘[^’\n]+’|'[^'\n]+')'''
VERB = r"(?:said|says|wrote|writes|stated|states|argued|argues|observed|noted|declared)"
FORWARD = re.compile(
    rf"\b{PERSON}\b\s+(?:(?:once|famously)\s+)?{VERB}\s*[,:\-—]?\s*{QUOTE}",
    re.I,
)
REVERSE = re.compile(
    rf"{QUOTE}\s*[,;:\-—–]?\s*(?:{VERB}\s+)?{PERSON}\b",
    re.I,
)


def has_attributed_quotation(text):
    """Flag recognized real-person attributions for verification, not fictional dialogue."""
    return bool(FORWARD.search(text) or REVERSE.search(text))
