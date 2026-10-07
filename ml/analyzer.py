"""Analiza un texto con el modelo entrenado. Sin scikit-learn ni matplotlib en tiempo de ejecución:
el modelo se carga como arrays (FastForest) y la gráfica la dibuja el navegador."""

import string
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from .fastforest import FastForest
from .features import EXPECTED, FEATURE_NAMES, extract, letter_frequencies
from .labels import LABELS

MODEL_PATH = Path(__file__).resolve().parent / "model.joblib"
# Solo en estos casos las letras son "reales" y su frecuencia aporta algo.
LETTER_BASED = {"texto", "cesar", "atbash", "invertido"}
MIN_LETTERS_FOR_CHART = 12  # con menos letras las frecuencias no dicen nada


class ModelMissing(Exception):
    pass


@lru_cache(maxsize=1)
def _model() -> FastForest:
    if not MODEL_PATH.exists():
        raise ModelMissing("El modelo no está entrenado. Ejecuta: python -m ml.train")
    data = joblib.load(MODEL_PATH)
    if "forest" not in data or data.get("feature_names") != FEATURE_NAMES:
        raise ModelMissing("El modelo guardado es de una versión anterior. Vuelve a entrenarlo: python -m ml.train")
    return FastForest.from_dict(data["forest"])


def warmup():
    """Carga el modelo y hace una predicción para que la primera petición real ya vaya rápida."""
    try:
        predict("calentando")
    except ModelMissing:
        pass


def predict(text: str, top: int = 3) -> list[dict]:
    model = _model()
    probs = model.predict_proba(extract(text)[None, :])[0]
    order = np.argsort(probs)[::-1][:top]
    labels = [str(model.classes[i]) for i in order]
    return [{"label": label, "name": LABELS[label][0], "explanation": LABELS[label][1],
             "probability": round(float(probs[i]), 3)} for label, i in zip(labels, order)]


def frequencies(text: str) -> dict | None:
    """Frecuencia (%) de cada letra del texto frente a la habitual en español, para dibujarla en el cliente."""
    if sum(c.isascii() and c.isalpha() for c in text) < MIN_LETTERS_FOR_CHART:
        return None
    freqs = letter_frequencies(text)
    return {"letters": list(string.ascii_lowercase),
            "text": [round(float(f) * 100, 2) for f in freqs],
            "spanish": [round(float(f) * 100, 2) for f in EXPECTED]}


def analyze(text: str) -> dict:
    predictions = predict(text)
    freq = frequencies(text) if predictions[0]["label"] in LETTER_BASED else None
    return {"predictions": predictions, "frequencies": freq}
