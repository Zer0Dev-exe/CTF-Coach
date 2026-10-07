"""Extracción de características de un texto para identificar su codificación o cifrado.

Además de mirar el texto tal cual, se normaliza (quitando separadores como espacios, ':' o '0x' en
hexadecimal, o aceptando Base64 de URL sin relleno) y se analiza el contenido decodificado: el hex de
un texto da algo legible, mientras que el hex de un XOR da bytes sin sentido aunque sean imprimibles.
"""

import base64
import binascii
import math
import re
import string
from collections import Counter

import numpy as np

# Frecuencia de letras en español (%), sin la ñ.
SPANISH_FREQ = dict(zip(string.ascii_lowercase, [
    12.53, 1.42, 4.68, 5.86, 13.68, 0.69, 1.01, 0.70, 6.25, 0.44, 0.02, 4.97, 3.15,
    6.71, 8.68, 2.51, 0.88, 6.87, 7.98, 4.63, 3.93, 0.90, 0.01, 0.22, 0.90, 0.52,
]))
EXPECTED = np.array([SPANISH_FREQ[c] for c in string.ascii_lowercase]) / 100

# Bigramas muy frecuentes en español e inglés: sirven para detectar texto legible o invertido.
COMMON_BIGRAMS = {"de", "es", "en", "el", "la", "os", "ar", "ue", "ra", "re", "er", "as", "on", "st",
                  "ad", "al", "or", "ta", "co", "nt", "an", "do", "qu", "ci", "se", "to",
                  "th", "he", "in", "ed", "nd", "ha", "at", "ou", "it", "is", "ng"}

# Palabras muy comunes (español, inglés y jerga técnica) para medir si el texto "se lee".
COMMON_WORDS = set("""
de la que el en y a los se del las un por con no una su para es al lo como mas pero sus le ya o este si
porque esta entre cuando muy sin sobre también me hasta hay donde quien desde todo nos durante todos uno les
ni contra otros ese eso ante ellos e esto mi antes algunos unos yo otro otras otra tanto esa estos mucho
the of and to in is it you that he was for on are as with his they at be this have from or one had by but
not what all were we when your can said there use an each which she do how their if will up other about out
user password login failed accepted from port root admin error warning denied access server session key
secret token http get post html head body title form input button flag hola mensaje clave mundo hello world
""".split())

HEX = set(string.hexdigits)
B64 = set(string.ascii_letters + string.digits + "+/=")
B64URL = set(string.ascii_letters + string.digits + "-_=")
B32 = set(string.ascii_uppercase + "234567=")
MORSE = set(".-/ \n")

# Hex con separadores: "48 6f", "48:6f", "0x48 0x6f", "\x48\x6f"
HEX_SEPARATED = re.compile(r"(?:0x|\\x)?[0-9a-fA-F]{2}(?:[\s:,\-]*(?:0x|\\x)?[0-9a-fA-F]{2})*")

FEATURE_NAMES = [
    "longitud (log)", "% mayúsculas", "% minúsculas", "% dígitos", "% espacios", "% símbolos",
    "solo hex", "solo base64", "solo base32", "relleno '='", "longitud % 4 == 0", "longitud % 8 == 0",
    "entropía", "índice de coincidencia", "chi² español", "chi² mejor César", "ganancia César",
    "chi² Atbash", "bigramas", "bigramas invertido", "forma JWT", "orden de llaves", "% caracteres únicos",
    "palabras conocidas", "palabras conocidas invertido",
    "hex válido (normalizado)", "hex con separadores", "hex → imprimible", "hex → legible", "hex → otra codificación",
    "hex: 32 car.", "hex: 40 car.", "hex: 64 car.",
    "base64 válido (normalizado)", "base64 de URL", "base64 → imprimible", "base64 → legible", "base64 → otra codificación",
    "base32 válido", "base32 → imprimible", "base32 → legible",
    "solo 0 y 1", "bits múltiplo de 8", "% secuencias %XX", "alfabeto Morse",
]


def _letters(text: str) -> str:
    return "".join(c for c in text.lower() if "a" <= c <= "z")


def _letter_counts(letters: str) -> np.ndarray:
    counts = np.zeros(26)
    for c, v in Counter(letters).items():
        counts[ord(c) - 97] = v
    return counts


def _chi2(counts: np.ndarray) -> float:
    total = counts.sum()
    if total < 4:
        return 5.0
    expected = EXPECTED * total
    return float(np.sum((counts - expected) ** 2 / expected) / total)


def _bigram_score(text: str) -> float:
    t = text.lower()
    pairs = [t[i:i + 2] for i in range(len(t) - 1)]
    pairs = [p for p in pairs if p.isalpha()]
    return sum(p in COMMON_BIGRAMS for p in pairs) / len(pairs) if pairs else 0.0


def _known_words(text: str) -> float:
    words = [w for w in "".join(c if c.isalpha() else " " for c in text.lower()).split() if len(w) > 1]
    return sum(w in COMMON_WORDS for w in words) / len(words) if words else 0.0


def _printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    return sum(32 <= b < 127 or b in (9, 10, 13) or b >= 0xC2 for b in data) / len(data)


