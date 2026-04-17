#!/usr/bin/env python
import argparse
import json
from pathlib import Path

from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments


def load_samples(path: Path) -> Dataset:
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return Dataset.from_list(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description='LoRA fine-tuning for ATS local models')
    parser.add_argument('--model-id', default='Qwen/Qwen2.5-1.5B-Instruct')
    parser.add_argument('--data', default='ai/training_pipeline/data/processed/train.jsonl')
    parser.add_argument('--output', default='ai/training_pipeline/artifacts/lora-model')
    parser.add_argument('--epochs', type=int, default=1)
    parser.add_argument('--batch-size', type=int, default=1)
    parser.add_argument('--max-length', type=int, default=1024)
    args = parser.parse_args()

    dataset = load_samples(Path(args.data))

    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(args.model_id, torch_dtype='auto', device_map='auto')

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=['q_proj', 'v_proj', 'k_proj', 'o_proj'],
        lora_dropout=0.05,
        bias='none',
        task_type='CAUSAL_LM',
    )
    model = get_peft_model(model, lora_config)

    def tokenize_fn(batch):
        text = [f"{p}\n{c}" for p, c in zip(batch['prompt'], batch['completion'])]
        tokenized = tokenizer(
            text,
            truncation=True,
            max_length=args.max_length,
            padding='max_length',
        )
        tokenized['labels'] = tokenized['input_ids'].copy()
        return tokenized

    tokenized_dataset = dataset.map(tokenize_fn, batched=True, remove_columns=dataset.column_names)

    training_args = TrainingArguments(
        output_dir=args.output,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        warmup_ratio=0.03,
        logging_steps=10,
        save_steps=100,
        bf16=False,
        fp16=False,
        report_to=[],
    )

    trainer = Trainer(model=model, args=training_args, train_dataset=tokenized_dataset)
    trainer.train()
    trainer.save_model(args.output)
    tokenizer.save_pretrained(args.output)
    print(f'LoRA model saved: {args.output}')


if __name__ == '__main__':
    main()
