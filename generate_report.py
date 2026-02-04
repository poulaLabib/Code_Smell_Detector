"""
Final Report Generator
Produces a clean summary of the entire pipeline.
"""

import json, os
from collections import Counter

BASE = "/home/claude/code_smell_project"

# Load all results
with open(os.path.join(BASE, "models", "baseline_a_results.json")) as f:
    baseline_a = json.load(f)
with open(os.path.join(BASE, "models", "baseline_b_tfidf_results.json")) as f:
    baseline_b = json.load(f)
with open(os.path.join(BASE, "dataset", "split_info.json")) as f:
    splits = json.load(f)
with open(os.path.join(BASE, "gold_set", "ground_truth_meta.json")) as f:
    truth = json.load(f)

smell_counts = Counter(t["true_smell"] for t in truth)

report = []
report.append("=" * 70)
report.append(" CODE SMELL DETECTION — FULL PIPELINE REPORT")
report.append("=" * 70)

report.append("\n📁 PROJECT STRUCTURE")
report.append("-" * 70)
report.append("""
  code_smell_project/
  ├── projects/                  ← 12 Java projects (synthetic)
  ├── ck_metrics/                ← CK metrics per project + combined JSON
  ├── sonar_issues/              ← SonarQube-style detections per project
  ├── dataset/
  │   ├── dataset.csv            ← Full dataset (features + labels, no code)
  │   ├── dataset.json           ← Full dataset (includes raw_code)
  │   └── split_info.json        ← Train/Val/Test project assignments
  ├── gold_set/
  │   ├── ground_truth_meta.json ← True labels for all 191 classes
  │   └── gold_validation.csv    ← 156 stratified gold examples
  ├── models/
  │   ├── baseline_a_results.json
  │   ├── baseline_b_tfidf_results.json
  │   └── baseline_b_codebert.py ← Ready to run on GPU
  ├── clone_projects.sh          ← Run on YOUR machine to get real repos
  ├── generate_synthetic_java.py ← Generated the 191 Java files
  ├── ck_extractor.py            ← CK metrics extractor (pure Python)
  ├── sonar_detector.py          ← SonarQube rule emulator
  ├── build_dataset.py           ← Merges everything into dataset
  ├── baseline_a_rf.py           ← RandomForest on CK metrics
  └── baseline_b_text.py         ← TF-IDF + CodeBERT pipeline
""")

report.append("\n📊 DATASET STATISTICS")
report.append("-" * 70)
report.append("  Total classes analyzed:  191")
report.append("  Projects:                12")
report.append("")
report.append("  Smell distribution (ground truth):")
for smell in ["GodClass", "FeatureEnvy", "LongMethod", "DataClass", "DeadCode", "Clean"]:
    count = smell_counts.get(smell, 0)
    pct = count / 191 * 100
    bar = "█" * int(pct / 2)
    report.append("    {:15s}: {:3d} ({:5.1f}%)  {}".format(smell, count, pct, bar))

report.append("")
report.append("  Project-level split (NO data leakage):")
report.append("    TRAIN  (67%): {} projects → {} examples".format(
    len(splits["train"]), sum(1 for t in truth if t["project"] in splits["train"])))
report.append("    VAL    ( 8%): {} projects → {} examples".format(
    len(splits["val"]), sum(1 for t in truth if t["project"] in splits["val"])))
report.append("    TEST   (25%): {} projects → {} examples".format(
    len(splits["test"]), sum(1 for t in truth if t["project"] in splits["test"])))

report.append("\n  Gold validation set: 156 stratified examples")

report.append("\n📈 BASELINE A — RandomForest on CK Metrics")
report.append("-" * 70)
report.append("  {:20s} {:>8s} {:>8s} {:>8s}".format("Smell", "Prec", "Rec", "F1"))
report.append("  " + "-" * 48)
SMELL_TYPES = ["GodClass", "FeatureEnvy", "LongMethod", "DataClass", "DeadCode"]
for smell in SMELL_TYPES:
    key = smell + "__RandomForest"
    if key in baseline_a["results"]:
        r = baseline_a["results"][key]
        report.append("  {:20s} {:>8.3f} {:>8.3f} {:>8.3f}".format(
            smell, r["precision"], r["recall"], r["f1"]))

report.append("")
report.append("  Top features per smell:")
for smell in SMELL_TYPES:
    if smell in baseline_a["feature_importances"]:
        fi = baseline_a["feature_importances"][smell]
        top = sorted(fi.items(), key=lambda x: -x[1])[:3]
        top_str = ", ".join(["{} ({:.2f})".format(f, v) for f, v in top])
        report.append("    {:15s} → {}".format(smell, top_str))

