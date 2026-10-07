"""Entrena el identificador de codificaciones y cifrados.

Uso:  python -m ml.train
Genera ml/model.joblib y gráficas en ml/reports/.
"""

import base64
import hashlib
import json
import random
import secrets
import sys
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.metrics import classification_report, confusion_matrix  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.transforms import apply  # noqa: E402
from ml.fastforest import FastForest  # noqa: E402
from ml.features import FEATURE_NAMES, extract  # noqa: E402
from ml.labels import LABELS  # noqa: E402

MODEL_PATH = Path(__file__).resolve().parent / "model.joblib"
REPORTS = Path(__file__).resolve().parent / "reports"
SAMPLES_PER_CLASS = 2500

WORDS = """el la los las de del en un una y que por para con sin sobre entre hasta desde
mensaje secreto clave servidor contraseña usuario acceso red sistema ataque defensa equipo
general ejército barco pirata tesoro mapa noche ciudad puerto castillo rey reina espía agente
código cifrado archivo registro datos firma token puerta llave correo ordenador seguridad
encontrar enviar guardar abrir cerrar proteger esconder descubrir atacar buscar llegar
mañana hoy siempre nunca pronto tarde aquí allí norte sur este oeste rojo verde azul
importante peligroso nuevo antiguo oculto rápido lento grande pequeño primero último""".split()

STYLES = dict(blue="#3987e5", orange="#d95926", text="#e6edf3", muted="#8b949e", grid="#30363d")


def random_flag(rng: random.Random) -> str:
    leet = str.maketrans("aeios", "43105")
    words = [rng.choice(WORDS) for _ in range(rng.randint(1, 4))]
    body = "_".join(w.translate(leet) if rng.random() < 0.5 else w for w in words)
    return f"flag{{{body}}}"


ENGLISH = """the of and to in is for on with that this from user password login failed accepted
server admin root error warning session port connection request access denied secret key hello world
message meet me at night north gate attack defend the castle quick brown fox jumps over lazy dog
we will be there tomorrow keep it safe never share your code with anyone else""".split()

MORSE_CODE = dict(zip("abcdefghijklmnopqrstuvwxyz0123456789", """.- -... -.-. -.. . ..-. --. .... .. .--- -.- .-.. --
-. --- .--. --.- .-. ... - ..- ...- .-- -..- -.-- --.. ----- .---- ..--- ...-- ....- ..... -.... --... ---.. ----.""".split()))


def random_ip(rng: random.Random) -> str:
    return ".".join(str(rng.randint(1, 254)) for _ in range(4))


def random_log(rng: random.Random) -> str:
    lines = []
    for _ in range(rng.randint(1, 12)):
        user = rng.choice(["root", "admin", "backup", "deploy", rng.choice(WORDS)])
        msg = rng.choice([f"Failed password for {user} from {random_ip(rng)} port {rng.randint(1024, 65535)} ssh2",
                          f"Accepted password for {user} from {random_ip(rng)} port {rng.randint(1024, 65535)} ssh2",
                          f"GET /{rng.choice(WORDS)}?id={rng.randint(1, 999)} HTTP/1.1 {rng.choice([200, 403, 404, 500])}",
                          f"sudo: {user} : TTY=pts/{rng.randint(0, 9)} ; COMMAND=/bin/{rng.choice(['cat', 'ls', 'bash'])}"])
        lines.append(f"Oct {rng.randint(1, 28):2d} {rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:{rng.randint(0, 59):02d} srv {msg}")
    return "\n".join(lines)


def random_html(rng: random.Random) -> str:
    title = " ".join(rng.choice(WORDS) for _ in range(rng.randint(1, 4)))
    comment = f"  <!-- {' '.join(rng.choice(WORDS + ENGLISH) for _ in range(rng.randint(2, 8)))} -->\n" if rng.random() < 0.7 else ""
    return (f"<html>\n<head>\n  <title>{title}</title>\n{comment}</head>\n<body>\n"
            f"  <form action=\"/{rng.choice(WORDS)}\" method=\"post\">\n    <input name=\"user\">\n"
            f"    <button>{rng.choice(WORDS)}</button>\n  </form>\n</body>\n</html>")


def random_sentence(rng: random.Random, vocab: list[str]) -> str:
    sentence = " ".join(rng.choice(vocab) for _ in range(rng.randint(3, 25)))
    return sentence.capitalize() + rng.choice([".", "", "!", "?"])


