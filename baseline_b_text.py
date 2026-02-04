"""
Baseline B — Code Text Classifier
====================================
Two modes:
  (1) TF-IDF mode  — runs here, no GPU needed. Uses TF-IDF on Java source.
  (2) CodeBERT mode — run on your own machine with GPU. Fine-tunes microsoft/codebert-base.

Both share the same evaluation pipeline so results are directly comparable.

Usage:
  python baseline_b_text.py          # runs TF-IDF mode
  python baseline_b_text.py --codebert  # runs CodeBERT mode (needs GPU + transformers)
"""

import json, os, sys
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import classification_report, f1_score, confusion_matrix
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings("ignore")

BASE = "/home/claude/code_smell_project"

# ── Load dataset ──
with open(os.path.join(BASE, "dataset", "dataset.json")) as f:
    dataset = json.load(f)

df = pd.DataFrame(dataset)

with open(os.path.join(BASE, "dataset", "split_info.json")) as f:
    splits = json.load(f)

train_df = df[df["project"].isin(splits["train"])]
test_df  = df[df["project"].isin(splits["test"])]

FEATURE_COLS = [
    "LOC", "WMC", "METHODS", "FIELDS", "PRIVATE_METHODS",
    "CBO", "DIT", "LCOM", "TCC", "ATFD", "MAX_METHOD_LOC", "NOC"
]


# ══════════════════════════════════════════════════════════════
#  MODE 1: TF-IDF + Classifiers (runs anywhere)
# ══════════════════════════════════════════════════════════════

