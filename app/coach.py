"""Coach interno: tutor por reglas, sin servicios externos.

Combina pistas escritas a mano (retos), notas de cada pregunta (salas), un glosario de conceptos y
el analizador local de codificaciones. Nunca da respuestas: un filtro final elimina cualquier frase
que contenga la respuesta de una pregunta de la tarea actual.
"""

import re
import unicodedata

from ml import analyzer

from .answers import answer_hash

HINT_NAMES = {1: "concepto", 2: "técnica", 3: "pasos"}
STOPWORDS = set("""a al algo como con cual cuales cuando de del donde el ella en es esa ese esta este hay la las le lo
los mas me mi mismo muy no o para pero por que quien se si sin sobre su sus te tu un una uno unos y ya
qué cuál cuáles cómo dónde cuánto cuántos usa usan hace tiene puede debe sirve llama llamado normalmente
defecto exactamente aparece aparecen ejemplo datos teoria tarea pregunta respuesta""".split())


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


# ---------- Glosario (explicaciones conceptuales, sin respuestas concretas) ----------

GLOSSARY = [
    (r"base ?64", "Base64",
     "Una forma de escribir cualquier dato usando solo letras, números, `+` y `/`.",
     "Sirve para meter datos binarios en sitios que solo aceptan texto (correos, URLs, JSON). No protege nada: cualquiera puede decodificarlo. Se reconoce por sus caracteres y porque a veces termina en `=`."),
    (r"base ?32", "Base32",
     "Como Base64 pero con un alfabeto más pequeño: mayúsculas y los dígitos del 2 al 7.",
     "Ocupa más que Base64 pero evita confusiones entre caracteres parecidos. También es solo una codificación: no hay clave."),
    (r"\bhex(adecimal)?\b", "Hexadecimal",
     "Sistema de numeración en base 16: dígitos del 0 al 9 y letras de la a a la f.",
     "Se usa para escribir bytes de forma legible: cada byte se representa con una pareja de símbolos. Si ves un texto que solo tiene esos caracteres, prueba a decodificarlo como hex."),
    (r"\bxor\b", "XOR",
     "Operación bit a bit: devuelve 1 cuando los dos bits son distintos.",
     "Aplicar XOR dos veces con la misma clave devuelve el dato original, por eso se usa para «cifrar». Con una clave corta es muy débil: se puede probar con todas las claves o usar texto conocido."),
    (r"\bcesar\b|\bcaesar\b|\brot ?13\b", "Cifrado César",
     "Cada letra se desplaza un número fijo de posiciones en el alfabeto.",
     "ROT13 es el caso de desplazamiento 13. Como solo hay 25 desplazamientos posibles, se rompe probándolos todos o comparando las frecuencias de las letras con las del idioma."),
    (r"\batbash\b", "Atbash",
     "Cifrado que da la vuelta al alfabeto: la primera letra pasa a ser la última y así sucesivamente.",
     "No tiene clave: aplicarlo dos veces devuelve el texto original."),
    (r"\bhash(es)?\b|\bmd5\b|\bsha", "Función hash",
     "Convierte cualquier dato en una huella de longitud fija. No se puede deshacer.",
     "Cada algoritmo produce huellas de una longitud característica, así que contar caracteres ayuda a identificarlo. Para «romper» un hash se calcula el hash de muchas candidatas y se compara (ataque de diccionario)."),
    (r"\bsal\b|\bsalt\b", "Sal",
     "Valor aleatorio que se añade a cada contraseña antes de calcular su hash.",
     "Hace que dos contraseñas iguales den hashes distintos e inutiliza las tablas precalculadas."),
    (r"bcrypt|argon|scrypt", "Algoritmos para contraseñas",
     "Funciones hash lentas a propósito, pensadas para guardar contraseñas.",
     "Su lentitud hace que probar millones de contraseñas sea muy caro para un atacante."),
    (r"\bjwt\b|token", "JWT",
     "Token con tres partes separadas por puntos: cabecera, contenido y firma.",
     "Las dos primeras partes son Base64 de URL y cualquiera puede leerlas. La firma impide modificarlas; si el secreto de la firma es débil, se puede adivinar."),
    (r"\bhmac\b", "HMAC",
     "Firma que combina un hash con una clave secreta.",
     "Sin la clave no se puede generar una firma válida, pero si la clave es una palabra común se puede adivinar probando una lista."),
    (r"simetric|asimetric|\baes\b|\brsa\b|clave (publica|privada)", "Cifrado simétrico y asimétrico",
     "Simétrico: la misma clave cifra y descifra. Asimétrico: un par de claves, una pública y otra privada.",
     "El simétrico es rápido; el asimétrico resuelve cómo compartir claves sin habérselas pasado antes. En la práctica se combinan."),
    (r"\bpuertos?\b", "Puerto",
     "Número que identifica a un servicio dentro de un equipo, como el número de puerta de un edificio.",
     "Una IP te lleva al equipo y el puerto al servicio concreto. Muchos servicios usan siempre el mismo por convenio."),
    (r"\btcp\b|\budp\b|handshake|saludo", "TCP y UDP",
     "Dos protocolos de transporte: uno establece conexión y garantiza la entrega, el otro no.",
     "TCP abre la conexión con un intercambio de tres mensajes antes de enviar datos; UDP envía directamente, más rápido pero sin garantías."),
    (r"\bdns\b|registro", "DNS",
     "El sistema que traduce nombres de dominio a direcciones IP.",
     "Guarda varios tipos de registro: unos apuntan a direcciones IP, otros al servidor de correo, otros son texto libre..."),
    (r"\bip\b|direccion", "Dirección IP",
     "Identificador de un equipo en una red.",
     "Las IPv4 tienen cuatro números separados por puntos; las IPv6 son más largas y usan hexadecimal."),
    (r"\bssh\b", "SSH",
     "Protocolo para abrir una terminal remota de forma cifrada.",
     "Es la forma habitual de administrar servidores Linux, por eso es un objetivo frecuente de ataques de fuerza bruta."),
    (r"\bhttps?\b|peticion|codigo de estado|metodo", "HTTP",
     "El protocolo que usa la web: el navegador envía peticiones y el servidor responde con un código de estado.",
     "Los métodos indican qué se quiere hacer (pedir, enviar, borrar...) y los códigos de estado cómo ha ido (bien, redirección, error del cliente, error del servidor)."),
    (r"cookie|httponly|samesite|secure", "Cookies",
     "Pequeños datos que el servidor guarda en tu navegador, por ejemplo para recordar tu sesión.",
     "Sus atributos de seguridad limitan quién puede leerlas y cuándo se envían."),
    (r"\bxss\b|cross.site", "XSS",
     "Ocurre cuando una web muestra datos de un usuario sin tratarlos y otro navegador los ejecuta como código.",
     "Se previene escapando la salida y limitando de dónde puede cargar scripts la página."),
    (r"inyeccion|\bsql\b", "Inyección",
     "Ocurre cuando la aplicación mezcla datos del usuario con código, por ejemplo al construir una consulta pegando textos.",
     "La defensa principal es separar siempre consulta y datos."),
    (r"owasp", "OWASP Top 10",
     "Lista de los riesgos de seguridad web más importantes, que se actualiza cada pocos años.",
     "Es la referencia habitual para aprender seguridad de aplicaciones web."),
    (r"control de acceso|autorizacion|idor", "Control de acceso",
     "Comprobar que un usuario puede hacer lo que pide sobre un recurso concreto.",
     "Debe comprobarse siempre en el servidor: lo que hay en el navegador se puede modificar."),
    (r"permis|chmod|rwx|octal", "Permisos en Linux",
     "Cada archivo tiene permisos de lectura, escritura y ejecución para el propietario, el grupo y el resto.",
     "Se leen en bloques de tres caracteres. En octal, cada permiso tiene un valor y se suman dentro de cada bloque."),
    (r"\bgrep\b|\bfind\b|buscar", "Buscar en Linux",
     "Hay herramientas para buscar texto dentro de archivos y otras para buscar archivos por nombre.",
     "Combinadas con tuberías (`|`) permiten filtrar y contar líneas de registros muy largos."),
    (r"\blogs?\b|auth\.?log|registros?", "Registros (logs)",
     "Archivos donde el sistema anota lo que pasa: inicios de sesión, errores, comandos...",
     "Para investigar, agrupa las líneas por tipo, busca patrones (muchos fallos seguidos) y reconstruye el orden de los hechos."),
    (r"\bsudo\b|root|administrador", "sudo",
     "Permite a un usuario ejecutar un comando con privilegios de administrador.",
     "Cada uso queda registrado, por eso aparece en los logs de una investigación."),
    (r"phishing|correo|remitente|enlace", "Phishing",
     "Engaño, normalmente por correo, para que entregues credenciales o abras algo malicioso.",
     "Fíjate en el dominio real del remitente, en el destino real de los enlaces y en la presión para actuar rápido."),
    (r"cyberchef", "CyberChef",
     "Herramienta web gratuita para encadenar operaciones de codificación, cifrado y análisis.",
     "Se arrastran operaciones a una «receta» y se ve el resultado de cada paso. Muy útil para quitar capas una a una."),
    (r"diccionario|fuerza bruta|wordlist|lista de contrasenas", "Ataque de diccionario",
     "Probar una lista de candidatas, comparando cada una con lo que se busca.",
     "Funciona porque mucha gente usa contraseñas comunes. Con hashes, se calcula el hash de cada candidata y se compara."),
    (r"binario", "Binario",
     "Sistema en base 2: solo ceros y unos.",
     "Ocho bits forman un byte, que suele corresponder a un carácter."),
    (r"morse", "Código Morse",
     "Codifica letras con puntos y rayas.",
     "Las letras suelen ir separadas por espacios y las palabras por `/`."),
    (r"\bflag\b", "Flag",
     "El texto que demuestra que has resuelto un reto. Aquí tiene la forma `flag{...}`.",
     "Cuando la encuentres, cópiala completa, con las llaves, en el campo de la flag."),
]
GLOSSARY = [(re.compile(p), t, s, l) for p, t, s, l in GLOSSARY]

