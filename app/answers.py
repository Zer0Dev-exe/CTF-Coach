"""Normalización de respuestas de las salas (compartida por el script de construcción y el servidor)."""

import hashlib
import re
import unicodedata


def normalize(answer: str) -> str:
    s = unicodedata.normalize("NFKD", answer.strip().casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s).strip(" .\"'`")
    return s


def answer_hash(answer: str) -> str:
    return hashlib.sha256(normalize(answer).encode()).hexdigest()


def mask(answer: str) -> str:
    """Máscara al estilo THM: cada letra o dígito se convierte en '*', el resto se mantiene."""
    return re.sub(r"\w", "*", answer)
