"""Genera app/rooms.json (rutas de aprendizaje, salas, tareas y preguntas).

Las respuestas en texto plano solo viven aquí: el JSON guarda su SHA-256 tras normalizarlas
(minúsculas, sin tildes, sin espacios sobrantes), así que ni el frontend ni el Coach las ven.

Uso:  python tools/build_rooms.py
"""

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.answers import answer_hash, mask, normalize  # noqa: E402

OUT = ROOT / "app" / "rooms.json"


def q(prompt, answers, points=10, notes="", options=None):
    return {"prompt": prompt, "answers": answers if isinstance(answers, list) else [answers],
            "points": points, "tutor_notes": notes, "options": options}


def auth_log() -> tuple[str, int]:
    lines, t = [], 0

    def ts(sec):
        return f"Oct 14 02:{40 + sec // 60:02d}:{sec % 60:02d}"

    fails = 0
    for ip, users in [("198.51.100.23", ["root"] * 4), ("192.0.2.140", ["admin", "admin", "test"])]:
        for user in users:
            lines.append(f"{ts(t)} web01 sshd[{2200 + t}]: Failed password for {user} from {ip} port {41000 + t} ssh2")
            t += 3
            fails += 1
    lines.append(f"{ts(t)} web01 sshd[{2200 + t}]: Accepted publickey for deploy from 10.0.5.20 port 52344 ssh2")
    t += 5
    for user in ["root", "admin", "oracle", "soporte", "soporte", "soporte"]:
        lines.append(f"{ts(t)} web01 sshd[{2200 + t}]: Failed password for {user} from 203.0.113.77 port {41000 + t} ssh2")
        t += 1
        fails += 1
    lines.append(f"{ts(t)} web01 sshd[{2200 + t}]: Accepted password for soporte from 203.0.113.77 port {41000 + t} ssh2")
    t += 40
    lines.append(f"{ts(t)} web01 sudo:  soporte : TTY=pts/2 ; PWD=/home/soporte ; USER=root ; "
                 "COMMAND=/usr/bin/tar czf /tmp/.copia.tgz /var/www")
    return "\n".join(lines), fails


LOG, FAILS = auth_log()

WORDLIST = ["123456", "contraseña", "qwerty", "futbol", "barcelona", "madrid", "mariposa", "princesa", "tequiero", "sol"]

