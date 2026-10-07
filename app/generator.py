"""Generación procedural de retos (100 % local, sin servicios externos).

A partir del tema que escribe el usuario se elige una cadena de transformaciones según la
dificultad, se monta una historia con pistas sutiles sobre cada transformación, se genera
una flag aleatoria y se comprueba que el reto se puede resolver deshaciendo los pasos.
"""

import hashlib
import random
import re
import secrets
import unicodedata
from typing import Literal

from pydantic import BaseModel

from .transforms import apply, invert

Op = Literal["base64", "base32", "hex", "rot13", "caesar", "atbash", "reverse", "xor"]
Difficulty = Literal["Fácil", "Media", "Difícil"]

STEP_RANGE = {"Fácil": (1, 2), "Media": (2, 3), "Difícil": (3, 5)}
POINTS = {"Fácil": 100, "Media": 200, "Difícil": 300}
ENCODINGS = {"base64", "base32", "hex"}
CIPHERS = {"caesar", "rot13", "atbash", "xor"}

THEMES = ["piratas", "espacio", "Egipto", "dragones", "espías", "la Antártida", "un museo", "el océano",
          "una biblioteca", "un faro", "el desierto", "una estación de tren", "robots", "la selva"]

NAMES = {
    "base64": "Base64", "base32": "Base32", "hex": "hexadecimal", "rot13": "ROT13", "caesar": "cifrado César",
    "atbash": "Atbash", "reverse": "texto invertido", "xor": "XOR con una clave de un byte",
}
# Cómo se reconoce cada capa a simple vista (pista de nivel 1).
LOOKS = {
    "base64": "usa letras mayúsculas y minúsculas, números y quizá `+`, `/` o un `=` al final",
    "base32": "solo tiene mayúsculas y los dígitos del 2 al 7, a veces con `=` al final",
    "hex": "solo tiene números y letras de la `a` a la `f`",
    "rot13": "parece texto con las letras cambiadas, pero los números y los símbolos siguen en su sitio",
    "caesar": "parece texto con las letras cambiadas, pero los números y los símbolos siguen en su sitio",
    "atbash": "parece texto con las letras cambiadas, pero los números y los símbolos siguen en su sitio",
    "reverse": "se puede leer si empiezas por el final: fíjate en dónde está la `}`",
    "xor": "son bytes que no forman texto legible",
}
# Cómo deshacer cada capa (pista de nivel 2 y 3).
UNDO = {
    "base64": "`From Base64` en CyberChef (Python: `base64.b64decode`)",
    "base32": "`From Base32` en CyberChef (Python: `base64.b32decode`)",
    "hex": "`From Hex` en CyberChef (Python: `bytes.fromhex`)",
    "rot13": "`ROT13` en CyberChef: aplicarlo otra vez lo deshace",
    "caesar": "`ROT13` en CyberChef cambiando la cantidad hasta que se lea (o la gráfica del analizador)",
    "atbash": "`Atbash Cipher` en CyberChef: aplicarlo otra vez lo deshace",
    "reverse": "`Reverse` en CyberChef (Python: `texto[::-1]`)",
    "xor": "`XOR Brute Force` en CyberChef, o texto conocido: la flag empieza por `f`",
}
# Frases de la historia que insinúan cada transformación sin nombrarla.
STORY_HINTS = {
    "base64": ["Quien lo preparó presumía de usar un alfabeto de sesenta y cuatro símbolos.",
               "En el margen alguien anotó: «64 caracteres bastan para escribirlo todo»."],
    "base32": ["Alguien comentó que solo hacían falta treinta y dos símbolos, todos en mayúsculas.",
               "Una nota decía: «32 signos, ni uno más»."],
    "hex": ["Parte del mensaje parece escrito con apenas dieciséis símbolos.",
            "Quien lo escribió contaba con los dedos de las manos... y seis más."],
    "rot13": ["Una nota decía: «trece pasos hacia delante te dejan donde trece hacia atrás».",
              "Alguien subrayó el número 13 en todas las páginas."],
    "caesar": ["El autor era un gran admirador de los generales de la antigua Roma.",
               "Junto al mensaje había una moneda con el perfil de un emperador romano."],
    "atbash": ["En una esquina alguien escribió: «la A mira a la Z, la B mira a la Y».",
               "Se dice que el alfabeto se miró en un espejo y nunca volvió a ser el mismo."],
    "reverse": ["El mensaje se escribió delante de un espejo.",
                "Quien lo dejó tenía la costumbre de empezar las cosas por el final."],
    "xor": ["Todo quedó protegido con una única llave, tan pequeña que cabe en un byte.",
            "El guardián solo tenía una llave, y era diminuta: un único byte."],
}
INTROS = [
    "Durante una investigación sobre «{tema}» se interceptó un mensaje que nadie ha conseguido leer.",
    "En los archivos del caso «{tema}» apareció una cadena extraña escondida entre documentos sin importancia.",
    "Un informante relacionado con «{tema}» nos dejó este mensaje antes de desaparecer.",
    "El equipo que estudiaba «{tema}» encontró este texto en un servidor olvidado.",
]
TITLES = ["Operación {Tema}", "Expediente {Tema}", "Protocolo {Tema}", "Clave {Tema}", "Señal {Tema}", "Archivo {Tema}"]


