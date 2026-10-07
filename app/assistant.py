"""Bit, la mascota de CTF Coach: resuelve dudas sobre la web y te lleva a donde está cada cosa.

Funciona por reglas (100 % local). Cada respuesta puede llevar «acciones»: botones que navegan a una
vista (goto), resaltan un elemento de la página (highlight) o abren el registro (auth).
"""

import re

from . import roadmap
from .challenges import STATIC
from .coach import GLOSSARY, _plain
from .rooms import PATHS, QUESTION_COUNT, ROOMS

NAME = "Bit"


def act(label: str, goto: str | None = None, highlight: str | None = None, auth: str | None = None,
        ask: str | None = None) -> dict:
    """Botón de una respuesta: navega (goto), resalta (highlight), abre el acceso (auth) o pregunta a Bit (ask)."""
    return {k: v for k, v in {"label": label, "goto": goto, "highlight": highlight, "auth": auth, "ask": ask}.items() if v}


def answer(reply: str, actions: list | None = None, suggestions: list | None = None) -> dict:
    return {"reply": reply, "actions": actions or [], "suggestions": suggestions or []}


def has(text: str, *patterns: str) -> bool:
    return any(re.search(p, text) for p in patterns)


# ---------- Qué hay en la web (entidades) ----------

ROOM_ALIASES = {
    "redes": ["redes", "puerto", "puertos", "tcp", "udp", "dns", "direccion ip", "handshake"],
    "linux": ["linux", "terminal", "permisos", "chmod", "comandos", "grep", "consola"],
    "codificacion": ["codificar", "codificacion", "base64", "hexadecimal", "cifrado simetrico", "asimetrico", "aes", "rsa"],
    "hashes": ["hash", "hashes", "md5", "sha", "contrasenas", "sal", "bcrypt", "ataque de diccionario"],
    "logs": ["logs", "auth.log", "login sospechoso", "registros", "investigacion", "incidente"],
    "phishing": ["phishing", "correo", "email", "suplantacion", "fraude"],
    "http": ["como funciona la web", "http", "cookies", "codigos de estado", "codigo fuente"],
    "owasp": ["owasp", "xss", "inyeccion", "sql", "control de acceso", "defensa web"],
}
CHALLENGE_ALIASES = {
    "capas": ["capas de cebolla", "cebolla", "capas"],
    "cesar": ["mensaje del general", "general", "cesar"],
    "xor": ["un solo byte", "xor"],
    "fuente": ["antes de produccion", "produccion", "comentario html"],
    "logs": ["noche movida"],
    "hash": ["contrasena filtrada", "filtrada"],
    "jwt": ["token de confianza", "jwt"],
}
CHALLENGES = {c["id"]: c for c in STATIC}
PATH_OF_ROOM = {r["id"]: p for p in PATHS for r in p["rooms"]}
TOPICS = {t["id"]: (stage, t) for stage in roadmap.ROADMAP for t in stage["topics"]}

# Concepto del glosario → sala donde se practica.
GLOSSARY_ROOM = {
    "Base64": "codificacion", "Base32": "codificacion", "Hexadecimal": "codificacion", "XOR": "codificacion",
    "Cifrado César": "codificacion", "Atbash": "codificacion", "Función hash": "hashes", "Sal": "hashes",
    "Algoritmos para contraseñas": "hashes", "JWT": "http", "Cifrado simétrico y asimétrico": "codificacion",
    "Puerto": "redes", "TCP y UDP": "redes", "DNS": "redes", "Dirección IP": "redes", "SSH": "redes",
    "HTTP": "http", "Cookies": "http", "XSS": "owasp", "Inyección": "owasp", "OWASP Top 10": "owasp",
    "Control de acceso": "owasp", "Permisos en Linux": "linux", "Buscar en Linux": "linux",
    "Registros (logs)": "logs", "sudo": "logs", "Phishing": "phishing", "Ataque de diccionario": "hashes",
}


def _find(aliases: dict[str, list[str]], text: str) -> str | None:
    best, best_len = None, 0
    for key, words in aliases.items():
        for w in words:
            if re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", text) and len(w) > best_len:
                best, best_len = key, len(w)
    return best


