#!/usr/bin/env python
import argparse
import json
from pathlib import Path

from datasets import load_dataset


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def pick_split(dataset_dict) -> str:
    for preferred in ('train', 'validation', 'test'):
        if preferred in dataset_dict:
            return preferred
    return next(iter(dataset_dict.keys()))


def safe_row_to_json(row: dict) -> str:
    cleaned = {k: v for k, v in row.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))}
    return json.dumps(cleaned, ensure_ascii=False)


def download_dataset(dataset_id: str, output_file: Path, max_rows: int) -> bool:
    try:
        ds = load_dataset(dataset_id)
        split = pick_split(ds)
        rows = ds[split]
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with output_file.open('w', encoding='utf-8') as fout:
            for idx, row in enumerate(rows):
                if idx >= max_rows:
                    break
                fout.write(safe_row_to_json(row) + '\n')
        return True
    except Exception as exc:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.with_suffix('.error.txt').write_text(str(exc), encoding='utf-8')
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description='Download datasets from discovered manifest')
    parser.add_argument('--manifest', default='ai/training_pipeline/configs/datasets_manifest.json')
    parser.add_argument('--output-dir', default='ai/training_pipeline/data/raw')
    parser.add_argument('--max-per-category', type=int, default=3)
    parser.add_argument('--max-rows', type=int, default=5000)
    args = parser.parse_args()

    manifest = load_manifest(Path(args.manifest))
    output_dir = Path(args.output_dir)

    for category, datasets in manifest.get('categories', {}).items():
        selected = datasets[: args.max_per_category]
        for entry in selected:
            dataset_id = entry['id']
            safe_name = dataset_id.replace('/', '__')
            output_file = output_dir / category / f'{safe_name}.jsonl'
            ok = download_dataset(dataset_id, output_file, max_rows=args.max_rows)
            print(f'[{category}] {dataset_id}: {"ok" if ok else "failed"}')


if __name__ == '__main__':
    main()