ASK_ANSWER = re.compile(
    r"\b(dame|dime|pasame|escribeme|escribe|quiero|cual es|necesito)\b.{0,40}\b(flag|respuesta|solucion|contrasena|secreto|clave|resultado)\b")
GREETING = re.compile(r"^\s*(hola|buenas|hey|buenos dias|buenas tardes|que tal)\b")
THANKS = re.compile(r"\b(gracias|genial|perfecto|lo tengo|ya esta|resuelto)\b")
WHAT_IS = re.compile(r"\b(que es|que son|que significa|explica|explicame|no entiendo|para que sirve)\b")

UNDO_BY_LABEL = {
    "base64": "deshazlo con `From Base64` en CyberChef (Python: `base64.b64decode`)",
    "base32": "deshazlo con `From Base32` en CyberChef (Python: `base64.b32decode`)",
    "hex": "deshazlo con `From Hex` en CyberChef (Python: `bytes.fromhex`)",
    "cesar": "prueba desplazamientos con `ROT13` en CyberChef cambiando la cantidad, o mira la gráfica de letras del analizador",
    "atbash": "aplica `Atbash Cipher` en CyberChef: aplicarlo otra vez lo deshace",
    "invertido": "dale la vuelta con `Reverse` en CyberChef (Python: `texto[::-1]`)",
    "xor": "decodifica el hex y prueba claves con `XOR Brute Force` en CyberChef",
    "md5": "un hash no se deshace: compáralo con los hashes de una lista de candidatas",
    "sha1": "un hash no se deshace: compáralo con los hashes de una lista de candidatas",
    "sha256": "un hash no se deshace: compáralo con los hashes de una lista de candidatas",
    "jwt": "decodifica sus dos primeras partes como Base64 de URL para leer cabecera y contenido",
    "binario": "agrupa los bits de ocho en ocho y conviértelos a caracteres (`From Binary` en CyberChef)",
    "url": "deshazlo con `URL Decode` en CyberChef (Python: `urllib.parse.unquote`)",
    "morse": "tradúcelo con `From Morse Code` en CyberChef",
}