TOPIC_ALIASES = {
    "forense": ["forense", "evidencias"], "cloud": ["nube", "cloud", "aws", "azure"],
    "malware": ["malware", "virus", "ransomware", "ingenieria inversa"], "siem": ["siem", "soc", "monitorizacion"],
    "ir": ["respuesta a incidentes", "incidentes"], "bastionado": ["bastionado", "hardening", "bastionar"],
    "privesc": ["escalada", "privilegios"], "ad": ["directorio activo", "active directory", "kerberos"],
    "metodologia": ["pentesting", "pentest", "auditoria", "hacking etico", "red team"],
    "grc": ["normativa", "iso 27001", "rgpd", "nis2", "cumplimiento", "grc"],
    "certs": ["certificacion", "certificaciones", "oscp", "ejpt", "security+"],
    "programacion": ["python", "bash", "programar", "programacion", "scripting"],
    "windows": ["windows", "powershell"], "appsec": ["devsecops", "appsec", "desarrollo seguro"],
    "conceptos": ["mitre", "nist", "triada", "riesgo"], "blue": ["blue team", "defensa"],
}


def _find_topic(text: str) -> str | None:
    best, best_len = None, 0
    for tid, (_, t) in TOPICS.items():
        for w in [_plain(t["title"])] + [_plain(s) for s in t["skills"]] + TOPIC_ALIASES.get(tid, []):
            if len(w) >= 3 and re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", text) and len(w) > best_len:
                best, best_len = tid, len(w)
    return best


# ---------- Dónde está cada cosa ----------

FEATURES = [
    {"keys": [r"analizador", r"identificar (la )?codificacion", r"que codificacion es", r"modelo local"],
     "reply": "El **analizador local** está en la ficha de cada reto, debajo de los datos. Pegas un texto y te dice "
              "qué codificación o cifrado parece (Base64, hex, César, XOR, hashes...) mientras escribes. Es gratis y no resta puntos.",
     "actions": [act("Abrir el analizador", "#reto/capas", "#analyzer")]},
    {"keys": [r"pistas?", r"ayuda en (un|el) reto", r"penaliza", r"me atasco", r"estoy atascad"],
     "reply": "Las **pistas** están en el panel del Coach, a la derecha de cada reto. Hay tres niveles: "
              "concepto (−10 %), técnica (−25 %) y pasos (−50 %). Solo cuenta el nivel más alto que pidas antes de resolverlo. "
              "En las salas preguntar al Coach es gratis.",
     "actions": [act("Ver las pistas de un reto", "#reto/capas", ".hint-buttons")]},
    {"keys": [r"(crea|creo|crear|genera|genero|generar|hago|hacer|invento|inventar|monto|montar) (un |mi |otro )?reto",
              r"reto (nuevo|propio|personalizado)", r"generador"],
     "reply": "En **Retos**, arriba del todo, está «Crear un reto nuevo». Escribes un tema, eliges la dificultad y se "
              "genera un reto de codificación o criptografía con su historia y sus pistas. Aparece en «Creados por jugadores».",
     "actions": [act("Ir a crear un reto", "#retos", "#gen-form")]},
    {"keys": [r"insignias?", r"medallas?", r"logros?", r"badges?"],
     "reply": "Las **insignias** se ven arriba en la página de **Salas**. Ganas una al completar todas las preguntas de una sala "
              "y otra especial (en dorado) al completar todas las salas de una ruta.",
     "actions": [act("Ver mis insignias", "#salas", ".badges-box")]},
    {"keys": [r"nivel (del coach|de explicacion|de las explicaciones)", r"cambiar (el )?nivel", r"principiante|avanzado|intermedio"],
     "reply": "El **nivel de las explicaciones** se elige en el desplegable de la cabecera del Coach, dentro de cualquier "
              "sala o reto. En «Principiante» el Coach explica más los conceptos; en «Avanzado» va al grano.",
     "actions": [act("Ver dónde se cambia", "#sala/redes", ".level-select")]},
    {"keys": [r"enviar (la )?flag", r"donde (pongo|meto|escribo) la flag", r"campo de la flag"],
     "reply": "La flag se escribe en el campo **flag{...}** de la ficha del reto, justo debajo de los datos, y se envía con "
              "«Enviar flag». Cópiala completa, con las llaves.",
     "actions": [act("Ver el campo de la flag", "#reto/capas", "#flag-form")]},
    {"keys": [r"copiar (los )?datos", r"boton (de )?copiar"],
     "reply": "En la ficha de cada reto, el recuadro de **Datos** tiene un botón «Copiar» en la esquina superior derecha.",
     "actions": [act("Ver el botón", "#reto/capas", "#copy")]},
    {"keys": [r"semana", r"ultimos 7 dias", r"semanal"],
     "reply": "En **Clasificación** puedes cambiar entre «Siempre» y «Últimos 7 días» con el selector de arriba a la derecha. "
              "La vista semanal solo cuenta los puntos ganados esa semana: buena para remontar.",
     "actions": [act("Ver la clasificación semanal", "#clasificacion", ".lb-period")]},
    {"keys": [r"filtr", r"solo (lo )?disponible"],
     "reply": "En el **Roadmap** hay un filtro «Solo disponible aquí» que deja únicamente los temas que puedes practicar en CTF Coach.",
     "actions": [act("Ver el filtro", "#roadmap", ".rm-filter")]},
    {"keys": [r"chat del coach", r"hablar con el coach", r"donde esta el coach", r"\bcoach\b"],
     "reply": "El **Coach** es el tutor de cada sala y cada reto: está en el panel de la derecha (o debajo, en el móvil). "
              "Te orienta con preguntas y pistas, pero nunca te da la respuesta. Yo, Bit, te ayudo con la web en general.",
     "actions": [act("Ver el Coach", "#sala/redes", ".coach")]},
]

