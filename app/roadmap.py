"""Roadmap general de aprendizaje en ciberseguridad.

Incluye temas que la plataforma todavía no cubre: esos llevan recursos externos.
Los temas con salas o retos enlazados muestran el progreso del usuario.
"""

from .challenges import STATIC_BY_ID
from .rooms import QUESTION_COUNT, ROOMS


def topic(id, title, description, skills, rooms=(), challenges=(), resources=()):
    return {"id": id, "title": title, "description": description, "skills": list(skills),
            "rooms": list(rooms), "challenges": list(challenges),
            "resources": [{"name": n, "url": u} for n, u in resources]}


R_MDN_HTTP = ("MDN · Guía de HTTP", "https://developer.mozilla.org/es/docs/Web/HTTP")
R_BANDIT = ("OverTheWire · Bandit", "https://overthewire.org/wargames/bandit/")
R_PORTSWIGGER = ("PortSwigger Web Security Academy", "https://portswigger.net/web-security")
R_OWASP_TOP10 = ("OWASP Top 10", "https://owasp.org/www-project-top-ten/")
R_ATTACK = ("MITRE ATT&CK", "https://attack.mitre.org/")
R_NIST_CSF = ("NIST Cybersecurity Framework", "https://www.nist.gov/cyberframework")
R_PICO = ("picoCTF", "https://picoctf.org/")
R_CYBERDEF = ("CyberDefenders", "https://cyberdefenders.org/")
R_THM = ("TryHackMe", "https://tryhackme.com/")
R_HTB = ("Hack The Box Academy", "https://academy.hackthebox.com/")
R_PYTHON = ("Tutorial oficial de Python", "https://docs.python.org/es/3/tutorial/")
R_INCIBE = ("INCIBE · Formación", "https://www.incibe.es/")
R_CCN = ("CCN-CERT · Guías CCN-STIC", "https://www.ccn-cert.cni.es/")
R_MS_LEARN = ("Microsoft Learn · Windows", "https://learn.microsoft.com/es-es/training/")
R_SANS_POSTERS = ("SANS · Pósters y hojas de referencia", "https://www.sans.org/posters/")
R_CLOUD_AWS = ("AWS Skill Builder · Seguridad", "https://skillbuilder.aws/")