def format_user_message(message: str, level: str, hint_level: int | None, task_title: str | None = None) -> str:
    """Texto que se guarda en el historial (la interfaz oculta las etiquetas entre corchetes)."""
    prefix = f"[Nivel del alumno: {level}]"
    if hint_level:
        prefix += f" [Pide una pista de nivel {hint_level}]"
    if task_title:
        prefix += f" [Tarea: {task_title}]"
    return f"{prefix}\n{message.strip() or 'Dame una pista, por favor.'}"


def _concepts(text: str, level: str, limit: int = 2) -> list[str]:
    plain = _plain(text)
    out = []
    for pattern, title, short, long in GLOSSARY:
        if pattern.search(plain):
            out.append(f"**{title}:** {short}" + (f" {long}" if level == "principiante" else ""))
        if len(out) >= limit:
            break
    return out


def _pasted_analysis(message: str) -> str | None:
    """Si el mensaje contiene algo que parece codificado, dice qué parece (sin decodificarlo)."""
    text = message.strip()
    # Un trozo sin espacios de 12+ caracteres, o el mensaje entero si apenas tiene palabras
    # (Morse, binario o hex separado por espacios). Una frase normal nunca se analiza.
    tokens = sorted(re.findall(r"\S{12,}", text), key=len, reverse=True)
    candidates = [t for t in tokens[:1] if not re.fullmatch(r"[a-záéíóúñ]+[.,!?]?", t.lower())]
    words = re.findall(r"[a-záéíóúñ]{3,}", text.lower())
    if len(text) >= 16 and not words and not candidates:
        candidates.append(text)
    for chunk in candidates:
        try:
            best = analyzer.predict(chunk)[0]
        except analyzer.ModelMissing:
            return None
        if best["label"] != "texto" and best["probability"] >= 0.5:
            pct = round(best["probability"] * 100)
            return (f"He pasado lo que me has pegado por el analizador local: parece **{best['name']}** ({pct} %). "
                    f"{best['explanation']} Si es así, {UNDO_BY_LABEL.get(best['label'], 'identifica la capa y deshazla')}. "
                    "Después vuelve a analizar el resultado: puede haber más capas.")
    return None