FAQ = [
    {"keys": [r"puntos", r"puntuacion", r"como se (gana|consigue|suma)", r"cuanto vale"],
     "reply": "Así se ganan **puntos**:\n\n- Cada pregunta de una sala vale entre 10 y 30 puntos.\n"
              "- Cada reto vale 100 (fácil), 200 (medio) o 300 (difícil), menos la penalización de la pista más alta que hayas pedido.\n"
              "- Todo suma en la clasificación. Los puntos de un reto solo se ganan la primera vez.",
     "actions": [act("Ver la clasificación", "#clasificacion")]},
    {"keys": [r"que es (una|la) flag", r"\bflag\b.*\bque\b", r"formato de la flag"],
     "reply": "La **flag** es el texto que demuestra que has resuelto un reto. Aquí siempre tiene la forma `flag{...}`. "
              "Suele estar escondida o transformada dentro de los datos del reto."},
    {"keys": [r"\bctf\b", r"capture the flag"],
     "reply": "**CTF** significa *Capture The Flag*: competiciones de ciberseguridad donde resuelves retos para encontrar un "
              "texto secreto (la flag). En CTF Coach tienes retos de ese estilo y, además, salas guiadas para aprender la base.",
     "actions": [act("Ver los retos", "#retos"), act("Ver las salas", "#salas")]},
    {"keys": [r"empate", r"mismos puntos"],
     "reply": "Con los mismos puntos va delante **quien llegó antes** a esa puntuación."},
    {"keys": [r"gratis", r"pagar", r"precio", r"cuesta dinero"],
     "reply": "Todo es **gratis**: salas, retos, Coach, analizador y roadmap."},
    {"keys": [r"instalar", r"descargar", r"necesito (algo|programas)"],
     "reply": "No hace falta instalar nada: todo funciona en el navegador. Para algunos retos viene bien **CyberChef** "
              "(también web) o un poco de Python, pero no es obligatorio."},
    {"keys": [r"\bia\b", r"inteligencia artificial", r"internet", r"sin conexion", r"datos personales", r"privacidad"],
     "reply": "Todo funciona **en local**: el Coach, el analizador y yo funcionamos con reglas y un modelo propio, sin enviar "
              "nada a servicios externos. Solo se guardan tu usuario, una versión cifrada de tu contraseña y tu progreso."},
    {"keys": [r"diferencia entre (salas|retos)", r"salas? (y|o) retos?", r"retos? (y|o) salas?"],
     "reply": "- **Salas**: aprendes. Teoría corta y preguntas, con el Coach gratis.\n"
              "- **Retos**: lo pones en práctica. Tienes que encontrar una flag y las pistas cuestan puntos.\n\n"
              "Lo normal es hacer primero la sala de un tema y después su reto.",
     "actions": [act("Ir a las salas", "#salas"), act("Ir a los retos", "#retos")]},
    {"keys": [r"roadmap", r"ruta general", r"que estudiar", r"temario"],
     "reply": "El **Roadmap** es el camino completo para aprender ciberseguridad: 5 etapas y 24 temas, desde redes y Linux "
              "hasta especializaciones. Los temas disponibles aquí enlazan a sus salas y retos; el resto, a recursos externos.",
     "actions": [act("Abrir el roadmap", "#roadmap")]},
]


