# src/sft_train.py
"""
SFT trainer for Llama-3.2-1B (or similar).
Designed to work on Windows with small GPU (4GB).
Uses 4-bit NF4 quantization + LoRA + gradient checkpointing.
Tokenization: right padding, labels=input_ids (no special wrapper required).
"""

import os
import json
import argparse
from datasets import Dataset

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
)

from peft import LoraConfig, get_peft_model


# -------------------------
# Load demos -> plain text
# -------------------------
def load_demos(path, max_examples=None):
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if max_examples and i >= max_examples:
                break
            rec = json.loads(line)
            # Expecting each demo to contain "prompt" and "trace"
            prompt = rec.get("prompt", "")
            trace = rec.get("trace", [])
            text = prompt + "\n" + "\n".join(trace) + "\n"
            out.append(text)
    return out


# -------------------------
# Simple collator (right-pad)
# -------------------------
class SimpleCollator:
    def __init__(self, pad_token_id):
        self.pad_token_id = pad_token_id

    def __call__(self, features):
        # features: list of dicts with input_ids, attention_mask, labels
        input_ids = [torch.tensor(f["input_ids"], dtype=torch.long) for f in features]
        attn = [torch.tensor(f["attention_mask"], dtype=torch.long) for f in features]
        labels = [torch.tensor(f["labels"], dtype=torch.long) for f in features]

        input_ids = torch.nn.utils.rnn.pad_sequence(input_ids, batch_first=True, padding_value=self.pad_token_id)
        attn = torch.nn.utils.rnn.pad_sequence(attn, batch_first=True, padding_value=0)
        labels = torch.nn.utils.rnn.pad_sequence(labels, batch_first=True, padding_value=self.pad_token_id)

        # mask padding tokens in labels
        labels = labels.clone()
        labels[labels == self.pad_token_id] = -100

        return {"input_ids": input_ids, "attention_mask": attn, "labels": labels}


# -------------------------
# Main training flow
# -------------------------
def main(args):
    # Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_name,
        padding_side="right",
        truncation_side="right",
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load demos
    texts = load_demos(args.demos, max_examples=args.max_examples)
    dataset = Dataset.from_dict({"text": texts})

    # Tokenize and set labels explicitly
    def tokenize_and_label(batch):
        enc = tokenizer(
            batch["text"],
            truncation=True,
            max_length=args.max_length,
            padding="longest",
            return_attention_mask=True,
        )
        # critical: labels = input_ids
        enc["labels"] = enc["input_ids"].copy()
        return enc

    tokenized = dataset.map(tokenize_and_label, batched=True, remove_columns=["text"])

    # BitsAndBytes 4-bit config (NF4)
    print("\n>>> Preparing quantization config (4-bit NF4)...\n")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        llm_int8_enable_fp32_cpu_offload=True,
    )

    # Load model
    print(f"\n>>> Loading model {args.model_name} in 4-bit (this may take a moment)...\n")
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        quantization_config=bnb_config,
        device_map="auto",
        attn_implementation="eager",
    )

    # VRAM saving
    model.config.use_cache = False
    model.gradient_checkpointing_enable()

    # LoRA config (LLaMA-style module names)
    print("\n>>> Applying LoRA...\n")
    lora_cfg = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ],
    )

    model = get_peft_model(model, lora_cfg)

    # Ensure grads on input embeddings if needed (safe for Llama)
    try:
        if hasattr(model, "enable_input_require_grads"):
            model.enable_input_require_grads()
    except Exception:
        # non-fatal; continue
        pass

    # Print trainable LoRA params for sanity
    print("\nTrainable LoRA parameters:")
    total_trainable = 0
    for name, p in model.named_parameters():
        if p.requires_grad:
            print("TRAIN:", name)
            total_trainable += p.numel()
    print(f"\nTotal trainable params: {total_trainable:,}\n")

    # Collator & Trainer args (4GB-friendly)
    collator = SimpleCollator(pad_token_id=tokenizer.pad_token_id)

    training_args = TrainingArguments(
        output_dir=args.out_dir,
        per_device_train_batch_size=1,       # 4GB safe
        gradient_accumulation_steps=4,       # effective batch size = 4
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        logging_steps=10,
        save_steps=200,
        warmup_steps=20,
        fp16=False,
        bf16=False,
        optim="adamw_torch",
        gradient_checkpointing=True,
        max_grad_norm=1.0,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=collator,
    )

    # Train
    print("\n>>> Starting SFT...\n")
    trainer.train()

    # Save LoRA adapter
    out_lora = os.path.join(args.out_dir, "lora")
    os.makedirs(out_lora, exist_ok=True)
    model.save_pretrained(out_lora)
    print(f"\n>>> LoRA saved to: {out_lora}\n")
    print("\n>>> SFT complete.\n")


# -------------------------
# CLI
# -------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demos", required=True, help="Path to CoE demo jsonl")
    parser.add_argument("--model-name", default="meta-llama/Llama-3.2-1B")
    parser.add_argument("--out-dir", default="experiments/sft_llama")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--max_length", type=int, default=1024)
    parser.add_argument("--max-examples", type=int, default=None)
    args = parser.parse_args()
    main(args)