TRIM = "*«»\"'`.,;:()¿?¡!"
MAX_ANSWER_WORDS = 6


def _leaks(sentence: str, answer_hashes: set[str]) -> bool:
    """¿Contiene la frase alguna respuesta? Se comparan hashes de todos sus fragmentos de 1 a 6 palabras,
    así el servidor puede filtrar respuestas que solo conoce por su hash."""
    tokens = [t.strip(TRIM) for t in sentence.split()]
    tokens = [t for t in tokens if t]
    for i in range(len(tokens)):
        for j in range(i + 1, min(i + MAX_ANSWER_WORDS, len(tokens)) + 1):
            if j == i + 1 and len(tokens[i]) == 1 and tokens[i].isalpha():
                continue  # "a", "y", "o"... son palabras normales: una respuesta de una letra solo se filtra en contexto
            if answer_hash(" ".join(tokens[i:j])) in answer_hashes:
                return True
    return False


def _strip_answers(text: str, answer_hashes: set[str]) -> str:
    """Quita las frases que contengan alguna respuesta, conservando los párrafos."""
    paragraphs = []
    for para in text.split("\n\n"):
        sentences = re.split(r"(?<=[.!?])\s+", para)
        kept = [x for x in sentences if not _leaks(x, answer_hashes)]
        if kept:
            paragraphs.append(" ".join(kept))
    return "\n\n".join(paragraphs) or "Vuelve a leer la teoría de esta tarea con calma: la respuesta está ahí."


