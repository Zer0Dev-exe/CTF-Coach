"""Mide la velocidad y la precisión del analizador con casos escritos a mano (no generados).

Uso:  python -m ml.benchmark
"""

import base64
import hashlib
import statistics
import time

from app.transforms import apply
from ml import analyzer
from ml.features import extract


def b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


# (texto, etiqueta esperada). Casos variados: cortos, largos, mayúsculas, separadores, inglés...
CASES = [
    # Texto plano
    ("Hola, ¿qué tal estás? Mañana nos vemos en el puerto a las ocho.", "texto"),
    ("The quick brown fox jumps over the lazy dog", "texto"),
    ("flag{bienvenido_al_ctf}", "texto"),
    ("Oct 14 02:40:00 web01 sshd[2200]: Failed password for root from 198.51.100.23 port 41000 ssh2", "texto"),
    ("<html><head><title>Login</title></head><body><form method=post></form></body></html>", "texto"),
    ("contraseña", "texto"),
    # Base64
    (b64("Hola mundo"), "base64"),
    (b64("flag{c4p4s}"), "base64"),
    ("SGVsbG8gV29ybGQ=", "base64"),
    (b64("Este es un mensaje bastante más largo para comprobar que Base64 se detecta bien en textos largos."), "base64"),
    (b64("secreto").rstrip("="), "base64"),
    (base64.urlsafe_b64encode(b"\xfb\xff\xfe datos binarios \x00\x01").decode(), "base64"),
    # Base32
    (base64.b32encode(b"Hola mundo").decode(), "base32"),
    (base64.b32encode(b"flag{base32}").decode(), "base32"),
    # Hexadecimal
    ("486f6c61206d756e646f", "hex"),
    ("486F6C61206D756E646F", "hex"),
    ("48 6f 6c 61 20 6d 75 6e 64 6f", "hex"),
    ("66:6c:61:67:7b:68:65:78:7d", "hex"),
    ("0x48 0x6f 0x6c 0x61", "hex"),
    (b64("hola").encode().hex(), "hex"),
    # César / ROT13
    (apply("caesar", 3, b"El general ordena atacar al amanecer").decode(), "cesar"),
    (apply("rot13", 0, b"Hello world, this is a secret message").decode(), "cesar"),
    (apply("caesar", 11, b"flag{cesar_es_facil_de_romper}").decode(), "cesar"),
    (apply("caesar", 7, b"Nos vemos en la puerta norte del castillo a medianoche").decode(), "cesar"),
    # Atbash
    (apply("atbash", 0, b"Mensaje secreto para el agente en el puerto").decode(), "atbash"),
    (apply("atbash", 0, b"flag{espejo_del_alfabeto}").decode(), "atbash"),
    # Invertido
    ("}otrevni_otxet{galf", "invertido"),
    ("ohcoh sal a otreup le ne somev son anañaM", "invertido"),
    # XOR en hex
    (bytes(b ^ 0x42 for b in b"flag{x0r_n0_es_cifrado}").hex(), "xor"),
    (bytes(b ^ 0x13 for b in b"Mensaje secreto con XOR").hex(), "xor"),
    # Hashes
    (hashlib.md5(b"password").hexdigest(), "md5"),
    (hashlib.md5(b"admin").hexdigest().upper(), "md5"),
    (hashlib.sha1(b"password").hexdigest(), "sha1"),
    (hashlib.sha256(b"password").hexdigest(), "sha256"),
    (hashlib.sha256(b"hola").hexdigest().upper(), "sha256"),
    # Binario, URL y Morse
    ("01001000 01101111 01101100 01100001", "binario"),
    ("0110011001101100011000010110011101111011011000100110100101101110011111010", "binario"),  # le sobra un bit
    ("01100110011011000110000101100111", "binario"),
    ("Hola%20mundo%2C%20%C2%BFqu%C3%A9%20tal%3F", "url"),
    ("flag%7Burl_encoding%7D", "url"),
    ("... --- ... / .- -.-- ..- -.. .-", "morse"),
    (".... --- .-.. .- / -- ..- -. -.. ---", "morse"),
    # JWT
    ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ"
     ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c", "jwt"),
]


def main():
    analyzer._model()  # carga fuera de la medición
    ok, wrong = 0, []
    for text, expected in CASES:
        got = analyzer.predict(text)[0]
        if got["label"] == expected:
            ok += 1
        else:
            wrong.append((text[:50], expected, got["label"], got["probability"]))
    print(f"Precisión en casos reales: {ok}/{len(CASES)} ({ok / len(CASES):.0%})")
    for t, e, g, p in wrong:
        print(f"  ✗ {t!r}: esperado {e}, obtenido {g} ({p:.0%})")

    def timeit(fn, n=200):
        times = []
        for i in range(n):
            text = CASES[i % len(CASES)][0]
            t0 = time.perf_counter()
            fn(text)
            times.append((time.perf_counter() - t0) * 1000)
        return statistics.median(times), sorted(times)[int(n * 0.95)]

    for name, fn in [("características", extract), ("predicción", analyzer.predict), ("análisis completo", analyzer.analyze)]:
        med, p95 = timeit(fn)
        print(f"{name:>18}: mediana {med:.2f} ms · p95 {p95:.2f} ms")


if __name__ == "__main__":
    main()