def random_plaintext(rng: random.Random) -> str:
    kind = rng.random()
    if kind < 0.08:  # textos muy cortos: una a tres palabras
        return " ".join(rng.choice(WORDS + ENGLISH) for _ in range(rng.randint(1, 3)))
    if kind < 0.2:
        return random_flag(rng)
    if kind < 0.3:
        return random_log(rng)
    if kind < 0.38:
        return random_html(rng)
    if kind < 0.48:
        text = random_sentence(rng, ENGLISH + WORDS)
    else:
        text = "\n".join(random_sentence(rng, WORDS) for _ in range(rng.choice([1, 1, 1, 2, 4])))
    if rng.random() < 0.5:
        text += " " + random_flag(rng)
    return text


def make_jwt(rng: random.Random) -> str:
    def b64url(d: bytes) -> str:
        return base64.urlsafe_b64encode(d).rstrip(b"=").decode()
    header = {"alg": rng.choice(["HS256", "HS512", "RS256"]), "typ": "JWT"}
    payload = {"sub": str(rng.randint(1, 99999)), "name": rng.choice(WORDS), "role": rng.choice(["user", "admin"])}
    if rng.random() < 0.5:
        payload["exp"] = rng.randint(1_700_000_000, 1_900_000_000)
    return ".".join([b64url(json.dumps(header, separators=(",", ":")).encode()),
                     b64url(json.dumps(payload, separators=(",", ":")).encode()),
                     b64url(secrets.token_bytes(rng.choice([32, 64])))])


def hex_variant(raw: bytes, rng: random.Random) -> str:
    """Hex en las formas que se ven en la práctica: minúsculas, mayúsculas y con separadores."""
    h = raw.hex()
    if rng.random() < 0.25:
        h = h.upper()
    r = rng.random()
    pairs = [h[i:i + 2] for i in range(0, len(h), 2)]
    if r < 0.12:
        return " ".join(pairs)
    if r < 0.2:
        return ":".join(pairs)
    if r < 0.26:
        return " ".join("0x" + p for p in pairs)
    if r < 0.3:
        return "".join("\\x" + p for p in pairs)
    return h


def b64_variant(raw: bytes, rng: random.Random) -> str:
    r = rng.random()
    if r < 0.15:
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")
    out = base64.b64encode(raw).decode()
    if r < 0.3:
        out = out.rstrip("=")
    if len(out) > 76 and rng.random() < 0.3:  # como en MIME/PEM
        out = "\n".join(out[i:i + 64] for i in range(0, len(out), 64))
    return out


def sample(label: str, rng: random.Random) -> str:
    plain = random_plaintext(rng)
    data = plain.encode()
    if label in ("base64", "base32", "hex", "xor") and rng.random() < 0.3:
        data = apply(rng.choice(["base64", "hex", "rot13", "reverse"]), 0, data)  # una capa interior
    if label == "base64" and rng.random() < 0.1:
        data = secrets.token_bytes(rng.randint(8, 48))  # Base64 de datos binarios (claves, tokens)
    match label:
        case "texto": return plain
        case "base64": return b64_variant(data, rng)
        case "base32":
            out = apply("base32", 0, data).decode()
            return out.rstrip("=") if rng.random() < 0.2 else out
        case "hex": return hex_variant(data, rng)
        case "atbash": return apply("atbash", 0, data).decode()
        case "cesar": return apply("caesar", rng.choice([13, rng.randint(1, 25)]), data).decode()
        case "invertido": return plain[::-1]  # sobre texto, no bytes, por la ñ
        case "xor":
            # Claves pequeñas dan una salida imprimible que se confunde con hex de texto.
            key = rng.choice([rng.randint(1, 31), rng.randint(1, 255)])
            out = apply("xor", key, data).hex()
            return out.upper() if rng.random() < 0.2 else out
        case "md5" | "sha1" | "sha256":
            out = hashlib.new(label, plain.encode()).hexdigest()
            return out.upper() if rng.random() < 0.2 else out
        case "jwt": return make_jwt(rng)
        case "binario":
            sep = rng.choice([" ", " ", ""])
            out = sep.join(f"{b:08b}" for b in plain.encode()[:rng.randint(2, 60)])
            return out[:-rng.randint(1, 3)] if rng.random() < 0.1 else out  # copiado con algún bit de menos
        case "url":
            from urllib.parse import quote
            return quote(plain, safe="" if rng.random() < 0.5 else "/:")
        case "morse":
            words = [w for w in "".join(c if c.isalnum() else " " for c in plain.lower()).split() if w.isascii()][:12]
            return " / ".join(" ".join(MORSE_CODE[c] for c in w if c in MORSE_CODE) for w in words or ["sos"])
    raise ValueError(label)