PATHS = [
    {
        "id": "fundamentos",
        "title": "Fundamentos",
        "icon": "compass",
        "description": "Redes y Linux: lo que necesitas antes de cualquier otra cosa.",
        "rooms": [
            {
                "id": "redes",
                "title": "Redes desde cero",
                "icon": "network",
                "difficulty": "Fácil",
                "summary": "IPs, puertos, TCP/UDP y DNS explicados sin rodeos.",
                "tasks": [
                    {
                        "title": "Direcciones IP y puertos",
                        "content": """Una **dirección IP** identifica a un equipo en la red (por ejemplo `192.168.1.10`). Un **puerto** identifica a un servicio concreto dentro de ese equipo: es como el número de puerta dentro de un edificio.

Los puertos van del **0 al 65535**. Algunos servicios usan siempre el mismo por convenio:

- `21` FTP (transferencia de archivos, sin cifrar)
- `22` SSH (terminal remota cifrada)
- `53` DNS (resolución de nombres)
- `80` HTTP (web sin cifrar)
- `443` HTTPS (web cifrada)
- `3306` MySQL

Cuando auditas un sistema, saber qué puertos están abiertos te dice qué servicios hay que proteger.""",
                        "questions": [
                            q("¿Qué puerto usa SSH por defecto?", "22", notes="Búscalo en la lista de puertos habituales de la teoría."),
                            q("¿Qué puerto usa HTTPS por defecto?", "443", notes="Búscalo en la lista de puertos habituales: es la versión cifrada de la web."),
                            q("¿Cuál es el número de puerto más alto que existe?", "65535",
                              notes="La teoría da el rango completo de puertos. Curiosidad: ese máximo sale de que un puerto ocupa 16 bits."),
                        ],
                    },
                    {
                        "title": "TCP y UDP",
                        "content": """Los datos viajan usando un protocolo de transporte:

- **TCP** establece una conexión antes de enviar datos y garantiza que llegan completos y en orden. Lo usan la web, SSH o el correo.
- **UDP** envía los datos sin establecer conexión: es más rápido pero no garantiza la entrega. Lo usan DNS, el streaming o los juegos online.

TCP abre la conexión con el **saludo de tres vías** (*three-way handshake*):

1. El cliente envía un paquete `SYN`.
2. El servidor responde con `SYN-ACK`.
3. El cliente confirma con `ACK`.

Muchos escáneres de puertos se basan en este saludo para saber si un puerto está abierto.""",
                        "questions": [
                            q("¿Con qué paquete empieza el saludo de tres vías?", "SYN", notes="Fíjate en el primer paso de la lista numerada: quién envía qué."),
                            q("¿Qué protocolo de transporte usa normalmente DNS?", "UDP", options=["TCP", "UDP"],
                              notes="La teoría pone DNS como ejemplo de uno de los dos protocolos. ¿Cuál de ellos no establece conexión?"),
                        ],
                    },
                    {
                        "title": "DNS",
                        "content": """El **DNS** traduce nombres como `ejemplo.com` a direcciones IP. Funciona como una agenda: guarda distintos tipos de **registros**:

- `A`: nombre → dirección IPv4
- `AAAA`: nombre → dirección IPv6
- `MX`: servidor de correo del dominio
- `TXT`: texto libre (se usa, por ejemplo, para SPF y DKIM, que ayudan a frenar la suplantación de correo)
- `CNAME`: alias de otro nombre

Puedes consultarlos con `nslookup` o `dig` (por ejemplo `dig MX ejemplo.com`).""",
                        "questions": [
                            q("¿Qué tipo de registro indica el servidor de correo de un dominio?", "MX"),
                            q("¿Qué tipo de registro asocia un nombre a una dirección IPv4?", "A",
                              options=["A", "AAAA", "MX", "CNAME"]),
                        ],
                    },
                ],
            },
            {
                "id": "linux",
                "title": "Linux para seguridad",
                "icon": "terminal",
                "difficulty": "Fácil",
                "summary": "Moverte por la terminal, entender permisos y encontrar información.",
                "tasks": [
                    {
                        "title": "Moverse por el sistema",
                        "content": """Comandos básicos de la terminal:

- `pwd` muestra en qué carpeta estás.
- `ls` lista los archivos; `ls -l` da detalles y `ls -a` muestra también los **ocultos**.
- `cd carpeta` entra en una carpeta; `cd ..` sube un nivel.
- `cat archivo` muestra el contenido de un archivo.
- `whoami` te dice con qué usuario estás trabajando.

En Linux, un archivo es **oculto** si su nombre empieza por un punto, como `.bashrc` o `.ssh`. Muchos secretos de configuración viven en archivos ocultos, así que conviene revisarlos.""",
                        "questions": [
                            q("¿Qué opción de `ls` muestra los archivos ocultos?", ["-a", "-la", "-al"]),
                            q("¿Qué comando te dice con qué usuario estás trabajando?", "whoami"),
                        ],
                    },
                    {
                        "title": "Permisos",
                        "content": """Cada archivo tiene permisos para tres grupos: **propietario**, **grupo** y **otros**. Cada uno puede tener `r` (leer), `w` (escribir) y `x` (ejecutar).

```
-rw-r----- 1 ana contabilidad 1200 oct 14 notas.txt
```

Se lee en bloques de tres después del primer carácter: `rw-` (ana), `r--` (grupo contabilidad), `---` (otros).

En octal, `r`=4, `w`=2 y `x`=1, y se suman en cada bloque. Así `rw-r-----` es `640`. Los permisos se cambian con `chmod` (por ejemplo `chmod 600 clave.pem`).

Regla de oro: las claves privadas y los archivos con contraseñas solo deben poder leerlos su propietario.""",
                        "questions": [
                            q("¿Qué permisos tiene el grupo sobre notas.txt? (formato rwx, con guiones)", "r--",
                              notes="Separa los permisos en bloques de tres después del primer carácter: el segundo bloque es el del grupo."),
                            q("¿Cuál es el valor octal de `rw-------`?", "600",
                              notes="Calcula cada bloque por separado: r vale 4, w vale 2, x vale 1 y un guion vale 0. Luego escribe los tres resultados seguidos."),
                            q("¿Qué comando cambia los permisos de un archivo?", "chmod"),
                        ],
                    },
                    {
                        "title": "Buscar información",
                        "content": """Dos herramientas que usarás a diario:

- `grep texto archivo` busca líneas que contienen un texto (`grep -i` ignora mayúsculas, `grep -r` busca en carpetas).
- `find / -name "*.conf"` busca archivos por nombre.

Archivos importantes del sistema:

- `/etc/passwd` lista los usuarios (pero **no** sus contraseñas).
- `/etc/shadow` guarda los **hashes** de las contraseñas y solo root puede leerlo.
- `/var/log/` contiene los registros del sistema, como `auth.log` con los inicios de sesión.""",
                        "questions": [
                            q("¿Qué comando busca texto dentro de archivos?", "grep"),
                            q("¿En qué archivo se guardan los hashes de las contraseñas? (ruta completa)", "/etc/shadow"),
                        ],
                    },
                ],
            },
        ],
    },
    {
        "id": "cripto",
        "title": "Criptografía",
        "icon": "lock",
        "description": "Codificación, cifrado y hashes: qué protege de verdad y qué no.",
        "rooms": [
            {
                "id": "codificacion",
                "title": "Codificar no es cifrar",
                "icon": "binary",
                "difficulty": "Fácil",
                "summary": "Base64, hexadecimal y la diferencia entre codificar y cifrar.",
                "tasks": [
                    {
                        "title": "Codificación",
                        "content": """**Codificar** es cambiar la representación de unos datos para transportarlos, **sin ninguna clave**. Cualquiera puede deshacerlo, así que no protege nada.

- **Hexadecimal**: cada byte se escribe con 2 caracteres de `0-9` y `a-f`. `Hola` → `486f6c61`.
- **Base64**: usa `A-Z`, `a-z`, `0-9`, `+` y `/`, y a veces termina en `=`. `Hola` → `SG9sYQ==`.

Para decodificar puedes usar CyberChef, el **Analizador local** de los retos o Python:

```
import base64
base64.b64decode("SG9sYQ==").decode()
```

Un error real muy común es "proteger" contraseñas o tokens con Base64.""",
                        "data": "c2VndXJpZGFk",
                        "questions": [
                            q("Decodifica el texto en Base64 de los datos. ¿Qué palabra es?", "seguridad", points=20,
                              notes="Decodifica los datos de la tarea desde Base64: con CyberChef (From Base64) o con el código de ejemplo de la teoría."),
                            q("¿Cuántos caracteres hexadecimales representan un byte?", "2"),
                        ],
                    },
                    {
                        "title": "Cifrado simétrico y asimétrico",
                        "content": """**Cifrar** sí protege: sin la clave no se puede leer el mensaje.

- **Simétrico**: la misma clave cifra y descifra. Es rápido. Ejemplo: **AES**.
- **Asimétrico**: hay un par de claves. La **pública** se puede compartir con cualquiera y sirve para cifrar; la **privada** se guarda en secreto y sirve para descifrar (y para firmar). Ejemplo: **RSA**.

HTTPS combina los dos: usa criptografía asimétrica para acordar una clave y después cifra la conversación con una clave simétrica.""",
                        "questions": [
                            q("¿AES es un cifrado simétrico o asimétrico?", "Simétrico", options=["Simétrico", "Asimétrico"]),
                            q("En RSA, ¿qué clave debes mantener en secreto?", ["privada", "la privada", "clave privada",
                                                                                 "la clave privada"]),
                        ],
                    },
                ],
            },
            {
                "id": "hashes",
                "title": "Hashes y contraseñas",
                "icon": "hash",
                "difficulty": "Media",
                "summary": "Cómo se guardan las contraseñas y por qué algunas formas son peligrosas.",
                "tasks": [
                    {
                        "title": "¿Qué es un hash?",
                        "content": """Una **función hash** convierte cualquier dato en una huella de longitud fija. Es de **un solo sentido**: no se puede "deshacer".

Longitud en caracteres hexadecimales de los más conocidos:

- **MD5**: 32 (obsoleto)
- **SHA-1**: 40 (obsoleto)
- **SHA-256**: 64

Un cambio mínimo en la entrada produce un hash totalmente distinto. Por eso se usan para comprobar la integridad de archivos y para guardar contraseñas sin guardarlas en claro.""",
                        "data": "5f4dcc3b5aa765d61d8327deb882cf99",
                        "questions": [
                            q("¿Cuántos caracteres hexadecimales tiene un hash SHA-256?", "64"),
                            q("¿Qué algoritmo generó el hash de los datos?", "MD5", options=["MD5", "SHA-1", "SHA-256"],
                              notes="Cuenta los caracteres del hash de los datos y compáralo con las longitudes de la teoría."),
                        ],
                    },
                    {
                        "title": "Sal y algoritmos lentos",
                        "content": """Si dos usuarios tienen la misma contraseña, tendrán el mismo hash. Además, existen **tablas arcoíris**: listas enormes de hashes ya calculados.

Las defensas son:

- **Sal** (*salt*): un valor aleatorio distinto para cada usuario que se añade a la contraseña antes de calcular el hash. Así dos contraseñas iguales dan hashes distintos y las tablas precalculadas no sirven.
- **Algoritmos lentos** diseñados para contraseñas: **bcrypt**, **scrypt** o **Argon2**. Son lentos a propósito para que probar millones de contraseñas sea muy costoso.

MD5 o SHA-256 a secas son demasiado rápidos para guardar contraseñas.""",
                        "questions": [
                            q("¿Cómo se llama el valor aleatorio que se añade a la contraseña antes del hash?", ["sal", "salt"]),
                            q("¿Cuál de estas opciones es adecuada para guardar contraseñas?", "bcrypt",
                              options=["MD5", "SHA-1", "bcrypt", "Base64"]),
                        ],
                    },
                    {
                        "title": "Práctica: ataque de diccionario",
                        "content": """Como un hash no se puede deshacer, para recuperar una contraseña débil se prueba una lista de candidatas: se calcula el hash de cada una y se compara con el objetivo. Es un **ataque de diccionario**, y por eso las contraseñas comunes son tan peligrosas.

En los datos tienes el hash MD5 (sin sal) de una contraseña filtrada y una lista de contraseñas habituales en España. Descubre cuál es.

```
import hashlib
hashlib.md5("candidata".encode()).hexdigest()
```""",
                        "data": f"hash: {hashlib.md5(b'mariposa').hexdigest()}\n\nlista:\n" + "\n".join(WORDLIST),
                        "questions": [
                            q("¿Cuál es la contraseña?", "mariposa", points=30,
                              notes="Calcula el MD5 de cada palabra de la lista y compáralo con el hash. Un bucle `for` en Python con el ejemplo de la teoría lo hace en tres líneas."),
                        ],
                    },
                ],
            },
        ],
    },
    {
        "id": "blueteam",
        "title": "Blue Team",
        "icon": "shield",
        "description": "Detectar y analizar ataques: logs y correos de phishing.",
        "rooms": [
            {
                "id": "logs",
                "title": "Investigando un login sospechoso",
                "icon": "search",
                "difficulty": "Media",
                "summary": "Analiza un auth.log real y reconstruye lo que pasó.",
                "tasks": [
                    {
                        "title": "Leer auth.log",
                        "content": """En Linux, los inicios de sesión SSH quedan registrados en `/var/log/auth.log`. Cada línea tiene la fecha, el equipo, el programa y el mensaje:

```
Oct 14 02:40:00 web01 sshd[2200]: Failed password for root from 198.51.100.23 port 41000 ssh2
```

Mensajes clave:

- `Failed password`: intento fallido.
- `Accepted password`: inicio de sesión con contraseña **correcto**.
- `Accepted publickey`: inicio de sesión con clave SSH (más seguro).
- Líneas de `sudo`: un usuario ejecutó algo como administrador.

Muchos fallos seguidos desde la misma IP indican un **ataque de fuerza bruta**. Lo crítico es encontrar si alguno terminó en éxito.""",
                        "questions": [
                            q("¿Qué texto aparece en el log cuando un inicio de sesión con contraseña tiene éxito?",
                              "Accepted password"),
                        ],
                    },
                    {
                        "title": "La investigación",
                        "content": """Estos son los registros del servidor `web01` de anoche. Reconstruye el incidente.

Consejo: en una terminal real usarías `grep "Failed" auth.log | wc -l` para contar fallos, o `grep "Accepted" auth.log` para ver los accesos correctos.""",
                        "data": LOG,
                        "questions": [
                            q("¿Cuántos intentos de inicio de sesión fallidos hay en total?", str(FAILS), points=20,
                              notes="Cuenta todas las líneas con `Failed password`, sean de la IP que sean. En una terminal: `grep -c`."),
                            q("¿Desde qué IP entró el atacante?", "203.0.113.77", points=20,
                              notes="Busca la IP que tiene fallos y, después, un `Accepted password`. Ojo con el `Accepted publickey` de la red interna: es una conexión legítima."),
                            q("¿Con qué usuario consiguió entrar?", "soporte", points=20,
                              notes="Mira la línea `Accepted password` de la IP atacante: el usuario aparece después de «for»."),
                            q("¿Qué programa ejecutó como administrador después de entrar?", ["tar", "/usr/bin/tar"], points=20,
                              notes="Mira la línea de `sudo`, en el campo `COMMAND`: el programa es lo que va justo después, sin la ruta."),
                        ],
                    },
                ],
            },
            {
                "id": "phishing",
                "title": "Detectar phishing",
                "icon": "mail",
                "difficulty": "Fácil",
                "summary": "Aprende a reconocer las señales de un correo fraudulento.",
                "tasks": [
                    {
                        "title": "Señales de alarma",
                        "content": """El **phishing** intenta engañarte para que entregues credenciales o abras algo malicioso. Señales típicas:

- **Urgencia o miedo**: "tu cuenta se bloqueará en 24 horas".
- **Remitente falso**: el nombre visible dice "Tu Banco" pero el dominio real del correo es otro.
- **Enlaces engañosos**: el texto del enlace muestra una web legítima, pero el destino real es distinto. Pasa el ratón por encima antes de hacer clic.
- **Adjuntos inesperados**, sobre todo `.zip`, `.html` o documentos con macros.
- Peticiones de contraseñas o códigos: un servicio legítimo nunca te los pedirá por correo.

Ante la duda, entra en la web escribiendo tú la dirección, nunca desde el enlace del correo.""",
                        "questions": [
                            q("¿Qué debes hacer antes de hacer clic en un enlace para ver su destino real?",
                              ["pasar el raton por encima", "pasar el raton", "poner el raton encima", "hover"],
                              notes="Repasa la lista de señales, en el punto sobre enlaces engañosos."),
                        ],
                    },
                    {
                        "title": "Analiza este correo",
                        "content": "Una empleada ha reenviado este correo al equipo de seguridad. Analízalo (el banco es ficticio).",
                        "data": """De: "Banco Norte - Seguridad" <avisos@banconorte-verificacion.com>
Para: laura.gomez@empresa.es
Asunto: URGENTE: actividad sospechosa en su cuenta

Estimada clienta:

Hemos detectado un acceso no autorizado a su banca online. Por su seguridad,
su cuenta será BLOQUEADA en las próximas 2 horas si no verifica su identidad.

Verifique ahora: [https://www.banconorte.es/clientes]
    (destino real del enlace: http://banconorte.acceso-clientes.top/login)

Atentamente,
Departamento de Seguridad de Banco Norte""",
                        "questions": [
                            q("¿Cuál es el dominio real desde el que se envió el correo?", "banconorte-verificacion.com",
                              points=20, notes="Fíjate en lo que va después de la @ en la dirección del remitente, no en el nombre que se muestra."),
                            q("¿A qué dominio lleva realmente el enlace? (sin http ni ruta)", "banconorte.acceso-clientes.top",
                              points=20, notes="Fíjate en el destino real del enlace, no en el texto que se ve. Quita el protocolo y la ruta."),
                            q("¿Qué táctica de presión usa el correo?", "Urgencia",
                              options=["Urgencia", "Un premio", "Curiosidad", "Autoridad de un jefe"]),
                        ],
                    },
                ],
            },
        ],
    },
    {
        "id": "web",
        "title": "Web",
        "icon": "code",
        "description": "Cómo funciona la web y cómo se defiende.",
        "rooms": [
            {
                "id": "http",
                "title": "Cómo funciona la web",
                "icon": "globe",
                "difficulty": "Fácil",
                "summary": "Peticiones HTTP, códigos de estado, cookies y código fuente.",
                "tasks": [
                    {
                        "title": "Peticiones y respuestas",
                        "content": """El navegador habla con el servidor mediante **HTTP**. Cada petición tiene un **método**:

- `GET`: pedir un recurso (una página, una imagen).
- `POST`: enviar datos, por ejemplo un formulario de login.
- `PUT` / `DELETE`: modificar o borrar recursos (habitual en APIs).

El servidor responde con un **código de estado**:

- `200` OK
- `301` / `302` redirección
- `401` no autenticado (falta iniciar sesión)
- `403` prohibido (estás identificado, pero no tienes permiso)
- `404` no encontrado
- `500` error interno del servidor

Puedes ver todas las peticiones en las herramientas de desarrollador del navegador (F12, pestaña Red).""",
                        "questions": [
                            q("¿Qué código de estado significa 'no encontrado'?", "404"),
                            q("¿Qué método se usa normalmente para enviar un formulario de login?", "POST",
                              options=["GET", "POST", "DELETE"]),
                            q("¿Qué significa un 403?", "Prohibido: no tienes permiso",
                              options=["No has iniciado sesión", "Prohibido: no tienes permiso", "Error del servidor"]),
                        ],
                    },
                    {
                        "title": "Cookies",
                        "content": """HTTP no recuerda nada entre peticiones. Para saber quién eres, el servidor te da una **cookie de sesión** que el navegador envía en cada petición. Quien robe esa cookie puede hacerse pasar por ti.

Atributos de seguridad de las cookies:

- `HttpOnly`: JavaScript no puede leer la cookie. Reduce el daño de un ataque XSS.
- `Secure`: la cookie solo se envía por HTTPS.
- `SameSite`: limita el envío de la cookie desde otras webs (ayuda contra CSRF).

Esta misma plataforma usa una cookie `HttpOnly` con `SameSite=Lax` para tu sesión.""",
                        "questions": [
                            q("¿Qué atributo impide que JavaScript lea una cookie?", "HttpOnly"),
                            q("¿Qué atributo hace que la cookie solo se envíe por HTTPS?", "Secure"),
                        ],
                    },
                    {
                        "title": "El código fuente",
                        "content": """Todo lo que llega al navegador lo puede ver el usuario: HTML, JavaScript y **comentarios**. Los desarrolladores a veces se dejan notas, rutas internas o claves de prueba. Revisar el código fuente (Ctrl+U) es uno de los primeros pasos de cualquier auditoría web.

Aquí tienes el código de una página de una empresa ficticia.""",
                        "data": """<!DOCTYPE html>
<html>
<head>
  <title>Portal de empleados</title>
  <!-- TODO: quitar antes de publicar -->
  <!-- clave de la API de pruebas: dev-7f3a-temporal -->
  <script src="/js/app.js"></script>
</head>
<body>
  <h1>Bienvenido al portal</h1>
</body>
</html>""",
                        "questions": [
                            q("¿Qué clave de API aparece olvidada en el código?", "dev-7f3a-temporal", points=20,
                              notes="Busca en los comentarios HTML `<!-- ... -->`. Por eso los secretos nunca deben llegar al navegador."),
                        ],
                    },
                ],
            },
            {
                "id": "owasp",
                "title": "Defensa web: OWASP Top 10",
                "icon": "wall",
                "difficulty": "Media",
                "summary": "Las vulnerabilidades web más comunes y cómo se previenen.",
                "tasks": [
                    {
                        "title": "Control de acceso",
                        "content": """El **OWASP Top 10** es la lista de riesgos web más importantes. En la edición de 2021, el primer puesto es **Broken Access Control** (control de acceso roto): un usuario puede ver o modificar datos que no son suyos.

Ejemplo típico: la URL `/facturas/1042` muestra tu factura y nadie comprueba si `1043` también es tuya.

Defensas:

- Comprobar **en el servidor**, en cada petición, que el usuario tiene permiso sobre ese recurso concreto.
- Denegar por defecto.
- No confiar en que algo esté "escondido" en el frontend: el cliente se puede modificar.""",
                        "questions": [
                            q("¿Qué categoría ocupa el primer puesto del OWASP Top 10 de 2021?",
                              ["Broken Access Control", "control de acceso roto", "a01"]),
                            q("¿Dónde debe comprobarse que un usuario puede acceder a un recurso?", "En el servidor",
                              options=["En el navegador", "En el servidor", "En el HTML"]),
                        ],
                    },
                    {
                        "title": "Inyección",
                        "content": """Hay **inyección** cuando la aplicación mezcla datos del usuario con código, por ejemplo construyendo una consulta SQL pegando textos. El usuario puede entonces alterar la consulta.

La defensa correcta son las **consultas parametrizadas**: la consulta y los datos viajan por separado, así que los datos nunca se interpretan como código.

```
cursor.execute("SELECT * FROM usuarios WHERE nombre = ?", (nombre,))
```

Otras medidas que ayudan: validar la entrada, usar un ORM, dar a la cuenta de la base de datos los mínimos permisos y no mostrar errores detallados al usuario.""",
                        "questions": [
                            q("¿Cuál es la defensa principal contra la inyección SQL?", "Consultas parametrizadas",
                              options=["Ocultar los mensajes de error", "Consultas parametrizadas", "Usar POST en vez de GET",
                                       "Cifrar la base de datos"]),
                        ],
                    },
                    {
                        "title": "Cross-Site Scripting (XSS)",
                        "content": """El **XSS** ocurre cuando una web muestra datos de un usuario sin tratarlos y el navegador de otra persona los ejecuta como JavaScript. Así se pueden robar sesiones o modificar la página.

Defensas:

- **Escapar la salida**: convertir caracteres como `<` y `>` en `&lt;` y `&gt;` para que se muestren como texto. Los frameworks modernos lo hacen por defecto.
- Cabecera **Content-Security-Policy (CSP)**: limita desde dónde puede cargar scripts la página.
- Cookies `HttpOnly`, para que un script no pueda leer la sesión.""",
                        "questions": [
                            q("¿Qué cabecera HTTP limita desde dónde se pueden cargar scripts?",
                              ["Content-Security-Policy", "CSP"]),
                            q("¿Cómo se debe mostrar el carácter `<` que escribe un usuario para que no se interprete como HTML?",
                              "&lt;", notes="Repasa el primer punto de la lista de defensas."),
                        ],
                    },
                ],
            },
        ],
    },
]


