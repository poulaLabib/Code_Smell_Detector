"""
Baseline A — RandomForest on CK Metrics
=========================================
Trains one RandomForest per smell type (one-vs-all).
Evaluates on gold validation set.
Reports: per-smell Precision / Recall / F1 + macro F1.
Saves: model artifacts + feature importance report.
"""

import json, os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)
import warnings
warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.abspath(__file__))

# ── Load dataset ──
with open(os.path.join(BASE, "dataset", "dataset.json")) as f:
    dataset = json.load(f)

df = pd.DataFrame(dataset)

# ── Define features and smell targets ──
FEATURE_COLS = [
    "LOC", "WMC", "METHODS", "FIELDS", "PRIVATE_METHODS",
    "CBO", "DIT", "LCOM", "TCC", "ATFD", "MAX_METHOD_LOC", "NOC"
]

SMELL_TYPES = ["GodClass", "FeatureEnvy", "LongMethod", "DataClass", "DeadCode"]

# ── Project-level split ──
with open(os.path.join(BASE, "dataset", "split_info.json")) as f:
    splits = json.load(f)

train_df = df[df["project"].isin(splits["train"])]
val_df   = df[df["project"].isin(splits["val"])]
test_df  = df[df["project"].isin(splits["test"])]

print("=" * 65)
print(" BASELINE A — RandomForest on CK Metrics")
print("=" * 65)
print("Train: {} | Val: {} | Test: {}".format(len(train_df), len(val_df), len(test_df)))
print()

# ── Train & Evaluate ──
X_train = train_df[FEATURE_COLS].values
X_test  = test_df[FEATURE_COLS].values

results = {}
feature_importances = {}

for smell in SMELL_TYPES:
    target_col = "true_" + smell
    y_train = train_df[target_col].values
    y_test  = test_df[target_col].values

    # Skip if no positives in train or test
    if y_train.sum() == 0 or y_test.sum() == 0:
        print("  [SKIP] {} — no positives in train or test".format(smell))
        continue

    # Train RandomForest with class balancing
    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        class_weight="balanced",
        random_state=42,
        min_samples_leaf=2
    )
    clf.fit(X_train, y_train)

    # Also train XGBoost-style (GradientBoosting) for comparison
    gbc = GradientBoostingClassifier(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.1,
        random_state=42
    )
    gbc.fit(X_train, y_train)

    # Predict
    y_pred_rf  = clf.predict(X_test)
    y_pred_gbc = gbc.predict(X_test)

    # Metrics
    for name, y_pred, model in [("RandomForest", y_pred_rf, clf), ("GradientBoosting", y_pred_gbc, gbc)]:
        p = precision_score(y_test, y_pred, zero_division=0)
        r = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)

        key = "{}__{}".format(smell, name)
        results[key] = {"precision": p, "recall": r, "f1": f1,
                        "support_pos": int(y_test.sum()), "support_neg": int((1-y_test).sum())}

    # Feature importances (RF)
    feature_importances[smell] = {
        FEATURE_COLS[i]: round(float(clf.feature_importances_[i]), 4)
        for i in range(len(FEATURE_COLS))
    }

# ── Print results ──
print("{:<20s} {:<18s} {:>8s} {:>8s} {:>8s}".format("Smell", "Model", "Prec", "Rec", "F1"))
print("-" * 65)

rf_f1s = []
gbc_f1s = []

for smell in SMELL_TYPES:
    for model_name in ["RandomForest", "GradientBoosting"]:
        key = "{}__{}".format(smell, model_name)
        if key in results:
            r = results[key]
            print("{:<20s} {:<18s} {:>8.3f} {:>8.3f} {:>8.3f}  (pos={})".format(
                smell, model_name, r["precision"], r["recall"], r["f1"], r["support_pos"]))
            if model_name == "RandomForest":
                rf_f1s.append(r["f1"])
            else:
                gbc_f1s.append(r["f1"])

print("-" * 65)
if rf_f1s:
    print("{:<20s} {:<18s} {:>8s} {:>8s} {:>8.3f}".format(
        "MACRO AVG", "RandomForest", "", "", np.mean(rf_f1s)))
if gbc_f1s:
    print("{:<20s} {:<18s} {:>8s} {:>8s} {:>8.3f}".format(
        "MACRO AVG", "GradientBoosting", "", "", np.mean(gbc_f1s)))

# ── Print feature importances ──
print("\n" + "=" * 65)
print(" Feature Importances (RandomForest)")
print("=" * 65)
for smell in SMELL_TYPES:
    if smell in feature_importances:
        print("\n  {}:".format(smell))
        sorted_fi = sorted(feature_importances[smell].items(), key=lambda x: -x[1])
        for feat, imp in sorted_fi[:5]:  # top 5
            bar = "█" * int(imp * 100)
            print("    {:20s} {:.4f}  {}".format(feat, imp, bar))

# ── Save results ──
with open(os.path.join(BASE, "models", "baseline_a_results.json"), "w") as f:
    json.dump({"results": results, "feature_importances": feature_importances}, f, indent=2)

print("\n✓ Results saved to models/baseline_a_results.json")

# ── Multi-class version: predict the SMELL TYPE directly ──
print("\n" + "=" * 65)
print(" MULTI-CLASS MODEL: Predict smell type directly")
print("=" * 65)

# Labels: GodClass, FeatureEnvy, LongMethod, DataClass, DeadCode, Clean
y_train_mc = train_df["true_smell"].values
y_test_mc  = test_df["true_smell"].values

clf_mc = RandomForestClassifier(
    n_estimators=300,
    max_depth=12,
    class_weight="balanced",
    random_state=42,
    min_samples_leaf=1
)
clf_mc.fit(X_train, y_train_mc)
y_pred_mc = clf_mc.predict(X_test)

print("\nClassification Report:")
print(classification_report(y_test_mc, y_pred_mc))

macro_f1 = f1_score(y_test_mc, y_pred_mc, average="macro", zero_division=0)
micro_f1 = f1_score(y_test_mc, y_pred_mc, average="micro", zero_division=0)
print("Macro F1: {:.3f}  |  Micro F1: {:.3f}".format(macro_f1, micro_f1))

# Confusion matrix
labels = sorted(set(y_test_mc))
cm = confusion_matrix(y_test_mc, y_pred_mc, labels=labels)
print("\nConfusion Matrix (rows=true, cols=predicted):")
print("{:>15s}".format("") + "".join(["{:>14s}".format(l) for l in labels]))
for i, label in enumerate(labels):
    print("{:>15s}".format(label) + "".join(["{:>14d}".format(cm[i][j]) for j in range(len(labels))]))

# Per-project performance
print("\n--- Per-Project Performance (Test Set) ---")
for proj in splits["test"]:
    proj_mask = test_df["project"] == proj
    if proj_mask.sum() == 0:
        continue
    X_proj = test_df.loc[proj_mask, FEATURE_COLS].values
    y_proj = test_df.loc[proj_mask, "true_smell"].values
    y_pred_proj = clf_mc.predict(X_proj)
    acc = (y_pred_proj == y_proj).mean()
    f1_p = f1_score(y_proj, y_pred_proj, average="macro", zero_division=0)
    print("  {:<20s}: Acc={:.2f}  MacroF1={:.2f}  (n={})".format(proj, acc, f1_p, len(y_proj)))

print("\n✓ Baseline A complete.")