# ---------- Respuestas ----------

def _room_answer(rid: str, ctx: dict) -> dict:
    room = ROOMS[rid]
    path = PATH_OF_ROOM[rid]
    done = len(ctx["answers"].get(rid, {}))
    total = QUESTION_COUNT[rid]
    progress = (f" Llevas **{done}/{total}** preguntas." if ctx["user"] and done < total
                else " ¡Ya la tienes completada!" if ctx["user"] else "")
    return answer(f"La sala **{room['title']}** ({room['difficulty']}) está en la ruta **{path['title']}**: "
                  f"{room['summary']}{progress}",
                  [act(f"Ir a {room['title']}", f"#sala/{rid}")])


def _challenge_answer(cid: str, ctx: dict) -> dict:
    ch = CHALLENGES[cid]
    solved = " Ya lo tienes resuelto." if cid in ctx["solved"] else ""
    return answer(f"El reto **{ch['title']}** es de {ch['category']} ({ch['difficulty']}, {ch['points']} pts).{solved} "
                  "Lo encontrarás en **Retos**, en su categoría.",
                  [act(f"Abrir {ch['title']}", f"#reto/{cid}")])


def _topic_answer(tid: str, ctx: dict) -> dict:
    stage, t = TOPICS[tid]
    text = f"**{t['title']}** está en la etapa «{stage['title']}» del roadmap ({stage['duration']}). {t['description']}"
    actions = [act("Verlo en el roadmap", "#roadmap", f".topic[data-topic='{tid}']")]
    if t["rooms"]:
        r = t["rooms"][0]
        text += f" Lo practicas en la sala **{ROOMS[r]['title']}**."
        actions.insert(0, act(f"Ir a {ROOMS[r]['title']}", f"#sala/{r}"))
    elif t["resources"]:
        text += f" Aún no hay sala aquí: en el roadmap te dejo recursos externos, como {t['resources'][0]['name']}."
    return answer(text, actions)


def _next_challenge(ctx: dict) -> dict:
    order = {"Fácil": 0, "Media": 1, "Difícil": 2}
    pending = sorted((c for c in STATIC if c["id"] not in ctx["solved"]), key=lambda c: (order[c["difficulty"]], c["points"]))
    if not pending:
        return answer("¡Has resuelto todos los retos oficiales! Crea uno nuevo con el generador.",
                      [act("Crear un reto", "#retos", "#gen-form")])
    c = pending[0]
    return answer(f"Te propongo **{c['title']}** ({c['category']}, {c['difficulty']}, {c['points']} pts). "
                  "Si te atascas, el analizador local y las pistas del Coach te ayudan.",
                  [act(f"Abrir {c['title']}", f"#reto/{c['id']}")]
                  + ([act(f"O {pending[1]['title']}", f"#reto/{pending[1]['id']}")] if len(pending) > 1 else []))