def _decoded_quality(data: bytes | None) -> tuple[float, float, float]:
    """(imprimible, legible, parece otra codificación) del contenido decodificado; -1 si no se pudo decodificar."""
    if data is None:
        return -1.0, -1.0, -1.0
    printable = _printable_ratio(data)
    text = data.decode("utf-8", errors="replace")
    readable = max(_known_words(text), min(1.0, _bigram_score(text) * 2.2), 1.0 if "flag{" in text.lower() else 0.0)
    compact = re.sub(r"\s", "", text)
    inner = float(len(compact) >= 4 and (set(compact) <= HEX or set(compact) <= B64 or set(compact) <= B64URL))
    return printable, readable * printable, inner


def normalize_hex(text: str) -> str | None:
    if not HEX_SEPARATED.fullmatch(text):
        return None
    compact = re.sub(r"0x|\\x|[\s:,\-]", "", text, flags=re.IGNORECASE)
    return compact if len(compact) % 2 == 0 and set(compact) <= HEX else None


def _decode_hex(compact: str | None) -> bytes | None:
    return bytes.fromhex(compact) if compact else None


def _decode_b64(text: str) -> tuple[bytes | None, bool]:
    compact = re.sub(r"\s", "", text)
    if len(compact) < 4:
        return None, False
    url = bool(set(compact) <= B64URL and set(compact) & set("-_"))
    if not (set(compact) <= B64 or url):
        return None, False
    body = compact.rstrip("=")
    if "=" in body or len(body) % 4 == 1:
        return None, False
    try:
        data = base64.b64decode(body.replace("-", "+").replace("_", "/") + "=" * (-len(body) % 4), validate=True)
    except (ValueError, binascii.Error):
        return None, False
    return data, url


def _decode_b32(text: str) -> bytes | None:
    compact = re.sub(r"\s", "", text)
    if len(compact) < 8 or not set(compact) <= B32:
        return None
    try:
        return base64.b32decode(compact + "=" * (-len(compact) % 8))
    except (ValueError, binascii.Error):
        return None


def extract(text: str) -> np.ndarray:
    text = text.strip()
    n = max(len(text), 1)
    chars = set(text)
    letters = _letters(text)

    counts = Counter(text)
    entropy = -sum(c / n * math.log2(c / n) for c in counts.values()) if text else 0.0
    lc = Counter(letters)
    L = len(letters)
    ioc = sum(v * (v - 1) for v in lc.values()) / (L * (L - 1)) if L > 1 else 0.0

    counts_arr = _letter_counts(letters)
    chi_plain = _chi2(counts_arr)
    chi_best = min(_chi2(np.roll(counts_arr, k)) for k in range(26))  # rotar = descifrar César
    chi_atbash = _chi2(counts_arr[::-1])  # Atbash = alfabeto en espejo

    open_i, close_i = text.find("{"), text.find("}")
    braces = 0 if open_i < 0 or close_i < 0 else (1 if open_i < close_i else -1)
    parts = text.split(".")
    jwt = float(len(parts) == 3 and text.startswith("eyJ") and all(parts))

    hex_compact = normalize_hex(text)
    hex_q = _decoded_quality(_decode_hex(hex_compact))
    b64_data, b64_url = _decode_b64(text) if not hex_compact or len(hex_compact) % 4 == 0 else (None, False)
    b64_q = _decoded_quality(b64_data)
    b32_q = _decoded_quality(_decode_b32(text))
    hex_len = len(hex_compact) if hex_compact else 0

    bits = re.sub(r"\s", "", text)
    binary = float(len(bits) >= 8 and set(bits) <= {"0", "1"})
    pct = len(re.findall(r"%[0-9A-Fa-f]{2}", text)) * 3 / n

    return np.array([
        math.log1p(len(text)),
        sum(c.isupper() for c in text) / n,
        sum(c.islower() for c in text) / n,
        sum(c.isdigit() for c in text) / n,
        text.count(" ") / n,
        sum(not c.isalnum() and c != " " for c in text) / n,
        float(chars <= HEX),
        float(chars <= B64),
        float(chars <= B32),
        len(text) - len(text.rstrip("=")),
        float(len(text) % 4 == 0),
        float(len(text) % 8 == 0),
        entropy,
        ioc,
        min(chi_plain, 5.0),
        min(chi_best, 5.0),
        min(chi_plain - chi_best, 5.0),
        min(chi_atbash, 5.0),
        _bigram_score(text),
        _bigram_score(text[::-1]),
        jwt,
        braces,
        len(chars) / n,
        _known_words(text),
        _known_words(text[::-1]),
        float(hex_compact is not None),
        float(hex_compact is not None and hex_compact != text),
        *hex_q,
        float(hex_len == 32), float(hex_len == 40), float(hex_len == 64),
        float(b64_data is not None),
        float(b64_url),
        *b64_q,
        float(b32_q[0] >= 0),
        *b32_q[:2],
        binary,
        float(binary and len(bits) % 8 == 0),
        min(pct, 1.0),
        float(len(text) >= 3 and chars <= MORSE and ("." in chars or "-" in chars)),
    ], dtype=np.float32)


def letter_frequencies(text: str) -> np.ndarray:
    """Frecuencia relativa (0-1) de cada letra a-z en el texto."""
    counts = _letter_counts(_letters(text))
    return counts / counts.sum() if counts.sum() else counts
