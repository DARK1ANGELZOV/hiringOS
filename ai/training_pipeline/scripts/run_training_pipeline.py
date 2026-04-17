#!/usr/bin/env python
import argparse
import subprocess
import sys


def run(cmd: list[str]) -> None:
    print('>>', ' '.join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description='Run full AI training pipeline')
    parser.add_argument('--with-train', action='store_true', help='Run LoRA training step')
    args = parser.parse_args()

    run([sys.executable, 'ai/training_pipeline/scripts/discover_datasets.py'])
    run([sys.executable, 'ai/training_pipeline/scripts/download_datasets.py'])
    run([sys.executable, 'ai/training_pipeline/scripts/preprocess.py'])

    if args.with_train:
        run([sys.executable, 'ai/training_pipeline/scripts/train_lora.py'])


if __name__ == '__main__':
    main()