def _next_step(ctx: dict) -> dict:
    if not ctx["user"]:
        return answer("Te recomiendo empezar por la sala **Redes desde cero**: son unos diez minutos y es la base de todo. "
                      "Si creas una cuenta, guardarás tu progreso y sumarás puntos.",
                      [act("Empezar por Redes", "#sala/redes"), act("Crear cuenta", auth="register")])
    for p in PATHS:
        for r in p["rooms"]:
            done = len(ctx["answers"].get(r["id"], {}))
            if done < QUESTION_COUNT[r["id"]]:
                verb = "Sigue con" if done else "Tu siguiente paso: la sala"
                extra = f" (llevas {done}/{QUESTION_COUNT[r['id']]})" if done else ""
                acts = [act(f"Ir a {r['title']}", f"#sala/{r['id']}")]
                pending = [c for c in STATIC if c["id"] not in ctx["solved"] and c["difficulty"] == "Fácil"]
                if pending:
                    acts.append(act(f"O prueba el reto {pending[0]['title']}", f"#reto/{pending[0]['id']}"))
                return answer(f"{verb} **{r['title']}**{extra}, de la ruta {p['title']}.", acts)
    pending = [c for c in STATIC if c["id"] not in ctx["solved"]]
    if pending:
        c = min(pending, key=lambda c: c["points"])
        return answer(f"¡Has completado todas las salas! Ahora toca practicar: prueba el reto **{c['title']}** "
                      f"({c['difficulty']}).", [act(f"Abrir {c['title']}", f"#reto/{c['id']}")])
    return answer("Lo has completado todo. Puedes crear retos nuevos con el generador o seguir el roadmap con "
                  "recursos externos.", [act("Crear un reto", "#retos", "#gen-form"), act("Ver el roadmap", "#roadmap")])


def _progress(ctx: dict) -> dict:
    if not ctx["user"]:
        return answer("Aún no has iniciado sesión, así que no guardo tu progreso. Crea una cuenta y lo verás aquí.",
                      [act("Crear cuenta", auth="register"), act("Iniciar sesión", auth="login")])
    answered = sum(len(a) for a in ctx["answers"].values())
    total = sum(QUESTION_COUNT.values())
    rooms_done = sum(len(ctx["answers"].get(r, {})) == n for r, n in QUESTION_COUNT.items())
    rank = ctx.get("rank")
    pos = (f"Vas **#{rank['rank']}** en la clasificación con **{rank['score']} puntos**"
           + (f"; te faltan {rank['gap']} para adelantar a {rank['ahead']}." if rank.get("ahead") else ". ¡Vas primero!")
           if rank else "Todavía no apareces en la clasificación: responde una pregunta para entrar.")
    return answer(f"Tu progreso:\n\n- Preguntas de salas: **{answered}/{total}**\n- Salas completadas: **{rooms_done}/{len(ROOMS)}**\n"
                  f"- Retos resueltos: **{len(ctx['solved'] & set(CHALLENGES))}/{len(CHALLENGES)}**\n\n{pos}",
                  [act("Ver la clasificación", "#clasificacion", "#lb-me"), act("¿Qué hago ahora?", ask="¿Qué hago ahora?")])


VIEW_HELP = {
    "landing": ("Estás en la **portada**. Desde aquí puedes crear una cuenta o explorar las salas y el roadmap.",
                [act("Ver las salas", "#salas"), act("Ver el roadmap", "#roadmap")]),
    "roadmap": ("Estás en el **Roadmap**: el camino completo para aprender, en 5 etapas. Los temas con el círculo verde "
                "se practican aquí; los de borde discontinuo llevan recursos externos.", [act("Filtrar lo disponible", None, ".rm-filter")]),
    "rooms": ("Estás en **Salas**: cada sala tiene teoría corta y preguntas. Arriba ves tus insignias y debajo las rutas.",
              [act("Ver insignias", None, ".badges-box")]),
    "room": ("Estás dentro de una **sala**. Abre cada tarea, lee la teoría y responde. Si te atascas, el Coach de la derecha "
             "te orienta gratis.", [act("Ir al Coach", None, ".coach")]),
    "play": ("Estás en **Retos**: busca la flag `flag{...}` escondida en los datos. Arriba puedes crear retos nuevos.",
             [act("Crear un reto", None, "#gen-form")]),
    "challenge": ("Estás en la ficha de un **reto**. Arriba tienes los datos y el campo de la flag; debajo, el analizador; "
                  "a la derecha, el Coach y sus pistas.", [act("Ver el analizador", None, "#analyzer"), act("Ver las pistas", None, ".hint-buttons")]),
    "leaderboard": ("Estás en la **Clasificación**. Arriba ves tu posición y a quién tienes delante, luego el podio y la tabla.",
                    [act("Cambiar a semanal", None, ".lb-period")]),
}

