"""Genera app/challenges.json a partir de las definiciones de abajo.

Las flags en texto plano solo viven aquí: el JSON generado guarda su SHA-256,
así que ni el frontend ni el tutor IA llegan a verlas nunca.

Uso:  python tools/build_challenges.py
"""

import base64
import hashlib
import hmac
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "app" / "challenges.json"


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def caesar(text: str, shift: int) -> str:
    out = []
    for c in text:
        if c.isascii() and c.isalpha():
            base = ord("A") if c.isupper() else ord("a")
            out.append(chr((ord(c) - base + shift) % 26 + base))
        else:
            out.append(c)
    return "".join(out)


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_jwt(payload: dict, secret: str) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    return f"{header}.{body}.{b64url(sig)}"


WORDLIST = [
    "123456", "password", "qwerty", "dragon", "letmein", "football", "monkey",
    "shadow", "sunshine", "princess", "superman", "trustno1", "iloveyou",
    "welcome", "admin", "hunter2", "batman", "master", "starwars", "pokemon",
]


def build() -> list[dict]:
    challenges = []

    # 1. Codificación en capas
    flag = "flag{c4p4s_d3_c3b0ll4}"
    data = base64.b64encode(flag.encode()).hex()
    challenges.append({
        "id": "capas",
        "hints": ['Fíjate en qué caracteres aparecen: solo números y letras de la **a** a la **f**. ¿Qué sistema de numeración usa justo esos 16 símbolos?', 'Son datos en **hexadecimal**. Decodifícalos (CyberChef: `From Hex`; Python: `bytes.fromhex(...)`) y mira el resultado con calma: tampoco parece texto normal.', 'Pasos: 1) `From Hex`. 2) Lo que sale usa A-Z, a-z y 0-9 y termina en `=`: es **Base64**, decodifícalo también. 3) El resultado ya debería tener la forma `flag{...}`.'],
        "title": "Capas de cebolla",
        "category": "Codificación",
        "difficulty": "Fácil",
        "points": 100,
        "description": "Interceptamos este mensaje. Parece ruido, pero alguien lo envolvió varias veces antes de enviarlo.",
        "data": data,
        "tutor_notes": "El dato es hexadecimal. Al decodificarlo de hex se obtiene una cadena Base64 (termina en '=' y usa A-Z, a-z, 0-9, +, /). Al decodificar el Base64 aparece la flag. Herramientas: CyberChef, `xxd -r -p`, Python bytes.fromhex + base64.b64decode.",
        "flag": flag,
    })

    # 2. César
    flag = "flag{v3n1_v1d1_v1c1}"
    plain = f"El general ordena atacar al amanecer. La clave de acceso es {flag}"
    challenges.append({
        "id": "cesar",
        "hints": ['El enunciado habla de Roma. Mira la estructura del texto: al final hay algo entre llaves `{...}`, igual que el formato de las flags.', 'Es un **cifrado César**: cada letra se desplaza el mismo número de posiciones. En CyberChef, `ROT13` permite cambiar la cantidad; el analizador local también te enseña la gráfica de letras.', 'Pasos: compara las letras que hay justo antes de la `{` con la palabra `flag`. La distancia entre la primera letra cifrada y la `f` es el desplazamiento: aplícalo hacia atrás a todo el texto (los números y símbolos no cambian).'],
        "title": "Mensaje del general",
        "category": "Criptografía",
        "difficulty": "Fácil",
        "points": 100,
        "description": "Un mensaje cifrado de un ejército de la antigua Roma. Las llaves y los números no parecen haber cambiado.",
        "data": caesar(plain, 7),
        "tutor_notes": "Cifrado César con desplazamiento 7 (solo letras; dígitos y símbolos intactos). Se puede romper por fuerza bruta probando los 25 desplazamientos, o fijándose en que el patrón 'mshn{' debe corresponder a 'flag{' (m->f es un desplazamiento de 7).",
        "flag": flag,
    })

    # 3. XOR de un byte
    flag = "flag{x0r_n0_3s_c1fr4d0_s3gur0}"
    key = 0x42
    challenges.append({
        "id": "xor",
        "hints": ['Son bytes en hexadecimal, pero al decodificarlos no sale nada legible. El enunciado dice que se usó una clave de **un solo byte**.', 'Es **XOR** con una clave de 1 byte: solo hay 256 claves posibles, así que se puede probar todas. CyberChef tiene `XOR Brute Force`.', 'Pasos: decodifica el hex. Después, o pruebas las 256 claves y te quedas con la que da texto legible, o usas texto conocido: la flag empieza por `f` (0x66), así que *primer byte XOR 0x66* es la clave. Aplícala a todos los bytes.'],
        "title": "Un solo byte",
        "category": "Criptografía",
        "difficulty": "Media",
        "points": 200,
        "description": "Un desarrollador 'cifró' este secreto con XOR usando una clave de un único byte. Los datos están en hexadecimal.",
        "data": bytes(b ^ key for b in flag.encode()).hex(),
        "tutor_notes": "XOR con clave de un byte (0x42). Solo hay 256 claves posibles: fuerza bruta y buscar texto legible. Alternativa elegante: ataque de texto plano conocido; si la flag empieza por 'f' (0x66) y el primer byte cifrado es 0x24, la clave es 0x24 XOR 0x66.",
        "flag": flag,
    })

    # 4. Código fuente
    flag = "flag{v13w_s0urc3_s13mpr3}"
    html = (
        "<!DOCTYPE html>\n<html>\n<head>\n  <title>Panel de login</title>\n"
        "  <!-- TODO: quitar antes de producción -->\n"
        f"  <!-- debug token: {flag[::-1]} -->\n"
        "</head>\n<body>\n  <form action=\"/login\" method=\"post\">\n"
        "    <input name=\"user\"> <input name=\"pass\" type=\"password\">\n"
        "    <button>Entrar</button>\n  </form>\n</body>\n</html>"
    )
    challenges.append({
        "id": "fuente",
        "hints": ['En el código fuente, busca lo que el navegador no enseña en pantalla: los comentarios `<!-- ... -->`.', 'Uno de los comentarios guarda un *token* que no parece tener sentido. Prueba a leerlo de derecha a izquierda.', 'Pasos: copia el valor del comentario de depuración e **inviértelo** (CyberChef: `Reverse`; Python: `texto[::-1]`). Debería empezar por `flag{`.'],
        "title": "Antes de producción",
        "category": "Web",
        "difficulty": "Fácil",
        "points": 100,
        "description": "Este es el código fuente de un panel de login. Los desarrolladores a veces se dejan cosas olvidadas.",
        "data": html,
        "tutor_notes": "La flag está en un comentario HTML ('debug token') pero escrita al revés. Hay que fijarse en los comentarios y darse cuenta de que '}' aparece al principio. Lección: nunca dejar secretos en comentarios del cliente.",
        "flag": flag,
    })

    # 5. Logs
    flag = "flag{203.0.113.45_backup}"
    lines = []
    t = 0
    def ts(sec):
        return f"Oct  6 03:{12 + sec // 60:02d}:{sec % 60:02d}"
    for ip, user in [("198.51.100.7", "admin"), ("192.0.2.33", "root")]:
        for _ in range(3):
            lines.append(f"{ts(t)} srv sshd[{4100 + t}]: Failed password for {user} from {ip} port {50000 + t} ssh2"); t += 2
    for user in ["root", "admin", "test", "oracle", "backup", "backup", "backup", "backup"]:
        lines.append(f"{ts(t)} srv sshd[{4100 + t}]: Failed password for {user} from 203.0.113.45 port {50000 + t} ssh2"); t += 1
    lines.append(f"{ts(t)} srv sshd[{4100 + t}]: Accepted password for backup from 203.0.113.45 port {50000 + t} ssh2"); t += 3
    lines.append(f"{ts(t)} srv sshd[{4100 + t}]: Accepted publickey for deploy from 10.0.0.12 port 50999 ssh2"); t += 4
    lines.append(f"{ts(t)} srv sudo:   backup : TTY=pts/1 ; PWD=/home/backup ; USER=root ; COMMAND=/bin/cat /etc/shadow")
    challenges.append({
        "id": "logs",
        "hints": ['Primero clasifica las líneas: hay intentos fallidos, accesos correctos y un comando ejecutado con `sudo`.', 'Quédate con los accesos correctos (`Accepted`) y compáralos con las IPs que acumulan `Failed password`. Ojo: no todos los accesos correctos son del atacante.', 'Pasos: la IP del atacante es la que tiene varios fallos seguidos de un `Accepted password`; el usuario es el de esa misma línea. Con esos dos datos construye `flag{IP_usuario}`.'],
        "title": "Noche movida",
        "category": "Forense",
        "difficulty": "Media",
        "points": 200,
        "description": "Extracto de /var/log/auth.log de un servidor. Alguien consiguió entrar tras un ataque de fuerza bruta. La flag es flag{IP_usuario} del atacante que tuvo éxito.",
        "data": "\n".join(lines),
        "tutor_notes": "Hay tres IPs con 'Failed password'. Solo una de ellas tiene después un 'Accepted password': esa es la del atacante y el usuario de ese login es la otra mitad de la respuesta. El 'Accepted publickey' desde la red interna 10.x es una conexión legítima y actúa como distractor. Después, el usuario comprometido usa sudo para leer /etc/shadow: escalada/exfiltración. Método: filtrar por 'Accepted', cruzar con las IPs que tenían fallos (grep, o contar con awk/sort/uniq -c).",
        "flag": flag,
    })

    # 6. Hash débil
    pwd = "trustno1"
    flag = f"flag{{{pwd}}}"
    challenges.append({
        "id": "hash",
        "hints": ['Cuenta los caracteres del hash: son 32 en hexadecimal. ¿Qué algoritmo produce huellas de esa longitud?', 'Es **MD5 sin sal**. Un hash no se descifra: se calcula el hash de cada contraseña candidata y se compara (*ataque de diccionario*).', 'Pasos: para cada palabra de la lista calcula `hashlib.md5(palabra.encode()).hexdigest()` y compáralo con el hash. La que coincida va dentro de `flag{...}`.'],
        "title": "Contraseña filtrada",
        "category": "Criptografía",
        "difficulty": "Media",
        "points": 200,
        "description": "De una base de datos filtrada sacamos el hash de la contraseña del administrador. Tenemos además una lista de contraseñas comunes. La flag es flag{contraseña}.",
        "data": f"hash: {hashlib.md5(pwd.encode()).hexdigest()}\n\nwordlist:\n" + "\n".join(WORDLIST),
        "tutor_notes": "El hash tiene 32 caracteres hex: MD5. Hay que calcular el MD5 de cada palabra de la wordlist y compararlo (ataque de diccionario). Herramientas: script Python con hashlib, hashcat -m 0, john --format=raw-md5. Lección: MD5 sin sal es inadecuado para contraseñas; usar bcrypt/argon2.",
        "flag": flag,
    })

    # 7. JWT con secreto débil
    secret = "superman"
    flag = f"flag{{{secret}}}"
    token = make_jwt({"sub": "1042", "name": "invitado", "role": "user"}, secret)
    challenges.append({
        "id": "jwt",
        "hints": ['El token tiene tres partes separadas por puntos. Decodifica las dos primeras como Base64 (variante URL): ¿qué algoritmo indica la cabecera?', '`HS256` significa que la firma es un **HMAC-SHA256** con un secreto compartido. Si el secreto es débil, se puede adivinar probando una lista de contraseñas.', 'Pasos: para cada palabra de la lista calcula HMAC-SHA256 con la palabra como clave sobre `cabecera.carga`, codifícalo en base64url sin `=` y compáralo con la tercera parte. La palabra que coincida es el secreto.'],
        "title": "Token de confianza",
        "category": "Web",
        "difficulty": "Difícil",
        "points": 300,
        "description": "Una API usa este JWT para autenticar. Si descubrimos el secreto con el que se firma, podríamos fabricarnos un token de admin. El secreto es una contraseña común (usa la wordlist del reto 'Contraseña filtrada'). La flag es flag{secreto}.",
        "data": token,
        "tutor_notes": "El JWT tiene tres partes separadas por puntos (header.payload.firma) en base64url. El header indica HS256: firma HMAC-SHA256 con un secreto compartido. Se puede atacar offline: para cada palabra de la wordlist, calcular HMAC-SHA256(palabra, header + '.' + payload), codificar en base64url sin '=' y compararlo con la firma. Herramientas: hashcat -m 16500, jwt_tool, script Python con hmac. Lección: usar secretos largos y aleatorios.",
        "flag": flag,
    })

    return challenges


def main():
    challenges = build()
    out = []
    for c in challenges:
        c = dict(c)
        flag = c.pop("flag")
        inner = flag[len("flag{"):-1]
        assert inner not in c["tutor_notes"], f"{c['id']}: la solución no debe aparecer en tutor_notes"
        assert len(c["hints"]) == 3, f"{c['id']}: hacen falta 3 niveles de pista"
        assert all(inner not in h for h in c["hints"]), f"{c['id']}: la solución no debe aparecer en las pistas"
        c["flag_sha256"] = sha256(flag)
        out.append(c)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(out)} retos escritos en {OUT}")


if __name__ == "__main__":
    main()
