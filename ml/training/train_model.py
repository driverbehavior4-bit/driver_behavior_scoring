"""
ml/training/train_model.py
Pure Python/NumPy Decision Tree Classifier.
sklearn C-extensions are blocked on this machine; everything uses only numpy.
"""
import os, sys, json
import numpy as np
from datetime import datetime

_HERE        = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.preprocessing.pipeline import load_processed, prepare_training_data, FEATURE_COLS

MODELS_DIR    = os.path.join(PROJECT_ROOT, "ml", "models")
MODEL_PATH    = os.path.join(MODELS_DIR, "best_model.joblib")
META_PATH     = os.path.join(MODELS_DIR, "model_metadata.json")
PROCESSED_CSV = os.path.join(PROJECT_ROOT, "data", "processed", "processed_data.csv")

SCORING_FORMULA = (
    "speed_score=clip(100-(max_speed-80)*2,0,100); "
    "braking_score=clip(100-harsh_braking*10,0,100); "
    "acceleration_score=clip(100-harsh_acceleration*10,0,100); "
    "trip_safety_score=speed*0.4+braking*0.3+accel*0.3; "
    "risk_label: >=70->0(Low), >=40->1(Moderate), else->2(High)"
)
RISK_CATS = {0: "Low Risk", 1: "Moderate Risk", 2: "High Risk"}


# ── Pure-NumPy Decision Tree ─────────────────────────────────────────────────

class _Node:
    __slots__ = ["feature","threshold","left","right","label"]
    def __init__(self):
        self.feature = self.threshold = self.left = self.right = self.label = None


class DecisionTreeNP:
    def __init__(self, max_depth=8, min_samples_split=5, random_state=42):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.random_state = random_state
        self.root_ = self.classes_ = self.n_features_ = None
        self.feature_importances_ = None

    @staticmethod
    def _gini(y):
        if len(y) == 0: return 0.0
        _, c = np.unique(y, return_counts=True)
        p = c / len(y)
        return float(1.0 - (p**2).sum())

    def _best_split(self, X, y):
        n, nf = X.shape
        bg, bf, bt = float("inf"), None, None
        for fi in range(nf):
            col = X[:, fi]
            thresholds = np.unique(col)
            if len(thresholds) > 20:
                thresholds = np.percentile(col, np.linspace(5, 95, 20))
            for thr in thresholds:
                lm = col <= thr
                nl, nr = lm.sum(), (~lm).sum()
                if nl == 0 or nr == 0: continue
                g = (nl/n)*self._gini(y[lm]) + (nr/n)*self._gini(y[~lm])
                if g < bg:
                    bg, bf, bt = g, fi, thr
        return bf, bt

    def _build(self, X, y, depth):
        node = _Node()
        nc = len(self.classes_)
        if depth >= self.max_depth or len(y) < self.min_samples_split or len(np.unique(y)) == 1:
            node.label = int(np.bincount(y, minlength=nc).argmax())
            return node
        fi, thr = self._best_split(X, y)
        if fi is None:
            node.label = int(np.bincount(y, minlength=nc).argmax())
            return node
        node.feature, node.threshold = fi, thr
        lm = X[:, fi] <= thr
        node.left  = self._build(X[lm],  y[lm],  depth+1)
        node.right = self._build(X[~lm], y[~lm], depth+1)
        return node

    def fit(self, X, y):
        np.random.seed(self.random_state)
        self.classes_    = np.unique(y)
        self.n_features_ = X.shape[1]
        self.root_       = self._build(np.array(X, dtype=float), np.array(y, dtype=int), 0)
        counts = np.zeros(self.n_features_)
        def _visit(nd):
            if nd is None or nd.label is not None: return
            counts[nd.feature] += 1
            _visit(nd.left); _visit(nd.right)
        _visit(self.root_)
        t = counts.sum()
        self.feature_importances_ = (counts/t).tolist() if t > 0 else counts.tolist()
        return self

    def _pred1(self, nd, x):
        while nd.label is None:
            nd = nd.left if x[nd.feature] <= nd.threshold else nd.right
        return nd.label

    def predict(self, X):
        return np.array([self._pred1(self.root_, r) for r in np.array(X, dtype=float)])


# ── Metrics ──────────────────────────────────────────────────────────────────

def _cm(yt, yp, nc=3):
    cm = np.zeros((nc, nc), dtype=int)
    for t, p in zip(yt, yp): cm[t][p] += 1
    return cm


def evaluate(model, X, y):
    yp = model.predict(X)
    acc = float(np.mean(yp == y))
    cm  = _cm(y.tolist(), yp.tolist())
    nc  = cm.shape[0]
    prec, rec, f1, sup = [], [], [], []
    for c in range(nc):
        tp = cm[c,c]; fp = cm[:,c].sum()-tp; fn = cm[c,:].sum()-tp
        p = tp/(tp+fp) if tp+fp else 0.0
        r = tp/(tp+fn) if tp+fn else 0.0
        f = 2*p*r/(p+r) if p+r else 0.0
        prec.append(p); rec.append(r); f1.append(f); sup.append(int(cm[c,:].sum()))
    tot = sum(sup)
    wp = sum(p*s for p,s in zip(prec,sup))/tot
    wr = sum(r*s for r,s in zip(rec,sup))/tot
    wf = sum(f*s for f,s in zip(f1,sup))/tot
    return {"accuracy":round(acc,4),"precision":round(wp,4),"recall":round(wr,4),
            "f1":round(wf,4),"confusion_matrix":cm.tolist()}