class Step(BaseModel):
    op: Op
    param: int  # desplazamiento para caesar, clave para xor; ignorado en el resto


class ChallengeIdea(BaseModel):
    title: str
    story: str
    keyword: str
    steps: list[Step]


class GenerationError(Exception):
    pass


def describe(op: str, p: int) -> str:
    return {
        "base64": "codificar en Base64",
        "base32": "codificar en Base32 (solo mayúsculas A-Z y dígitos 2-7, relleno con '=')",
        "hex": "codificar en hexadecimal",
        "rot13": "aplicar ROT13",
        "caesar": f"cifrado César con desplazamiento {p} (solo letras)",
        "atbash": "cifrado Atbash (a<->z, b<->y...)",
        "reverse": "invertir el orden de la cadena",
        "xor": f"XOR de cada byte con la clave 0x{p:02x}",
    }[op]


def normalize_steps(steps: list[Step], difficulty: str) -> list[tuple[str, int]]:
    """Ajusta la cadena a la dificultad y garantiza que el resultado sea texto imprimible."""
    lo, hi = STEP_RANGE[difficulty]
    out: list[tuple[str, int]] = []
    for s in steps[:hi]:
        p = 0
        if s.op == "caesar":
            p = s.param % 26 or 3
        elif s.op == "xor":
            p = s.param % 256 or 0x2a
        if out and out[-1][0] == "xor" and s.op not in ENCODINGS:
            out.append(("hex", 0))  # tras un XOR hay bytes binarios: hay que codificarlos
        out.append((s.op, p))
    while len(out) < lo:
        out.append((random.choice(["base64", "hex", "rot13", "reverse"]), 0))
    if out[-1][0] == "xor":
        out.append(("hex", 0))
    return out


def make_hints(steps: list[tuple[str, int]]) -> list[str]:
    """Tres niveles de pista a partir de la cadena real (nunca incluyen la flag)."""
    outer = steps[-1][0]
    layers = len(steps)
    undo = list(reversed(steps))
    h1 = (f"Fíjate en los datos: {LOOKS[outer]}. "
          + ("Sospecha de que hay más de una capa: cuando quites una, vuelve a mirar qué queda. " if layers > 1 else "")
          + "El analizador local te ayuda a identificarlo sin coste.")
    h2 = (f"La capa más externa es **{NAMES[outer]}**: deshazla con {UNDO[outer]}. "
          + (f"En total hay {layers} capas." if layers > 1 else "Es la única capa."))
    h3 = "Deshaz las capas en este orden: " + "; ".join(
        f"{i}) {NAMES[op]}" + (f" (desplazamiento {p})" if op == "caesar" else "")
        + (f" (clave 0x{p:02x})" if op == "xor" else "") for i, (op, p) in enumerate(undo, 1)
    ) + ". Al final debe quedar algo con la forma `flag{...}`."
    return [h1, h2, h3]