def _closing(level: str) -> str:
    return {"principiante": "Si algún término no te suena, pregúntame «qué es…» y te lo explico.",
            "intermedio": "",
            "avanzado": ""}[level]


# ---------- Retos ----------

CATEGORY_PROMPTS = {
    "Codificación": "¿Qué caracteres aparecen en los datos? ¿Alguno que no esté en un texto normal? Eso suele delatar la codificación.",
    "Criptografía": "¿Se conserva algo de la estructura original (llaves, guiones bajos, números)? Eso dice mucho del tipo de cifrado.",
    "Web": "¿Has revisado todo el código, incluido lo que el navegador no muestra en pantalla?",
    "Forense": "¿Qué tipos de eventos aparecen? Agrúpalos antes de sacar conclusiones y busca lo que se sale del patrón.",
}


def _generic_hints(ch: dict) -> list[str]:
    """Pistas para retos antiguos que no las traen: se apoyan en el analizador."""
    try:
        best = analyzer.predict(ch["data"])[0]
        guess = f"El analizador local cree que es **{best['name']}**: {best['explanation']}"
        undo = UNDO_BY_LABEL.get(best["label"], "deshaz esa capa")
    except analyzer.ModelMissing:
        guess, undo = "Observa qué caracteres usan los datos.", "deshaz la capa que identifiques"
    return [
        "Fíjate en el juego de caracteres de los datos y pásalos por el analizador local.",
        f"{guess} Para continuar, {undo}.",
        "Repite el ciclo: identifica la capa, deshazla y vuelve a analizar el resultado hasta llegar a `flag{...}`.",
    ]


def challenge_reply(ch: dict, message: str, level: str, hint_level: int | None) -> str:
    plain = _plain(message)
    parts: list[str] = []
    if hint_level:
        hints = ch.get("hints") or _generic_hints(ch)
        parts.append(f"**Pista {hint_level} · {HINT_NAMES[hint_level]}**\n\n{hints[hint_level - 1]}")
    if "flag{" in plain:
        parts.append("Eso tiene forma de flag. Pruébala en el campo **Enviar flag**: si es correcta, sumará los puntos.")
    elif ASK_ANSWER.search(plain):
        parts.append("La flag no te la voy a dar: la gracia es que llegues tú. Lo que sí puedo hacer es orientarte. "
                     "Si estás bloqueado, la **Pista 1** solo cuesta un 10 % de los puntos.")
    if not hint_level and "flag{" not in plain:
        analysis = _pasted_analysis(message)
        if analysis:
            parts.append(analysis)
    concepts = _concepts(message, level) if WHAT_IS.search(plain) or len(plain.split()) <= 4 else []
    parts += concepts
    if not parts:
        if GREETING.search(plain):
            parts.append("¡Hola! Cuéntame qué has probado o pégame un trozo de lo que tienes y te digo qué parece.")
        elif THANKS.search(plain):
            parts.append("¡A por ello! Si te vuelves a atascar, aquí estoy.")
        else:
            parts.append(CATEGORY_PROMPTS.get(ch.get("category"), CATEGORY_PROMPTS["Codificación"])
                         + " Si me pegas un trozo de los datos o de tu resultado intermedio, te digo qué parece.")
    closing = _closing(level)
    if closing and not hint_level:
        parts.append(closing)
    return "\n\n".join(parts)


# ---------- Salas ----------

def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", _plain(text)) if len(w) >= 3 and w not in STOPWORDS]


