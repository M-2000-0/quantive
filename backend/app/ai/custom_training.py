"""Custom model training pipeline.

Builds a small (1-3B) language model from scratch for sovereign debt domain.
Includes tokenizer training, pretraining, and domain adaptation.
"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional

TRAINING_DIR = Path(__file__).parent.parent.parent / "data" / "training"
CORPUS_DIR = TRAINING_DIR / "corpus"
TOKENIZER_DIR = TRAINING_DIR / "tokenizer"
MODELS_DIR = TRAINING_DIR / "models"


def ensure_dirs():
    for d in [TRAINING_DIR, CORPUS_DIR, TOKENIZER_DIR, MODELS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ── Corpus Preparation ─────────────────────────────────────────────────

def prepare_corpus(
    documents: List[str],
    corpus_name: str = "sovereign_debt",
) -> str:
    """Prepare a text corpus for tokenizer training and pretraining."""
    ensure_dirs()

    path = CORPUS_DIR / f"{corpus_name}.txt"
    with open(path, "w", encoding="utf-8") as f:
        for doc in documents:
            f.write(doc.strip() + "\n\n")

    return str(path)


def load_corpus(path: str) -> List[str]:
    """Load corpus as list of documents (separated by double newlines)."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return [doc.strip() for doc in content.split("\n\n") if doc.strip()]


# ── Tokenizer Training ─────────────────────────────────────────────────

def train_tokenizer(
    corpus_path: str,
    vocab_size: int = 32000,
    model_name: str = "sovereign_tokenizer",
) -> str:
    """Train a BPE tokenizer on the corpus."""
    ensure_dirs()
    output_dir = str(TOKENIZER_DIR / model_name)

    try:
        from tokenizers import Tokenizer, models, pre_tokenizers, trainers, processors

        tokenizer = Tokenizer(models.BPE(unk_token="[UNK]"))
        tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)

        trainer = trainers.BpeTrainer(
            vocab_size=vocab_size,
            special_tokens=["[UNK]", "[CLS]", "[SEP]", "[PAD]", "[MASK]"],
            min_frequency=2,
        )

        # Train from files
        files = [corpus_path] if isinstance(corpus_path, str) else corpus_path
        tokenizer.train(files, trainer)

        # Add CLS/SEP tokens
        cls_id = tokenizer.token_to_id("[CLS]")
        sep_id = tokenizer.token_to_id("[SEP]")
        tokenizer.post_processor = processors.TemplateProcessing(
            single=f"[CLS]:0 $A:0 [SEP]:0",
            pair=f"[CLS]:0 $A:0 [SEP]:0 $B:0 [SEP]:0",
            special_tokens=[("[CLS]", cls_id), ("[SEP]", sep_id)],
        )

        tokenizer.save(f"{output_dir}/tokenizer.json")

        # Save config
        config = {
            "vocab_size": vocab_size,
            "model_name": model_name,
            "corpus_path": corpus_path,
            "special_tokens": ["[UNK]", "[CLS]", "[SEP]", "[PAD]", "[MASK]"],
        }
        with open(f"{output_dir}/config.json", "w") as f:
            json.dump(config, f, indent=2)

        return output_dir

    except Exception as e:
        return f"Error: {e}"


# ── Model Architecture ─────────────────────────────────────────────────

def get_model_config(
    vocab_size: int = 32000,
    d_model: int = 768,
    n_heads: int = 12,
    n_layers: int = 12,
    d_ff: int = 3072,
    max_seq_length: int = 2048,
) -> Dict[str, Any]:
    """Get model configuration for a small GPT-style model."""
    return {
        "vocab_size": vocab_size,
        "d_model": d_model,
        "n_heads": n_heads,
        "n_layers": n_layers,
        "d_ff": d_ff,
        "max_seq_length": max_seq_length,
        "activation": "gelu",
        "dropout": 0.1,
        "attention_dropout": 0.1,
        "layer_norm_epsilon": 1e-5,
        "initializer_range": 0.02,
    }


# ── Pretraining ────────────────────────────────────────────────────────