def build() -> list[dict]:
    return PATHS


def main():
    out = []
    seen = set()
    for path in build():
        rooms = []
        for room in path["rooms"]:
            assert room["id"] not in seen, room["id"]
            seen.add(room["id"])
            tasks = []
            for ti, task in enumerate(room["tasks"], 1):
                questions = []
                for qi, qq in enumerate(task["questions"], 1):
                    if qq["options"]:
                        assert all(a in qq["options"] for a in qq["answers"]), qq["prompt"]
                    for a in qq["answers"]:
                        na = normalize(a)
                        if len(na) >= 3 and qq["tutor_notes"]:
                            assert not re.search(rf"(?<!\w){re.escape(na)}(?!\w)", normalize(qq["tutor_notes"])), \
                                f"{room['id']}: la respuesta '{a}' aparece en tutor_notes"
                    questions.append({
                        "id": f"t{ti}q{qi}",
                        "prompt": qq["prompt"],
                        "points": qq["points"],
                        "options": qq["options"],
                        "mask": None if qq["options"] else mask(qq["answers"][0]),
                        "tutor_notes": qq["tutor_notes"],
                        "answer_sha256": sorted({answer_hash(a) for a in qq["answers"]}),
                    })
                tasks.append({"id": f"t{ti}", "title": task["title"], "content": task["content"],
                              "data": task.get("data"), "questions": questions})
            rooms.append({k: room[k] for k in ("id", "title", "icon", "difficulty", "summary")} | {"tasks": tasks})
        out.append({k: path[k] for k in ("id", "title", "icon", "description")} | {"rooms": rooms})
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    n_q = sum(len(t["questions"]) for p in out for r in p["rooms"] for t in r["tasks"])
    print(f"{len(out)} rutas, {len(seen)} salas, {n_q} preguntas escritas en {OUT}")


if __name__ == "__main__":
    main()