# ── Train ─────────────────────────────────────────────────────────────────────

def stratified_split(X, y, test_size=0.2, seed=42):
    np.random.seed(seed)
    tr, te = [], []
    for c in np.unique(y):
        idx = np.where(y==c)[0]; np.random.shuffle(idx)
        split = max(1, int(len(idx)*(1-test_size)))
        tr.extend(idx[:split].tolist()); te.extend(idx[split:].tolist())
    np.random.shuffle(tr); np.random.shuffle(te)
    return X[tr], X[te], y[tr], y[te]


def train_and_select(csv_path=PROCESSED_CSV):
    df = load_processed(csv_path)
    X, y, feat = prepare_training_data(df)
    Xtr, Xte, ytr, yte = stratified_split(X, y)
    print(f"\nTrain: {len(Xtr)}  Test: {len(Xte)}")

    best_f1 = -1; best_model = None; best_depth = 8; best_metrics = {}
    for depth in [5, 8, 12]:
        print(f"\n--- DecisionTreeNP(max_depth={depth}) ---")
        m = DecisionTreeNP(max_depth=depth, min_samples_split=5, random_state=42)
        m.fit(Xtr, ytr)
        met = evaluate(m, Xte, yte)
        print(f"  Accuracy : {met['accuracy']}")
        print(f"  Precision: {met['precision']}")
        print(f"  Recall   : {met['recall']}")
        print(f"  F1       : {met['f1']}")
        print(f"  Confusion Matrix:")
        for row in met["confusion_matrix"]: print(f"    {row}")
        if met["f1"] > best_f1:
            best_f1, best_model, best_depth, best_metrics = met["f1"], m, depth, met

    name = f"DecisionTreeNP(max_depth={best_depth})"
    print(f"\n{'='*50}\nBest model: {name}  (F1={best_f1:.4f})\n{'='*50}")
    return name, best_model, best_metrics, list(feat)


def save_artifacts(name, model, metrics, feat):
    import joblib
    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"[save] Model -> {MODEL_PATH}")
    meta = {
        "model_name": name, "accuracy": metrics["accuracy"],
        "precision": metrics["precision"], "recall": metrics["recall"],
        "f1": metrics["f1"], "confusion_matrix": metrics["confusion_matrix"],
        "feature_names": feat, "classes": [0,1,2],
        "class_labels": ["Low Risk","Moderate Risk","High Risk"],
        "training_date": datetime.utcnow().isoformat()+"Z",
        "scoring_formula": SCORING_FORMULA,
        "note": "Pure-Python/NumPy Decision Tree (sklearn DLLs blocked by AppControl policy)",
    }
    with open(META_PATH, "w") as f: json.dump(meta, f, indent=2)
    print(f"[save] Metadata -> {META_PATH}")
    return meta


# ── Scoring helpers ───────────────────────────────────────────────────────────

def calculate_trip_score(max_speed, harsh_braking, harsh_acceleration):
    speed_score = float(np.clip(100-(max_speed-80)*2, 0, 100))
    braking_score = float(np.clip(100-harsh_braking*10, 0, 100))
    accel_score = float(np.clip(100-harsh_acceleration*10, 0, 100))
    score = round(speed_score*0.4 + braking_score*0.3 + accel_score*0.3, 2)
    return score, speed_score, braking_score, accel_score


def predict_trip_risk(features_dict: dict) -> dict:
    import joblib
    ms  = features_dict.get("max_speed", 80)
    hb  = features_dict.get("harsh_braking", 0)
    ha  = features_dict.get("harsh_acceleration", 0)
    score, ss, bs, as_ = calculate_trip_score(ms, hb, ha)

    risk_label = 0 if score >= 70 else (1 if score >= 40 else 2)
    ml_label   = risk_label
    if os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            row = np.array([[features_dict.get(c,0) for c in FEATURE_COLS]], dtype=float)
            ml_label = int(model.predict(row)[0])
        except Exception:
            pass

    factors = []
    if ms > 100: factors.append(f"Excessive speed (max {ms:.0f} km/h)")
    if hb >= 4:  factors.append(f"Frequent harsh braking ({hb} events)")
    if ha >= 4:  factors.append(f"Frequent harsh acceleration ({ha} events)")
    if not factors: factors.append("No major risk factors")

    return {"risk_label": risk_label, "risk_category": RISK_CATS[risk_label],
            "trip_safety_score": score, "speed_score": round(ss,2),
            "braking_score": round(bs,2), "acceleration_score": round(as_,2),
            "contributing_factors": factors, "ml_label": ml_label}


if __name__ == "__main__":
    name, model, metrics, feat = train_and_select()
    save_artifacts(name, model, metrics, feat)
    print("\n--- Smoke test ---")
    sample = {"average_speed":90,"max_speed":115,"harsh_braking":6,
              "harsh_acceleration":5,"trip_duration":30,"speed_difference":25,
              "total_harsh_events":11,"harsh_events_per_minute":0.367,
              "speed_risk":1,"braking_risk":1,"acceleration_risk":1}
    import json
    print(json.dumps(predict_trip_risk(sample), indent=2))