def pretrain_model(
    corpus_path: str,
    tokenizer_path: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    epochs: int = 10,
    batch_size: int = 8,
    learning_rate: float = 3e-4,
    warmup_steps: int = 1000,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Pretrain a small model on the corpus."""
    ensure_dirs()

    if config is None:
        config = get_model_config()

    if output_dir is None:
        config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:8]
        output_dir = str(MODELS_DIR / f"pretrained_{config_hash}")

    try:
        import torch
        import torch.nn as nn
        import math

        class SovereignGPT(nn.Module):
            def __init__(self, config):
                super().__init__()
                self.config = config
                self.embeddings = nn.Embedding(config["vocab_size"], config["d_model"])
                self.position_embeddings = nn.Embedding(config["max_seq_length"], config["d_model"])
                self.dropout = nn.Dropout(config["dropout"])

                layer = nn.TransformerDecoderLayer(
                    d_model=config["d_model"],
                    nhead=config["n_heads"],
                    dim_feedforward=config["d_ff"],
                    dropout=config["dropout"],
                    activation=config["activation"],
                    batch_first=True,
                )
                self.transformer = nn.TransformerDecoder(layer, num_layers=config["n_layers"])
                self.ln_f = nn.LayerNorm(config["d_model"], eps=config["layer_norm_epsilon"])
                self.head = nn.Linear(config["d_model"], config["vocab_size"], bias=False)

                self.apply(self._init_weights)

            def _init_weights(self, module):
                if isinstance(module, (nn.Linear, nn.Embedding)):
                    module.weight.data.normal_(mean=0.0, std=self.config["initializer_range"])
                elif isinstance(module, nn.LayerNorm):
                    module.bias.data.zero_()
                    module.weight.data.fill_(1.0)

            def forward(self, input_ids):
                seq_length = input_ids.size(1)
                position_ids = torch.arange(seq_length, dtype=torch.long, device=input_ids.device).unsqueeze(0)
                embeds = self.embeddings(input_ids) + self.position_embeddings(position_ids)
                embeds = self.dropout(embeds)

                mask = nn.Transformer.generate_square_subsequent_mask(seq_length).to(input_ids.device)
                hidden = self.transformer(embeds, embeds, mask=mask)
                hidden = self.ln_f(hidden)
                logits = self.head(hidden)
                return logits

        # Build model
        model = SovereignGPT(config)
        total_params = sum(p.numel() for p in model.parameters())

        return {
            "status": "initialized",
            "output_dir": output_dir,
            "config": config,
            "total_params": total_params,
            "total_params_m": round(total_params / 1e6, 1),
            "message": f"Model architecture created with {round(total_params / 1e6, 1)}M parameters. "
                       f"Full pretraining requires GPU and hours of compute. "
                       f"Use train_lora() for faster domain adaptation.",
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Domain Adaptation ──────────────────────────────────────────────────

def create_domain_dataset() -> List[Dict[str, str]]:
    """Create sovereign debt domain training data."""
    return [
        {"question": "What is sovereign debt?", "answer": "Sovereign debt is the total amount of money that a national government owes to domestic and foreign creditors, including bonds, loans, and other financial obligations."},
        {"question": "How is sovereign debt measured?", "answer": "Sovereign debt is typically measured as a percentage of GDP (debt-to-GDP ratio), which provides context for the country's ability to service its obligations."},
        {"question": "What factors affect sovereign bond yields?", "answer": "Key factors include credit rating, inflation expectations, economic growth prospects, fiscal deficit, political stability, monetary policy, and global risk sentiment."},
        {"question": "What is debt optimization?", "answer": "Debt optimization is the strategic management of a government's debt portfolio to minimize cost while managing risk, including maturity structure, currency mix, and interest rate exposure."},
        {"question": "What is the role of AI in sovereign debt management?", "answer": "AI can optimize debt issuance timing, predict yield curve movements, automate compliance monitoring, detect market anomalies, and provide scenario analysis for debt sustainability."},
        {"question": "What is a yield curve?", "answer": "A yield curve plots bond yields against maturities for a given issuer. It reflects market expectations about future interest rates and economic conditions."},
        {"question": "What is duration risk?", "answer": "Duration risk is the sensitivity of a bond's price to changes in interest rates. Higher duration means greater price volatility when rates change."},
        {"question": "What is the Debt-to-GDP ratio?", "answer": "The Debt-to-GDP ratio compares a country's total sovereign debt to its gross domestic product, indicating the government's ability to repay its debts from economic output."},
        {"question": "What are the main types of government bonds?", "answer": "Treasury bills (short-term), Treasury notes (medium-term), Treasury bonds (long-term), inflation-linked bonds, floating rate notes, and green/sustainable bonds."},
        {"question": "What is credit risk in sovereign debt?", "answer": "Credit risk is the risk that a sovereign borrower will default on its debt obligations, failing to make timely interest or principal payments."},
        {"question": "What is the role of central banks in sovereign debt?", "answer": "Central banks manage government debt issuance, conduct open market operations, set monetary policy affecting bond yields, and may act as lender of last resort."},
        {"question": "What is debt sustainability analysis?", "answer": "Debt sustainability analysis evaluates whether a government's current debt level and trajectory are compatible with maintaining long-term fiscal stability without requiring drastic policy changes."},
        {"question": "What are IMF debt sustainability frameworks?", "answer": "The IMF uses standardized frameworks with debt thresholds, growth scenarios, and probabilistic analysis to assess whether countries' debt levels are sustainable."},
        {"question": "What is foreign exchange risk in sovereign debt?", "answer": "FX risk arises when sovereign debt is denominated in foreign currencies, creating exposure to exchange rate fluctuations that can increase the domestic currency cost of debt service."},
        {"question": "What is the role of credit rating agencies?", "answer": "Rating agencies like S&P, Moody's, and Fitch assess sovereign creditworthiness, influencing borrowing costs and investor access to debt markets."},
        {"question": "What is debt restructuring?", "answer": "Debt restructuring involves modifying the terms of existing debt obligations, such as extending maturities, reducing interest rates, or writing down principal, to restore debt sustainability."},
        {"question": "What is a sovereign wealth fund?", "answer": "A sovereign wealth fund is a state-owned investment fund that manages excess revenues (often from natural resources) to stabilize the economy and save for future generations."},
        {"question": "What is fiscal consolidation?", "answer": "Fiscal consolidation involves reducing government deficits and debt accumulation through spending cuts, revenue increases, or structural reforms to improve fiscal sustainability."},
        {"question": "What is the difference between primary and overall fiscal balance?", "answer": "The primary balance excludes interest payments from the fiscal balance, showing whether the government can cover its non-interest spending from revenues."},
        {"question": "What is the role of IMF programs in sovereign debt?", "answer": "IMF programs provide financial assistance with conditions, technical assistance on debt management, and surveillance of fiscal and monetary policies to promote stability."},
    ]
