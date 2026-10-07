"""Inferencia rápida de un RandomForest de scikit-learn con numpy puro.

scikit-learn recorre los árboles uno a uno (con sobrecoste de Python por árbol y, con n_jobs, de hilos).
Aquí todos los árboles se aplanan en unos pocos arrays y se recorren a la vez, nivel a nivel: para una
muestra son ~profundidad operaciones vectorizadas en lugar de cientos de llamadas.
"""

import numpy as np


class FastForest:
    def __init__(self, feature, threshold, left, right, value, roots, depth, classes):
        self.feature = feature
        self.threshold = threshold
        self.left = left
        self.right = right
        self.value = value
        self.roots = roots
        self.depth = int(depth)
        self.classes = np.asarray(classes)

    @classmethod
    def from_sklearn(cls, forest) -> "FastForest":
        feats, thrs, lefts, rights, values, roots = [], [], [], [], [], []
        offset = 0
        for est in forest.estimators_:
            t = est.tree_
            idx = np.arange(t.node_count)
            leaf = t.children_left == -1
            roots.append(offset)
            feats.append(np.where(leaf, 0, t.feature).astype(np.int16))
            thrs.append(t.threshold.astype(np.float64))
            # Las hojas apuntan a sí mismas: así todos los árboles pueden recorrerse el mismo número de pasos.
            lefts.append((np.where(leaf, idx, t.children_left) + offset).astype(np.int32))
            rights.append((np.where(leaf, idx, t.children_right) + offset).astype(np.int32))
            v = t.value[:, 0, :]
            values.append((v / v.sum(axis=1, keepdims=True)).astype(np.float32))
            offset += t.node_count
        return cls(np.concatenate(feats), np.concatenate(thrs), np.concatenate(lefts), np.concatenate(rights),
                   np.concatenate(values), np.array(roots, dtype=np.int32),
                   max(e.tree_.max_depth for e in forest.estimators_), forest.classes_)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float32)  # sklearn compara en float32 contra umbrales float64
        rows = np.arange(X.shape[0])[:, None]
        node = np.broadcast_to(self.roots, (X.shape[0], self.roots.size)).copy()
        for _ in range(self.depth):
            go_left = X[rows, self.feature[node]] <= self.threshold[node]
            node = np.where(go_left, self.left[node], self.right[node])
        return self.value[node].mean(axis=1)

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in ("feature", "threshold", "left", "right", "value", "roots", "depth", "classes")}

    @classmethod
    def from_dict(cls, d: dict) -> "FastForest":
        return cls(**d)
