#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def extract_prompt_completion(category: str, row: dict) -> tuple[str, str] | None:
    if category == 'resume':
        source = row.get('resume') or row.get('text') or row.get('content')
        if not source:
            return None
        prompt = 'Extract structured profile from resume text.'
        completion = source
        return prompt, completion

    if category == 'interview':
        question = row.get('question') or row.get('prompt') or row.get('instruction')
        answer = row.get('answer') or row.get('response') or row.get('output')
        if not question or not answer:
            return None
        prompt = f'Interview question: {question}'
        completion = str(answer)
        return prompt, completion

    if category == 'skills':
        text = row.get('text') or row.get('job_description') or row.get('description')
        skills = row.get('skills') or row.get('labels') or row.get('tags')
        if not text or not skills:
            return None
        prompt = f'Extract required skills from text: {text}'
        completion = json.dumps({'skills': skills}, ensure_ascii=False)
        return prompt, completion

    return None


def main() -> None:
    parser = argparse.ArgumentParser(description='Preprocess raw datasets into SFT JSONL')
    parser.add_argument('--raw-dir', default='ai/training_pipeline/data/raw')
    parser.add_argument('--output', default='ai/training_pipeline/data/processed/train.jsonl')
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with output_path.open('w', encoding='utf-8') as fout:
        for category_dir in raw_dir.iterdir() if raw_dir.exists() else []:
            if not category_dir.is_dir():
                continue
            category = category_dir.name
            for file in category_dir.glob('*.jsonl'):
                for line in file.read_text(encoding='utf-8').splitlines():
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    pair = extract_prompt_completion(category, row)
                    if not pair:
                        continue
                    prompt, completion = pair
                    sample = {
                        'prompt': prompt,
                        'completion': completion,
                    }
                    fout.write(json.dumps(sample, ensure_ascii=False) + '\n')
                    written += 1

    print(f'Prepared {written} samples -> {output_path}')


if __name__ == '__main__':
    main()
