#!/usr/bin/env python
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import list_datasets


CATEGORIES = {
    'resume': ['resume', 'cv', 'job profile'],
    'interview': ['interview', 'hiring interview', 'hr interview'],
    'skills': ['skills taxonomy', 'job skills', 'skill extraction'],
}


def discover(limit_per_query: int = 10) -> dict:
    collected: dict[str, list[dict]] = {key: [] for key in CATEGORIES}

    for category, queries in CATEGORIES.items():
        seen_ids: set[str] = set()
        for query in queries:
            datasets = list_datasets(search=query, limit=limit_per_query)
            for ds in datasets:
                if ds.id in seen_ids:
                    continue
                seen_ids.add(ds.id)
                collected[category].append(
                    {
                        'id': ds.id,
                        'downloads': ds.downloads,
                        'likes': ds.likes,
                        'last_modified': ds.last_modified.isoformat() if ds.last_modified else None,
                        'tags': ds.tags,
                    }
                )

    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'source': 'huggingface_hub.list_datasets',
        'categories': collected,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Discover open HF datasets for ATS AI training')
    parser.add_argument('--output', default='ai/training_pipeline/configs/datasets_manifest.json')
    parser.add_argument('--limit-per-query', type=int, default=10)
    args = parser.parse_args()

    manifest = discover(limit_per_query=args.limit_per_query)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Manifest saved: {output_path}')


if __name__ == '__main__':
    main()
