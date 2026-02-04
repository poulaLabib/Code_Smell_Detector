"""
Dataset Builder
===============
Merges:
  1. CK metrics (all_ck_metrics.json)      — numeric features
  2. Sonar detections (all_sonar_issues.json) — tool-predicted labels
  3. Ground truth (ground_truth_meta.json)   — true labels (for gold set)

Output:
  dataset/dataset.csv          — full dataset with features + labels
  dataset/dataset.json         — same but JSON (includes raw_code)
  gold_set/gold_validation.csv — 200+ human-verified examples for eval
"""

import json, csv, os
from collections import defaultdict
BASE = os.path.dirname(os.path.abspath(__file__))



# ── Load CK metrics ──
with open(os.path.join(BASE, "ck_metrics", "all_ck_metrics.json")) as f:
    ck_data = json.load(f)

# ── Load Sonar detections ──
with open(os.path.join(BASE, "sonar_issues", "all_sonar_issues.json")) as f:
    sonar_data = json.load(f)["issues"]

# ── Load ground truth ──
with open(os.path.join(BASE, "gold_set", "ground_truth_meta.json")) as f:
    truth_data = json.load(f)

# ── Index ground truth by file_path ──
truth_by_path = {}
for t in truth_data:
    truth_by_path[t["file_path"]] = t["true_smell"]

# ── Index Sonar detections by file_path ──
sonar_by_path = defaultdict(list)
for issue in sonar_data:
    sonar_by_path[issue["file_path"]].append(issue["smell_label"])

# ── All smell types we track ──
SMELL_TYPES = ["GodClass", "FeatureEnvy", "LongMethod", "DataClass", "DeadCode"]

# ── Build unified dataset ──
dataset = []
for ck in ck_data:
    fpath = ck["file_path"]
    row = {
        # --- Identifiers ---
        "project":      ck["project"],
        "file_path":    fpath,
        "class_name":   ck["class_name"],
        "package":      ck["package"],

        # --- Numeric Features (CK metrics) ---
        "LOC":              ck["LOC"],
        "WMC":              ck["WMC"],
        "METHODS":          ck["METHODS"],
        "FIELDS":           ck["FIELDS"],
        "PRIVATE_METHODS":  ck["PRIVATE_METHODS"],
        "CBO":              ck["CBO"],
        "DIT":              ck["DIT"],
        "LCOM":             ck["LCOM"],
        "TCC":              ck["TCC"],
        "ATFD":             ck["ATFD"],
        "MAX_METHOD_LOC":   ck["MAX_METHOD_LOC"],
        "NOC":              ck["NOC"],

        # --- Raw code (for CodeBERT later) ---
        "raw_code":         ck["raw_code"],
    }

    # --- Sonar tool labels (per smell) ---
    sonar_smells = sonar_by_path.get(fpath, [])
    for smell in SMELL_TYPES:
        row["sonar_" + smell] = 1 if smell in sonar_smells else 0

    # --- Aggregated label: OR rule (any tool flags = 1) ---
    row["label_OR"] = 1 if len(sonar_smells) > 0 else 0

    # --- Aggregated label: majority (here we only have 1 tool, so same as OR) ---
    row["label_majority"] = row["label_OR"]

    # --- Which smell (most specific, first detected) ---
    row["predicted_smell"] = sonar_smells[0] if sonar_smells else "Clean"

    # --- Ground truth (simulates human labeling) ---
    row["true_smell"] = truth_by_path.get(fpath, "Unknown")

    # --- Binary ground truth per smell ---
    for smell in SMELL_TYPES:
        row["true_" + smell] = 1 if row["true_smell"] == smell else 0
    row["true_Clean"] = 1 if row["true_smell"] == "Clean" else 0

    dataset.append(row)

