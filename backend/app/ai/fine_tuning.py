"""Fine-tuning pipeline for sovereign debt LLM.

Supports LoRA/QLoRA fine-tuning of small models on domain-specific data.
Runs on CPU (slow) or GPU (fast). No external APIs.
"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional

TRAINING_DIR = Path(__file__).parent.parent.parent / "data" / "training"
DATASETS_DIR = TRAINING_DIR / "datasets"
CHECKPOINTS_DIR = TRAINING_DIR / "checkpoints"


def ensure_dirs():
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Dataset Preparation ────────────────────────────────────────────────

def create_qa_dataset(
    qa_pairs: List[Dict[str, str]],
    dataset_name: str = "sovereign_qa",
) -> str:
    """Create a QA dataset for fine-tuning. Returns path to dataset."""
    ensure_dirs()

    formatted = []
    for pair in qa_pairs:
        formatted.append({
            "instruction": pair.get("question", pair.get("instruction", "")),
            "input": pair.get("context", ""),
            "output": pair.get("answer", pair.get("output", "")),
        })

    path = DATASETS_DIR / f"{dataset_name}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for item in formatted:
            f.write(json.dumps(item) + "\n")

    return str(path)


def create_completion_dataset(
    examples: List[Dict[str, str]],
    dataset_name: str = "sovereign_completion",
) -> str:
    """Create a completion-style dataset."""
    ensure_dirs()

    path = DATASETS_DIR / f"{dataset_name}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps({
                "prompt": ex.get("prompt", ""),
                "completion": ex.get("completion", ""),
            }) + "\n")

    return str(path)


def load_dataset(path: str) -> List[Dict]:
    """Load a JSONL dataset."""
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


# ── Training ───────────────────────────────────────────────────────────

def train_lora(
    dataset_path: str,
    base_model: str = "sshleifer/distilgpt2",
    output_dir: Optional[str] = None,
    epochs: int = 3,
    batch_size: int = 4,
    learning_rate: float = 2e-4,
    lora_r: int = 8,
    lora_alpha: int = 16,
    max_seq_length: int = 512,
) -> Dict[str, Any]:
    """Fine-tune a model using LoRA. Returns training results."""
    ensure_dirs()

    if output_dir is None:
        model_hash = hashlib.sha256(base_model.encode()).hexdigest()[:8]
        output_dir = str(CHECKPOINTS_DIR / f"lora_{model_hash}")

    try:
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            TrainingArguments,
            Trainer,
            DataCollatorForLanguageModeling,
        )
        from peft import LoraConfig, get_peft_model, TaskType
        import torch

        # Load base model
        tokenizer = AutoTokenizer.from_pretrained(base_model)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype=torch.float32,
            device_map="cpu",
        )

        # Configure LoRA
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=lora_r,
            lora_alpha=lora_alpha,
            lora_dropout=0.1,
            target_modules=["c_attn", "c_proj"] if hasattr(model, "transformer") else ["q_proj", "v_proj"],
        )
        model = get_peft_model(model, lora_config)

        # Load dataset
        raw_data = load_dataset(dataset_path)

        def format_example(example):
            if "instruction" in example:
                text = f"### Instruction:\n{example['instruction']}\n\n### Response:\n{example['output']}"
            else:
                text = f"{example.get('prompt', '')}{example.get('completion', '')}"
            return tokenizer(text, truncation=True, max_length=max_seq_length, padding="max_length")

        tokenized = [format_example(ex) for ex in raw_data]

        # Training
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            learning_rate=learning_rate,
            warmup_steps=10,
            logging_steps=5,
            save_strategy="epoch",
            fp16=False,
            report_to="none",
        )

        data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized if tokenized else None,
            data_collator=data_collator,
        )

        if tokenized:
            trainer.train()

        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)

        return {
            "status": "completed",
            "base_model": base_model,
            "output_dir": output_dir,
            "epochs": epochs,
            "dataset_size": len(raw_data),
            "lora_r": lora_r,
            "lora_alpha": lora_alpha,
        }

    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "base_model": base_model,
        }


# ── Evaluation ─────────────────────────────────────────────────────────

def evaluate_model(
    model_path: str,
    test_pairs: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Evaluate a fine-tuned model on test pairs."""
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.float32, device_map="cpu")

        results = []
        for pair in test_pairs:
            prompt = f"### Instruction:\n{pair['question']}\n\n### Response:\n"
            inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.7, do_sample=True)
            response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            results.append({
                "question": pair["question"],
                "expected": pair.get("answer", ""),
                "generated": response,
                "match": response.lower().strip() == pair.get("answer", "").lower().strip(),
            })

        accuracy = sum(1 for r in results if r["match"]) / len(results) if results else 0
        return {"accuracy": accuracy, "total": len(results), "matches": sum(1 for r in results if r["match"]), "details": results}

    except Exception as e:
        return {"accuracy": 0, "error": str(e)}