def build(idea: ChallengeIdea, difficulty: str) -> dict:
    keyword = re.sub(r"[^a-z0-9]", "", idea.keyword.lower())[:16] or "reto"
    flag = f"flag{{{keyword}_{secrets.token_hex(3)}}}"
    steps = normalize_steps(idea.steps, difficulty)

    data = flag.encode()
    for op, p in steps:
        data = apply(op, p, data)
    if not all(32 <= b < 127 or b in (9, 10) for b in data):
        steps.append(("hex", 0))
        data = data.hex().encode()

    check = data
    for op, p in reversed(steps):
        check = invert(op, p, check)
    if check.decode() != flag:
        raise GenerationError("El reto generado no es resoluble")

    chain = "; luego ".join(describe(op, p) for op, p in steps)
    notes = (f"La flag se transformó en este orden: {chain}. Para resolverlo hay que deshacer los pasos en "
             "orden inverso.")
    hints = make_hints(steps)
    secret = flag[5:-1]
    if secret in notes or any(secret in h for h in hints):
        raise GenerationError("La solución se ha colado en las pistas")

    category = "Criptografía" if any(op in CIPHERS for op, _ in steps) else "Codificación"
    return {
        "id": f"gen-{secrets.token_hex(4)}",
        "title": idea.title.strip()[:80],
        "category": category,
        "difficulty": difficulty,
        "points": POINTS[difficulty],
        "description": idea.story.strip()[:1200] + "\n\nFormato de la flag: flag{...}",
        "data": data.decode(),
        "tutor_notes": notes,
        "hints": hints,
        "flag_sha256": hashlib.sha256(flag.encode()).hexdigest(),
    }


def clean_theme(theme: str) -> str:
    theme = re.sub(r"[^\w\sáéíóúüñÁÉÍÓÚÜÑ-]", "", theme).strip()
    theme = re.sub(r"\s+", " ", theme)[:40].strip()
    return theme


def slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    words = re.findall(r"[a-z0-9]+", ascii_text)
    stop = {"el", "la", "los", "las", "un", "una", "de", "del", "y", "en"}
    return next((w for w in words if w not in stop and len(w) > 2), words[0] if words else "reto")


def plan_steps(difficulty: str, rng: random.Random) -> list[Step]:
    """Cadena de capas distintas: primero se transforma el texto y al final se codifica.
    Fácil 1-2 capas, Media 2-3, Difícil 3-5 (con XOR o César)."""
    lo, hi = STEP_RANGE[difficulty]
    n = rng.randint(lo, hi)
    if difficulty == "Fácil":
        ops = rng.sample(["base64", "hex", "reverse", "rot13", "caesar"], n)
    else:
        n_enc = 2 if n >= 4 else 1  # en Difícil a veces hay dos codificaciones seguidas
        pool = ["caesar", "rot13", "atbash", "reverse"] + (["xor"] if difficulty == "Difícil" else [])
        transforms = rng.sample(pool, n - n_enc)
        if difficulty == "Difícil" and not {"xor", "caesar"} & set(transforms):
            transforms[0] = rng.choice(["xor", "caesar"])
        if "xor" in transforms:  # tras un XOR hay bytes binarios: debe ir justo antes de una codificación
            transforms.remove("xor")
            transforms.append("xor")
        ops = transforms + rng.sample(["base64", "base32", "hex"], n_enc)
    return [Step(op=op, param=rng.randint(1, 25) if op == "caesar" else rng.randint(1, 255) if op == "xor" else 0)
            for op in ops]


def generate(theme: str, difficulty: Difficulty, rng: random.Random | None = None) -> dict:
    rng = rng or random.Random(secrets.randbits(64))
    theme = clean_theme(theme) or rng.choice(THEMES)
    steps = plan_steps(difficulty, rng)
    tema_title = theme[:1].upper() + theme[1:]
    story = [rng.choice(INTROS).format(tema=theme)]
    # En Difícil solo se insinúan algunas capas: hay que deducir el resto.
    hinted = steps if difficulty != "Difícil" else rng.sample(steps, max(1, len(steps) // 2))
    story += [rng.choice(STORY_HINTS[s.op]) for s in hinted]
    story.append("Recupera la flag.")
    idea = ChallengeIdea(title=rng.choice(TITLES).format(Tema=tema_title), story=" ".join(story),
                         keyword=slug(theme), steps=steps)
    return build(idea, difficulty)