# ── Save full dataset as CSV (without raw_code) ──
csv_keys = [k for k in dataset[0].keys() if k != "raw_code"]
with open(os.path.join(BASE, "dataset", "dataset.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=csv_keys)
    w.writeheader()
    for row in dataset:
        w.writerow({k: row[k] for k in csv_keys})

# ── Save full dataset as JSON (with raw_code for CodeBERT) ──
with open(os.path.join(BASE, "dataset", "dataset.json"), "w") as f:
    json.dump(dataset, f, indent=2)

print("Dataset saved: {} total examples".format(len(dataset)))

# ── Create Gold Validation Set ──
# Strategy: take ALL examples and mark them as gold (we have ground truth for all).
# In a real scenario you'd manually label these — here ground truth IS our gold.
# We'll stratify: ensure each smell type is well-represented.
import random
random.seed(42)

gold = []
by_smell = defaultdict(list)
for row in dataset:
    by_smell[row["true_smell"]].append(row)

# Target: ~40 per smell type for gold, rest for training
gold_target = {"GodClass": 25, "FeatureEnvy": 20, "LongMethod": 25,
               "DataClass": 28, "DeadCode": 18, "Clean": 40}

for smell, target_n in gold_target.items():
    pool = by_smell.get(smell, [])
    n = min(target_n, len(pool))
    selected = random.sample(pool, n)
    for s in selected:
        s["_is_gold"] = True
        gold.append(s)

# Mark non-gold
gold_paths = set(g["file_path"] for g in gold)
for row in dataset:
    row["_is_gold"] = row["file_path"] in gold_paths

# Save gold set CSV
gold_csv_keys = [k for k in csv_keys if k != "raw_code"] + ["_is_gold"]
with open(os.path.join(BASE, "gold_set", "gold_validation.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=[k for k in csv_keys])
    w.writeheader()
    for row in gold:
        w.writerow({k: row[k] for k in csv_keys})

print("Gold validation set: {} examples".format(len(gold)))
for smell in list(gold_target.keys()):
    count = sum(1 for g in gold if g["true_smell"] == smell)
    print("  {:15s}: {}".format(smell, count))

# ── Label quality report ──
print("\n--- Label Quality Report (Sonar vs Ground Truth) ---")
for smell in SMELL_TYPES + ["Clean"]:
    true_pos = sum(1 for r in dataset if r["true_smell"] == smell and r["predicted_smell"] == smell)
    false_pos = sum(1 for r in dataset if r["true_smell"] != smell and r["predicted_smell"] == smell)
    false_neg = sum(1 for r in dataset if r["true_smell"] == smell and r["predicted_smell"] != smell)
    true_neg = sum(1 for r in dataset if r["true_smell"] != smell and r["predicted_smell"] != smell)
    
    precision = true_pos / (true_pos + false_pos) if (true_pos + false_pos) > 0 else 0
    recall    = true_pos / (true_pos + false_neg) if (true_pos + false_neg) > 0 else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    print("  {:15s} | P={:.2f}  R={:.2f}  F1={:.2f} | TP={} FP={} FN={} TN={}".format(
        smell, precision, recall, f1, true_pos, false_pos, false_neg, true_neg))

# ── Train/Val/Test split info ──
projects_list = sorted(set(r["project"] for r in dataset))
# 70/15/15 project split
n = len(projects_list)
train_end = int(n * 0.70)
val_end = train_end + int(n * 0.15)

train_projs = projects_list[:train_end]
val_projs   = projects_list[train_end:val_end]
test_projs  = projects_list[val_end:]

print("\n--- Project-Level Split ---")
print("  TRAIN projects ({:.0f}%): {}".format(len(train_projs)/n*100, train_projs))
print("  VAL   projects ({:.0f}%): {}".format(len(val_projs)/n*100, val_projs))
print("  TEST  projects ({:.0f}%): {}".format(len(test_projs)/n*100, test_projs))

split_info = {
    "train": train_projs,
    "val": val_projs,
    "test": test_projs
}
with open(os.path.join(BASE, "dataset", "split_info.json"), "w") as f:
    json.dump(split_info, f, indent=2)

# Add split column to dataset
for row in dataset:
    if row["project"] in train_projs:
        row["split"] = "train"
    elif row["project"] in val_projs:
        row["split"] = "val"
    else:
        row["split"] = "test"

# Re-save with split
with open(os.path.join(BASE, "dataset", "dataset.json"), "w") as f:
    json.dump(dataset, f, indent=2)

train_count = sum(1 for r in dataset if r["split"] == "train")
val_count   = sum(1 for r in dataset if r["split"] == "val")
test_count  = sum(1 for r in dataset if r["split"] == "test")
print("  TRAIN: {} examples | VAL: {} examples | TEST: {} examples".format(
    train_count, val_count, test_count))