def _pick_question(task: dict, message: str, answered: set[str]) -> dict:
    pending = [q for q in task["questions"] if q["id"] not in answered] or task["questions"]
    msg = set(w[:5] for w in _words(message))
    scored = [(len(msg & set(w[:5] for w in _words(q["prompt"]))), -i, q) for i, q in enumerate(pending)]
    best = max(scored, key=lambda t: (t[0], t[1]))
    return best[2]


def _theory_pointer(task: dict, question: dict) -> str:
    """Señala la línea de la teoría más relacionada con la pregunta, sin citarla.
    Las palabras que aparecen en pocas líneas (p. ej. «SSH») pesan más que las repetidas («puerto»)."""
    lines, kinds, in_code = [], [], False
    for line in task["content"].splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if not line.strip():
            continue
        lines.append(set(w[:5] for w in _words(line)))
        kinds.append("bloque de código" if in_code else "lista" if line.lstrip().startswith(("- ", "* "))
                     else "lista numerada" if re.match(r"\s*\d+\.", line) else "párrafo")
    prompt_words = [w for w in re.findall(r"[\wáéíóúñ-]+", question["prompt"])
                    if len(w) >= 3 and _plain(w) not in STOPWORDS]
    stems = {w: _plain(w)[:5] for w in prompt_words}
    df = {st: sum(st in ln for ln in lines) for st in stems.values()}
    best_i, best_score = None, 0.0
    for i, ln in enumerate(lines):
        score = sum(1 / df[st] for st in set(stems.values()) if st in ln and df[st])
        if score > best_score:
            best_i, best_score = i, score
    if best_i is None:
        if task.get("data"):
            return "La respuesta está en los datos de la tarea: analízalos con la pregunta en mente."
        return "Vuelve a leer la teoría con la pregunta en mente: la respuesta está ahí."
    shared = sorted({w for w, st in stems.items() if st in lines[best_i]}, key=lambda w: df[stems[w]])[:2]
    about = " y ".join(f"**{w}**" for w in shared)
    where = {"lista": "en la lista de la teoría", "lista numerada": "en los pasos numerados de la teoría",
             "bloque de código": "en el ejemplo de código de la teoría", "párrafo": "en la teoría"}[kinds[best_i]]
    verb = "aparecen" if len(shared) > 1 else "aparece"
    return f"Mira {where}" + (f", donde {verb} {about}." if about else ".")


def room_reply(task: dict, message: str, level: str, answered: set[str]) -> str:
    plain = _plain(message)
    parts: list[str] = []
    if ASK_ANSWER.search(plain):
        parts.append("No te voy a dar la respuesta directamente, pero te ayudo a encontrarla.")
    if all(q["id"] in answered for q in task["questions"]):
        parts.append("Ya has respondido todas las preguntas de esta tarea. ¡Buen trabajo! Pasa a la siguiente.")
    else:
        q = _pick_question(task, message, answered)
        parts.append(f"Vamos con «{q['prompt']}».")
        # La nota de la pregunta es la mejor pista; si no hay, se señala la parte de la teoría.
        parts.append(q["tutor_notes"] if q.get("tutor_notes") else _theory_pointer(task, q))
        if q.get("options"):
            parts.append("Es de opción múltiple: descarta primero las opciones que contradigan lo que dice la teoría.")
        if level == "principiante":
            parts += _concepts(q["prompt"], level, limit=1)
    analysis = _pasted_analysis(message)
    if analysis:
        parts.append(analysis)
    if WHAT_IS.search(plain):
        parts += [c for c in _concepts(message, level) if c not in parts]
    if THANKS.search(plain) and len(plain.split()) <= 4:
        parts = ["¡Genial! Sigue así. Si te atascas en otra pregunta, pregúntame."]
    closing = _closing(level)
    if closing:
        parts.append(closing)
    answer_hashes = {h for q in task["questions"] for h in q["answer_sha256"]}
    return _strip_answers("\n\n".join(parts), answer_hashes)