report.append("\n📈 BASELINE B — TF-IDF Code Text Classifier")
report.append("-" * 70)
report.append("  {:30s} {:>10s} {:>10s}".format("Model", "Macro F1", "Micro F1"))
report.append("  " + "-" * 52)
for model_name, r in baseline_b.items():
    report.append("  {:30s} {:>10.3f} {:>10.3f}".format(
        model_name, r["macro_f1"], r["micro_f1"]))

report.append("")
report.append("  Ablation (LogisticRegression):")
report.append("    Text-only (TF-IDF):      Macro F1 = 1.000")
report.append("    Metrics-only (CK):       Macro F1 = 1.000")
report.append("    Fused (TF-IDF + CK):     Macro F1 = 1.000")
report.append("    → On synthetic data all signals are clean.")
report.append("    → On REAL data, expect Text < Metrics for structural smells,")
report.append("      and Fused > either alone (especially for FeatureEnvy).")

report.append("\n⚠️  WHY PERFECT SCORES? (Important!)")
report.append("-" * 70)
report.append("""  Our synthetic Java files have very distinct patterns by design:
  • GodClass files have 18-30 fields and 14-25 methods
  • LongMethod files have 58-80 lines in one method
  • DataClass files have only getters/setters
  
  This makes them trivially separable. On REAL code:
  • God Classes emerge gradually — boundaries are fuzzy
  • Feature Envy requires understanding call semantics
  • Dead Code needs whole-program analysis
  
  Expected real-world performance:
  • LongMethod:     F1 ~ 0.85-0.95  (mostly LOC-based, straightforward)
  • GodClass:       F1 ~ 0.65-0.80  (structural, metrics help a lot)
  • DataClass:      F1 ~ 0.70-0.85  (ratio-based, works well)
  • DeadCode:       F1 ~ 0.50-0.70  (needs call-graph analysis)
  • FeatureEnvy:    F1 ~ 0.40-0.65  (most semantic, CodeBERT helps most here)
""")

report.append("\n🚀 NEXT STEPS — Running on Real Data")
report.append("-" * 70)
report.append("""
  STEP 1: Clone real projects (on your machine with internet)
          bash clone_projects.sh

  STEP 2: Run CK metrics on real projects
          python ck_extractor.py
          (change BASE path to point to your real projects/)

  STEP 3: Run SonarQube (REAL Docker version) for production labels
          docker run -d --name sonarqube -p 9000:9000 sonarqube:lts
          # wait ~2 min, then run sonar-scanner on each project
          # OR keep using sonar_detector.py as a fast approximation

  STEP 4: Build dataset
          python build_dataset.py
          (manually label 200-500 examples for gold set — 
           replace ground_truth_meta.json with your human labels)

  STEP 5: Train baselines
          python baseline_a_rf.py      ← works anywhere
          python baseline_b_text.py    ← TF-IDF version, works anywhere

  STEP 6: Fine-tune CodeBERT (needs GPU)
          pip install transformers torch accelerate
          python baseline_b_codebert.py
          
  STEP 7: Iterate
          • If GodClass F1 < 0.7 → add more training projects
          • If FeatureEnvy F1 < 0.5 → CodeBERT + feature fusion is key
          • If DeadCode F1 is low → consider adding call-graph features
          • Active learning: take uncertain predictions, manually label, retrain
""")

report.append("\n💡 KEY RECOMMENDATIONS")
report.append("-" * 70)
report.append("""  1. Use MAJORITY VOTE labels (≥2 tools agree) not OR — higher precision
  2. Always evaluate on human-labeled gold set, never trust tool-only metrics
  3. Different smells need different strategies:
     • Structural (GodClass, LongMethod) → CK metrics dominate
     • Semantic (FeatureEnvy) → CodeBERT embeddings are essential
     • Behavioral (DeadCode) → needs call-graph or whole-program analysis
  4. Project-level splits are NON-NEGOTIABLE — file-level splits will lie to you
  5. Report per-smell F1 — macro averages hide failures on rare smells
""")

report.append("=" * 70)
report.append(" END OF REPORT")
report.append("=" * 70)

full_report = "\n".join(report)
print(full_report)

# Save report
with open(os.path.join(BASE, "REPORT.txt"), "w") as f:
    f.write(full_report)
print("\n✓ Report saved to REPORT.txt")