def run_tfidf_mode():
    print("=" * 65)
    print(" BASELINE B — TF-IDF Code Text Classifier")
    print("=" * 65)

    # ── TF-IDF on raw Java code ──
    print("\n[1/4] Fitting TF-IDF vectorizer on code text...")
    tfidf = TfidfVectorizer(
        max_features=5000,
        analyzer="word",
        token_pattern=r"(?u)\b\w+\b",  # includes single-char tokens
        ngram_range=(1, 2),            # unigrams + bigrams
        sublinear_tf=True,             # apply sublinear TF scaling
        min_df=2,
        max_df=0.95,
    )

    X_train_text = tfidf.fit_transform(train_df["raw_code"].values)
    X_test_text  = tfidf.transform(test_df["raw_code"].values)

    print("  TF-IDF shape: train={}, test={}".format(X_train_text.shape, X_test_text.shape))

    # ── Also get numeric metrics ──
    from scipy.sparse import hstack, csr_matrix
    X_train_metrics = csr_matrix(train_df[FEATURE_COLS].values.astype(float))
    X_test_metrics  = csr_matrix(test_df[FEATURE_COLS].values.astype(float))

    # ── Fused features: TF-IDF + metrics ──
    X_train_fused = hstack([X_train_text, X_train_metrics])
    X_test_fused  = hstack([X_test_text, X_test_metrics])
    print("  Fused shape: train={}, test={}".format(X_train_fused.shape, X_test_fused.shape))

    y_train = train_df["true_smell"].values
    y_test  = test_df["true_smell"].values

    # ── Train 3 models ──
    print("\n[2/4] Training classifiers...")

    models = {
        "LogisticRegression": LogisticRegression(
            max_iter=1000, class_weight="balanced", C=1.0, random_state=42
        ),
        "RandomForest_TextFused": RandomForestClassifier(
            n_estimators=300, max_depth=15, class_weight="balanced",
            random_state=42, min_samples_leaf=1
        ),
        "MLP_TextFused": MLPClassifier(
            hidden_layer_sizes=(256, 128),
            max_iter=500,
            random_state=42,
            early_stopping=False,
            learning_rate="adaptive",
        ),
    }

    # Which features each model uses (MLP needs dense arrays)
    model_features = {
        "LogisticRegression":        X_train_fused,
        "RandomForest_TextFused":    X_train_fused,
        "MLP_TextFused":             X_train_fused.toarray(),
    }
    model_test_features = {
        "LogisticRegression":        X_test_fused,
        "RandomForest_TextFused":    X_test_fused,
        "MLP_TextFused":             X_test_fused.toarray(),
    }

    results = {}
    for name, model in models.items():
        print("  Training {}...".format(name))
        model.fit(model_features[name], y_train)
        y_pred = model.predict(model_test_features[name])

        macro_f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
        micro_f1 = f1_score(y_test, y_pred, average="micro", zero_division=0)
        results[name] = {"macro_f1": macro_f1, "micro_f1": micro_f1}
        print("    Macro F1: {:.3f}  |  Micro F1: {:.3f}".format(macro_f1, micro_f1))

    # ── Detailed report for best model ──
    best_model_name = max(results, key=lambda k: results[k]["macro_f1"])
    print("\n[3/4] Detailed report for best model: {}".format(best_model_name))

    best_model = models[best_model_name]
    y_pred_best = best_model.predict(model_test_features[best_model_name])

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred_best))

    # Confusion matrix
    labels = sorted(set(y_test))
    cm = confusion_matrix(y_test, y_pred_best, labels=labels)
    print("Confusion Matrix:")
    print("{:>15s}".format("") + "".join(["{:>14s}".format(l) for l in labels]))
    for i, label in enumerate(labels):
        print("{:>15s}".format(label) + "".join(["{:>14d}".format(cm[i][j]) for j in range(len(labels))]))

    # Per-project
    print("\n[4/4] Per-Project Performance:")
    for proj in splits["test"]:
        mask = test_df["project"] == proj
        if mask.sum() == 0:
            continue
        X_proj = model_test_features[best_model_name][mask.values]
        y_proj = test_df.loc[mask, "true_smell"].values
        y_pred_proj = best_model.predict(X_proj)
        acc = (y_pred_proj == y_proj).mean()
        f1_p = f1_score(y_proj, y_pred_proj, average="macro", zero_division=0)
        print("  {:<20s}: Acc={:.2f}  MacroF1={:.2f}  (n={})".format(proj, acc, f1_p, mask.sum()))

    # ── Comparison: text-only vs metrics-only vs fused ──
    print("\n" + "=" * 65)
    print(" ABLATION: Text-only vs Metrics-only vs Fused")
    print("=" * 65)

    # Text only
    lr_text = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    lr_text.fit(X_train_text, y_train)
    f1_text = f1_score(y_test, lr_text.predict(X_test_text), average="macro", zero_division=0)

    # Metrics only
    lr_metrics = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    lr_metrics.fit(X_train_metrics, y_train)
    f1_metrics = f1_score(y_test, lr_metrics.predict(X_test_metrics), average="macro", zero_division=0)

    # Fused
    f1_fused = results["LogisticRegression"]["macro_f1"]

    print("  Text-only (TF-IDF):        Macro F1 = {:.3f}".format(f1_text))
    print("  Metrics-only (CK):         Macro F1 = {:.3f}".format(f1_metrics))
    print("  Fused (TF-IDF + CK):       Macro F1 = {:.3f}".format(f1_fused))

    # Save
    with open(os.path.join(BASE, "models", "baseline_b_tfidf_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("\n✓ Results saved to models/baseline_b_tfidf_results.json")


# ══════════════════════════════════════════════════════════════
#  MODE 2: CodeBERT Fine-tuning (run on YOUR machine with GPU)
# ══════════════════════════════════════════════════════════════

CODEBERT_SCRIPT = '''
"""
CodeBERT Fine-Tuning Script
============================
Requirements (install on your machine):
    pip install transformers datasets torch accelerate scikit-learn

Run:
    python baseline_b_codebert.py

This script:
  1. Loads your dataset.json
  2. Tokenizes code with microsoft/codebert-base tokenizer
  3. Fine-tunes for sequence classification (6 smell classes)
  4. Evaluates on test set
  5. Optionally fuses CodeBERT embeddings + CK metrics
"""

import json, os
import torch
import numpy as np
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EvalPrediction,
)
from sklearn.metrics import f1_score
from sklearn.preprocessing import LabelEncoder

BASE = "/home/claude/code_smell_project"  # <-- change if needed

# ── Load data ──
with open(os.path.join(BASE, "dataset", "dataset.json")) as f:
    dataset = json.load(f)
with open(os.path.join(BASE, "dataset", "split_info.json")) as f:
    splits = json.load(f)

import pandas as pd
df = pd.DataFrame(dataset)
train_df = df[df["project"].isin(splits["train"])]
test_df  = df[df["project"].isin(splits["test"])]

# ── Label encoding ──
le = LabelEncoder()
le.fit(["GodClass", "FeatureEnvy", "LongMethod", "DataClass", "DeadCode", "Clean"])
y_train = le.transform(train_df["true_smell"].values)
y_test  = le.transform(test_df["true_smell"].values)

# ── Tokenizer & Model ──
MODEL_NAME = "microsoft/codebert-base"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=6)

# ── Dataset class ──
class CodeSmellDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            str(self.texts[idx]),
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        return {
            "input_ids":      encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "labels":         torch.tensor(self.labels[idx], dtype=torch.long),
        }

train_dataset = CodeSmellDataset(train_df["raw_code"].values, y_train, tokenizer)
test_dataset  = CodeSmellDataset(test_df["raw_code"].values,  y_test,  tokenizer)

# ── Compute metrics ──
def compute_metrics(eval_pred: EvalPrediction):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    macro_f1 = f1_score(labels, preds, average="macro", zero_division=0)
    micro_f1 = f1_score(labels, preds, average="micro", zero_division=0)
    return {"macro_f1": macro_f1, "micro_f1": micro_f1}

# ── Training args ──
training_args = TrainingArguments(
    output_dir=os.path.join(BASE, "models", "codebert_checkpoints"),
    num_train_epochs=10,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=16,
    learning_rate=2e-5,
    weight_decay=0.01,
    warmup_ratio=0.1,
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="macro_f1",
    greater_is_better=True,
    logging_steps=10,
    fp16=True,  # set False if no GPU / use bf16=True for newer GPUs
    report_to="none",
)

# ── Trainer ──
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=test_dataset,
    compute_metrics=compute_metrics,
)

# ── Train ──
print("Starting CodeBERT fine-tuning...")
trainer.train()

# ── Evaluate ──
results = trainer.evaluate()
print("\\nCodeBERT Results:")
print("  Macro F1: {:.3f}".format(results["eval_macro_f1"]))
print("  Micro F1: {:.3f}".format(results["eval_micro_f1"]))

# ── Save results ──
with open(os.path.join(BASE, "models", "baseline_b_codebert_results.json"), "w") as f:
    json.dump(results, f, indent=2)

print("\\n✓ CodeBERT fine-tuning complete. Model saved.")

# ════════════════════════════════════════════════════════
# OPTIONAL: Feature Fusion (CodeBERT embeddings + CK metrics)
# ════════════════════════════════════════════════════════
# After training, extract embeddings from the [CLS] token,
# concatenate with CK metrics, and train an MLP on top.
# This often improves structural smell detection.
#
# See: https://huggingface.co/docs/transformers/main_classes/model
# Use model.get_output_embeddings() or hook into the last hidden state.
# ════════════════════════════════════════════════════════
'''

def save_codebert_script():
    """Save the CodeBERT script for the user to run on their GPU machine."""
    path = os.path.join(BASE, "baseline_b_codebert.py")
    with open(path, "w") as f:
        f.write(CODEBERT_SCRIPT)
    print("✓ CodeBERT script saved to: baseline_b_codebert.py")
    print("  Run on your GPU machine: python baseline_b_codebert.py")


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if "--codebert" in sys.argv:
        print("CodeBERT mode selected. Make sure you have a GPU and run:")
        print("  pip install transformers datasets torch accelerate")
        save_codebert_script()
    else:
        run_tfidf_mode()
        save_codebert_script()