def build_dataset(rng: random.Random):
    X, y = [], []
    for label in LABELS:
        for _ in range(SAMPLES_PER_CLASS):
            X.append(extract(sample(label, rng)))
            y.append(label)
    return np.array(X), np.array(y)


def style_axes(ax):
    ax.set_facecolor("none")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(STYLES["grid"])
    ax.tick_params(colors=STYLES["muted"], labelsize=9)
    ax.title.set_color(STYLES["text"])
    ax.xaxis.label.set_color(STYLES["muted"])
    ax.yaxis.label.set_color(STYLES["muted"])


def plot_confusion(y_true, y_pred, classes):
    cm = confusion_matrix(y_true, y_pred, labels=classes, normalize="true")
    names = [LABELS[c][0] for c in classes]
    fig, ax = plt.subplots(figsize=(9, 7.5), facecolor="#0d1117")
    style_axes(ax)
    im = ax.imshow(cm, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(names)), names, rotation=45, ha="right")
    ax.set_yticks(range(len(names)), names)
    ax.set_xlabel("Predicción")
    ax.set_ylabel("Clase real")
    ax.set_title("Matriz de confusión (proporción por clase real)", loc="left", fontsize=12, color=STYLES["text"])
    for i in range(len(names)):
        for j in range(len(names)):
            if cm[i, j] >= 0.01:
                ax.text(j, i, f"{cm[i, j]:.2f}", ha="center", va="center", fontsize=8,
                        color="#0b0b0b" if cm[i, j] < 0.6 else "#ffffff")
    cbar = fig.colorbar(im, ax=ax, fraction=0.04)
    cbar.ax.tick_params(colors=STYLES["muted"], labelsize=8)
    cbar.outline.set_visible(False)
    fig.tight_layout()
    fig.savefig(REPORTS / "matriz_confusion.png", dpi=130)
    plt.close(fig)


def plot_importances(model):
    order = np.argsort(model.feature_importances_)
    fig, ax = plt.subplots(figsize=(8, 7), facecolor="#0d1117")
    style_axes(ax)
    ax.barh([FEATURE_NAMES[i] for i in order], model.feature_importances_[order],
            color=STYLES["blue"], height=0.7)
    ax.xaxis.grid(True, color=STYLES["grid"], linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_xlabel("Importancia (reducción media de impureza)")
    ax.set_title("¿En qué se fija el modelo?", loc="left", fontsize=12, color=STYLES["text"])
    fig.tight_layout()
    fig.savefig(REPORTS / "importancia_caracteristicas.png", dpi=130)
    plt.close(fig)


def main():
    rng = random.Random(42)
    print("Generando datos sintéticos...")
    X, y = build_dataset(rng)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=0)

    print(f"Entrenando con {len(X_train)} ejemplos ({len(LABELS)} clases)...")
    model = RandomForestClassifier(n_estimators=150, min_samples_leaf=2, max_depth=24, n_jobs=-1, random_state=0)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred, digits=3))

    # La inferencia del servidor usa FastForest: se comprueba que da exactamente lo mismo que scikit-learn.
    fast = FastForest.from_sklearn(model)
    assert np.allclose(fast.predict_proba(X_test), model.predict_proba(X_test), atol=1e-5), "FastForest no coincide"
    print(f"FastForest verificado: {fast.roots.size} árboles, {fast.feature.size} nodos, profundidad {fast.depth}")

    REPORTS.mkdir(exist_ok=True)
    plot_confusion(y_test, y_pred, list(model.classes_))
    plot_importances(model)
    joblib.dump({"forest": fast.to_dict(), "feature_names": FEATURE_NAMES}, MODEL_PATH, compress=3)
    print(f"Modelo guardado en {MODEL_PATH}\nGráficas en {REPORTS}")


if __name__ == "__main__":
    main()