DEFAULT_SUGGESTIONS = ["¿Por dónde empiezo?", "¿Dónde está el analizador?", "¿Cómo funcionan los puntos?", "Llévame al roadmap"]
# Sugerencias del saludo según la página en la que estés.
VIEW_SUGGESTIONS = {
    "landing": ["¿Por dónde empiezo?", "¿Qué es un CTF?", "¿Es gratis?"],
    "roadmap": ["¿Qué estudio primero?", "¿Dónde aprendo forense?", "Filtrar lo disponible aquí"],
    "rooms": ["¿Qué hago ahora?", "¿Dónde veo mis insignias?", "¿Diferencia entre salas y retos?"],
    "room": ["¿Qué hay en esta página?", "¿Cómo cambio el nivel del Coach?", "¿Qué hago ahora?"],
    "play": ["¿Cómo creo un reto?", "¿Cómo funcionan las pistas?", "¿Qué reto hago?"],
    "challenge": ["¿Dónde está el analizador?", "¿Cómo funcionan las pistas?", "¿Dónde meto la flag?"],
    "leaderboard": ["Mi progreso", "¿Cómo se ganan puntos?", "Ver la clasificación semanal"],
}


def reply(message: str, view: str, ctx: dict) -> dict:
    """ctx: {"user": nombre|None, "answers": {sala: {pregunta: ...}}, "solved": set(ids), "rank": dict|None}."""
    text = _plain(message).strip()
    r = _reply(text, view, ctx)
    if not text:
        r["suggestions"] = VIEW_SUGGESTIONS.get(view, DEFAULT_SUGGESTIONS)
    if not r["suggestions"]:
        r["suggestions"] = [s for s in DEFAULT_SUGGESTIONS if _plain(s) != text][:3]
    return r


