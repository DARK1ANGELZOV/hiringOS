#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

from huggingface_hub import HfApi, snapshot_download

GIB = 1024**3


@dataclass(frozen=True)
class RepoSpec:
    repo_id: str
    repo_type: str  # model | dataset
    label: str


def configured_specs() -> list[RepoSpec]:
    return [
        RepoSpec(os.getenv('RESUME_LLM_MODEL_ID', 'Qwen/Qwen2.5-1.5B-Instruct'), 'model', 'resume_llm'),
        RepoSpec(os.getenv('INTERVIEW_LLM_MODEL_ID', 'Qwen/Qwen2.5-1.5B-Instruct'), 'model', 'interview_llm'),
        RepoSpec(os.getenv('EMBEDDING_MODEL_ID', 'sentence-transformers/all-MiniLM-L6-v2'), 'model', 'embeddings'),
        RepoSpec(os.getenv('STT_MODEL_ID', 'openai/whisper-small'), 'model', 'stt'),
        RepoSpec(os.getenv('TTS_MODEL_ID', 'microsoft/speecht5_tts'), 'model', 'tts'),
        RepoSpec(os.getenv('TTS_VOCODER_MODEL_ID', 'microsoft/speecht5_hifigan'), 'model', 'tts_vocoder'),
        RepoSpec(os.getenv('VIDEO_ANALYSIS_MODEL_ID', 'openai/clip-vit-base-patch32'), 'model', 'video_analysis'),
        RepoSpec(os.getenv('TTS_SPEAKER_DATASET_ID', 'Matthijs/cmu-arctic-xvectors'), 'dataset', 'tts_speaker_dataset'),
    ]


def repo_size_bytes(api: HfApi, spec: RepoSpec) -> int:
    if spec.repo_type == 'dataset':
        info = api.dataset_info(spec.repo_id, files_metadata=True)
    else:
        info = api.model_info(spec.repo_id, files_metadata=True)

    total = 0
    for sibling in info.siblings:
        size = getattr(sibling, 'size', None)
        if isinstance(size, int):
            total += size
    return total


def fmt_gib(size_bytes: int) -> str:
    return f'{size_bytes / GIB:.2f} GiB'


def main() -> int:
    parser = argparse.ArgumentParser(description='Check and optionally pre-download local HF models against memory budget.')
    parser.add_argument('--budget-gb', type=float, default=12.0, help='Maximum allowed total size in GiB.')
    parser.add_argument('--download', action='store_true', help='Download snapshots into HF cache.')
    parser.add_argument('--cache-dir', default=os.getenv('HF_HOME') or None, help='Custom HF cache directory.')
    args = parser.parse_args()

    api = HfApi()
    specs = configured_specs()

    dedup: dict[tuple[str, str], RepoSpec] = {}
    for spec in specs:
        dedup[(spec.repo_type, spec.repo_id)] = spec
    unique_specs = list(dedup.values())

    print('Configured HF repositories:')
    for spec in unique_specs:
        print(f'- [{spec.repo_type}] {spec.repo_id} ({spec.label})')

    size_rows: list[tuple[RepoSpec, int]] = []
    total = 0
    for spec in unique_specs:
        size = repo_size_bytes(api, spec)
        size_rows.append((spec, size))
        total += size

    print('\nResolved repository sizes:')
    for spec, size in size_rows:
        print(f'- {spec.repo_id:<45} {fmt_gib(size)}')

    budget_bytes = int(args.budget_gb * GIB)
    print(f'\nTotal: {fmt_gib(total)} | Budget: {args.budget_gb:.2f} GiB')

    if total > budget_bytes:
        print('ERROR: total configured model/dataset size exceeds budget.')
        return 2

    if args.download:
        print('\nDownloading repositories...')
        for spec, _size in size_rows:
            print(f'- downloading [{spec.repo_type}] {spec.repo_id}')
            snapshot_download(
                repo_id=spec.repo_id,
                repo_type=spec.repo_type,
                cache_dir=args.cache_dir,
                local_dir_use_symlinks=False,
                resume_download=True,
            )
        print('Download completed.')

    print('Budget check passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