ROADMAP = [
    {
        "id": "fundamentos",
        "title": "Fundamentos técnicos",
        "duration": "1-3 meses",
        "description": "Sin esto, todo lo demás se queda cojo. Entender cómo funcionan las redes, los sistemas y la web.",
        "topics": [
            topic("redes", "Redes", "Modelo TCP/IP, direcciones IP, puertos, TCP y UDP, DNS y cómo viaja un paquete.",
                  ["TCP/IP", "Puertos", "DNS", "Subredes"], rooms=["redes"]),
            topic("linux", "Linux", "Moverte por la terminal, permisos, procesos, usuarios y dónde están los logs.",
                  ["Terminal", "Permisos", "grep/find", "Procesos"], rooms=["linux"], resources=[R_BANDIT]),
            topic("web", "Cómo funciona la web", "Peticiones y respuestas HTTP, cookies, sesiones y lo que llega al navegador.",
                  ["HTTP", "Cookies", "DevTools"], rooms=["http"], resources=[R_MDN_HTTP]),
            topic("windows", "Windows", "Usuarios y grupos, permisos NTFS, servicios, registro y visor de eventos.",
                  ["PowerShell", "Registro", "Eventos"], resources=[R_MS_LEARN]),
            topic("programacion", "Programación y scripting", "Python y Bash para automatizar tareas, procesar datos y entender código ajeno.",
                  ["Python", "Bash", "Expresiones regulares"], resources=[R_PYTHON]),
        ],
    },
    {
        "id": "bases",
        "title": "Bases de seguridad",
        "duration": "1-2 meses",
        "description": "Los conceptos que comparten todas las ramas: qué se protege, de quién y con qué herramientas.",
        "topics": [
            topic("conceptos", "Conceptos y marcos", "Confidencialidad, integridad y disponibilidad; amenaza, vulnerabilidad y riesgo; marcos como NIST CSF y MITRE ATT&CK.",
                  ["Tríada CIA", "Riesgo", "ATT&CK"], resources=[R_NIST_CSF, R_ATTACK]),
            topic("cripto", "Criptografía aplicada", "Diferencia entre codificar, cifrar y hacer hash; cifrado simétrico y asimétrico; por qué fallan los cifrados clásicos.",
                  ["Base64/hex", "AES/RSA", "Hashes"], rooms=["codificacion"], challenges=["capas", "cesar", "xor"]),
            topic("auth", "Autenticación y contraseñas", "Cómo se guardan las contraseñas, sal, algoritmos lentos, tokens como JWT y autenticación multifactor.",
                  ["bcrypt/Argon2", "JWT", "MFA"], rooms=["hashes"], challenges=["hash", "jwt"]),
            topic("social", "Ingeniería social", "Phishing, pretexting y suplantación: cómo reconocerlos y cómo formar a otras personas.",
                  ["Phishing", "Concienciación"], rooms=["phishing"]),
        ],
    },
    {
        "id": "blue",
        "title": "Defensa (Blue Team)",
        "duration": "3-6 meses",
        "description": "Detectar, investigar y responder. Es la puerta de entrada más habitual al sector (analista SOC).",
        "topics": [
            topic("logs", "Análisis de logs", "Leer registros de sistemas y servicios para reconstruir qué ha pasado.",
                  ["auth.log", "Eventos de Windows", "Línea temporal"], rooms=["logs"], challenges=["logs"]),
            topic("siem", "SIEM y monitorización", "Centralizar eventos, escribir reglas de detección y reducir falsos positivos.",
                  ["Reglas de detección", "Sigma", "Alertas"], resources=[R_CYBERDEF]),
            topic("ir", "Respuesta a incidentes", "Las fases de un incidente: preparación, detección, contención, erradicación, recuperación y lecciones aprendidas.",
                  ["Playbooks", "Contención", "Comunicación"], resources=[R_SANS_POSTERS]),
            topic("forense", "Forense digital", "Adquirir y analizar evidencias de disco, memoria y red sin alterarlas.",
                  ["Cadena de custodia", "Memoria", "Artefactos"], resources=[R_CYBERDEF]),
            topic("bastionado", "Bastionado de sistemas", "Reducir la superficie de ataque: configuraciones seguras, parches y mínimos privilegios.",
                  ["Guías CIS/CCN", "Parches", "Mínimo privilegio"], resources=[R_CCN]),
        ],
    },
    {
        "id": "red",
        "title": "Seguridad ofensiva (ética)",
        "duration": "3-6 meses",
        "description": "Pensar como un atacante para encontrar fallos antes que él. Siempre en laboratorios propios o con autorización.",
        "topics": [
            topic("metodologia", "Metodología de auditoría", "Alcance y autorización, reconocimiento, enumeración y redacción del informe final.",
                  ["Alcance", "Reconocimiento", "Informe"], resources=[R_THM]),
            topic("web-sec", "Seguridad de aplicaciones web", "Las vulnerabilidades del OWASP Top 10: cómo se producen, cómo se detectan y cómo se corrigen.",
                  ["OWASP Top 10", "Control de acceso", "Inyección"], rooms=["owasp"], challenges=["fuente"], resources=[R_PORTSWIGGER, R_OWASP_TOP10]),
            topic("privesc", "Escalada de privilegios", "Por qué una mala configuración permite pasar de usuario normal a administrador, en Linux y Windows.",
                  ["Configuraciones débiles", "Permisos", "Servicios"], resources=[R_HTB]),
            topic("ad", "Directorio Activo", "Cómo funciona la autenticación en redes Windows corporativas y sus debilidades más comunes.",
                  ["Kerberos", "Dominios", "Políticas de grupo"], resources=[R_HTB]),
            topic("ctf", "Práctica con CTF", "Competiciones y retos para entrenar la resolución de problemas bajo presión.",
                  ["Resolución de problemas", "Writeups"], challenges=["capas", "cesar", "xor", "fuente", "logs", "hash", "jwt"], resources=[R_PICO]),
        ],
    },
    {
        "id": "especializacion",
        "title": "Especialización",
        "duration": "Continua",
        "description": "Con la base asentada, toca elegir rama. No hace falta dominarlas todas.",
        "topics": [
            topic("cloud", "Seguridad en la nube", "Identidades y permisos, configuraciones erróneas y el modelo de responsabilidad compartida.",
                  ["IAM", "AWS/Azure", "Configuración"], resources=[R_CLOUD_AWS]),
            topic("malware", "Análisis de malware", "Análisis estático y dinámico en entornos aislados para entender qué hace una muestra.",
                  ["Sandbox", "Ingeniería inversa", "Indicadores"], resources=[R_SANS_POSTERS]),
            topic("appsec", "AppSec y DevSecOps", "Integrar la seguridad en el desarrollo: revisión de código, análisis automático y gestión de dependencias.",
                  ["Revisión de código", "SAST/DAST", "Cadena de suministro"], resources=[R_OWASP_TOP10]),
            topic("grc", "Gobierno, riesgo y cumplimiento", "Normativa y estándares: ENS, RGPD, ISO 27001 y NIS2. Análisis de riesgos y políticas.",
                  ["ISO 27001", "ENS", "RGPD", "NIS2"], resources=[R_INCIBE, R_CCN]),
            topic("certs", "Certificaciones", "Orientativas para validar conocimientos: CompTIA Security+, eJPT, BTL1 y, más adelante, OSCP.",
                  ["Security+", "eJPT", "BTL1", "OSCP"]),
        ],
    },
]

for _stage in ROADMAP:
    for _t in _stage["topics"]:
        assert all(r in ROOMS for r in _t["rooms"]), _t["id"]
        assert all(c in STATIC_BY_ID for c in _t["challenges"]), _t["id"]


def build(room_answers: dict[str, dict], solved: set[str]) -> list[dict]:
    """room_answers: {room_id: {question_id: ...}}; solved: ids de retos resueltos."""
    out = []
    for stage in ROADMAP:
        topics = []
        for t in stage["topics"]:
            total = sum(QUESTION_COUNT[r] for r in t["rooms"]) + len(t["challenges"])
            done = sum(len(room_answers.get(r, {})) for r in t["rooms"]) + sum(c in solved for c in t["challenges"])
            status = "externo" if not total else "completado" if done == total else "en_curso" if done else "disponible"
            topics.append(t | {
                "status": status, "done": done, "total": total,
                "rooms": [{"id": r, "title": ROOMS[r]["title"], "done": len(room_answers.get(r, {})),
                           "total": QUESTION_COUNT[r]} for r in t["rooms"]],
                "challenges": [{"id": c, "title": STATIC_BY_ID[c]["title"], "solved": c in solved} for c in t["challenges"]],
            })
        out.append({k: stage[k] for k in ("id", "title", "duration", "description")} | {"topics": topics})
    return out