def _reply(text: str, view: str, ctx: dict) -> dict:
    who = f", {ctx['user']}" if ctx["user"] else ""
    if not text or has(text, r"^(hola|buenas|hey|ey|holi|buenos dias|buenas tardes)\b"):
        return answer(f"¡Hola{who}! Soy **{NAME}**, la mascota de CTF Coach. Conozco toda la web: pregúntame dónde está "
                      "algo, qué hacer ahora o qué significa un concepto, y te llevo.")
    if has(text, r"\b(gracias|genial|perfecto|crack|guay)\b") and len(text.split()) <= 5:
        return answer("¡A mandar! Si necesitas algo más, aquí estoy, abajo a la derecha.")
    if has(text, r"quien eres", r"como te llamas", r"que eres", r"que (puedes|sabes) hacer", r"^ayuda$", r"en que me ayudas"):
        return answer(f"Soy **{NAME}**. Puedo:\n\n- Llevarte a cualquier sala, reto o tema del roadmap.\n"
                      "- Decirte dónde está cada cosa en la página y resaltarla.\n- Recomendarte qué hacer según tu progreso.\n"
                      "- Explicarte conceptos como Base64, XOR o phishing.\n\nPara las dudas de una sala o un reto concreto, "
                      "usa el **Coach** que hay dentro de cada uno.")

    # Cuenta
    if has(text, r"(olvide|recuperar|cambiar|resetear).{0,20}contrasena", r"contrasena.{0,20}(olvidada|perdida)"):
        return answer("De momento no hay recuperación ni cambio de contraseña: si la pierdes, tendrías que crear otra cuenta. "
                      "Guárdala en un gestor de contraseñas.")
    if has(text, r"(borrar|eliminar|darme de baja).{0,20}cuenta"):
        return answer("Por ahora no se puede borrar la cuenta desde la web. Solo se guarda tu usuario, una versión cifrada "
                      "de tu contraseña y tu progreso.")
    if has(text, r"cerrar sesion", r"\bsalir\b", r"desconectar", r"logout"):
        if not ctx["user"]:
            return answer("No tienes ninguna sesión abierta.")
        return answer("Para cerrar sesión, abre tu menú de usuario (tu avatar, arriba a la derecha) y pulsa «Cerrar sesión». "
                      "Ahí también tienes atajos a tu clasificación, tus insignias y el roadmap.",
                      [act("Mostrármelo", None, "#user-btn")])
    if has(text, r"(crear|hacerme|abrir|registrar).{0,15}cuenta", r"registr", r"apuntarme"):
        if ctx["user"]:
            return answer(f"Ya tienes la sesión iniciada como **{ctx['user']}**.")
        return answer("Crear una cuenta lleva diez segundos: elige un usuario y una contraseña de al menos 8 caracteres.",
                      [act("Crear cuenta", auth="register")])
    if has(text, r"iniciar sesion", r"entrar a mi cuenta", r"\blogin\b", r"loguear"):
        if ctx["user"]:
            return answer(f"Ya has iniciado sesión como **{ctx['user']}**.")
        return answer("Puedes iniciar sesión con el botón de arriba a la derecha.", [act("Iniciar sesión", auth="login")])

    # Personalizado
    if has(text, r"por donde empiezo", r"que hago( ahora)?", r"siguiente paso", r"recomienda", r"que me toca",
           r"no se que hacer", r"empezar", r"que (reto|sala) hago", r"que estudio primero"):
        return _next_challenge(ctx) if has(text, r"\breto") else _next_step(ctx)
    if has(text, r"mi progreso", r"mis puntos", r"cuantos puntos (tengo|llevo)", r"mi posicion", r"como voy", r"en que puesto"):
        return _progress(ctx)

    # Dónde estoy
    if has(text, r"donde estoy", r"que (hay|hago|es) (aqui|esta pagina)", r"esta pagina", r"explica(me)? (esta|la) pagina"):
        reply_text, actions = VIEW_HELP.get(view, VIEW_HELP["landing"])
        return answer(reply_text, actions)

    # Funciones concretas de la web
    for f in FEATURES:
        if has(text, *f["keys"]):
            return answer(f["reply"], f["actions"])

    # Una sala, un reto o un tema concretos
    rid, cid = _find(ROOM_ALIASES, text), _find(CHALLENGE_ALIASES, text)
    wants_challenge = has(text, r"\breto\b")
    if cid and (wants_challenge or not rid):
        return _challenge_answer(cid, ctx)
    if rid and not has(text, r"que es", r"que son", r"que significa"):
        return _room_answer(rid, ctx)

    # Conceptos del glosario
    for pattern, title, short, long in GLOSSARY:
        if pattern.search(text):
            room = GLOSSARY_ROOM.get(title)
            actions = [act(f"Practicarlo en {ROOMS[room]['title']}", f"#sala/{room}")] if room else []
            return answer(f"**{title}:** {short} {long}", actions)
    if rid:
        return _room_answer(rid, ctx)
    tid = _find_topic(text)
    if tid:
        return _topic_answer(tid, ctx)

    # Preguntas frecuentes
    for f in FAQ:
        if has(text, *f["keys"]):
            return answer(f["reply"], f.get("actions"))

    # Navegación general
    pages = [(r"\bsalas?\b", "#salas", "Salas"), (r"\bretos?\b", "#retos", "Retos"),
             (r"clasificacion|ranking|tabla|podio", "#clasificacion", "Clasificación"),
             (r"inicio|portada|principal", "#inicio", "la portada")]
    for pattern, goto, label in pages:
        if has(text, pattern):
            return answer(f"Te llevo a **{label}**.", [act(f"Ir a {label}", goto)])

    return answer("No estoy seguro de haberte entendido. Puedo llevarte a una sala o reto, decirte dónde está algo en la "
                  "página o explicarte un concepto. Prueba con algo como «llévame a la sala de Linux» o «¿qué es XOR?».")
