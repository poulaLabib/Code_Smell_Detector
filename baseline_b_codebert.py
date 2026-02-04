
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
print("\nCodeBERT Results:")
print("  Macro F1: {:.3f}".format(results["eval_macro_f1"]))
print("  Micro F1: {:.3f}".format(results["eval_micro_f1"]))

# ── Save results ──
with open(os.path.join(BASE, "models", "baseline_b_codebert_results.json"), "w") as f:
    json.dump(results, f, indent=2)

print("\n✓ CodeBERT fine-tuning complete. Model saved.")

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
