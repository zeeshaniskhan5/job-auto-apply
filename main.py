#!/usr/bin/env python3
"""
Job Auto Apply — Unified async launcher
Applies to jobs on LinkedIn, Indeed, and Naukri simultaneously.
"""

import sys
import asyncio
import yaml
import logging
import colorlog
from pathlib import Path
from datetime import datetime


def setup_logging():
    # ── Console handler (coloured) ────────────────────────────
    console = colorlog.StreamHandler(sys.stdout)
    console.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s  %(levelname)-8s  %(message)s%(reset)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG":    "cyan",
            "INFO":     "green",
            "WARNING":  "yellow",
            "ERROR":    "red",
            "CRITICAL": "bold_red",
        },
    ))

    # ── File handler (plain text, saved to logs/) ─────────────
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"session_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(file_handler)

    logging.info(f"Log file: {log_file.resolve()}")
    return log_file


def load_config(path: str = "config.yaml") -> dict:
    p = Path(path)
    if not p.exists():
        print("\n[ERROR] config.yaml not found.")
        print("  Copy config.example.yaml to config.yaml and fill in your details.\n")
        sys.exit(1)
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


PLATFORMS = {
    "1": ("LinkedIn", "bots.linkedin_bot", "LinkedInBot"),
    "2": ("Indeed",   "bots.indeed_bot",   "IndeedBot"),
    "3": ("Naukri",   "bots.naukri_bot",   "NaukriBot"),
}


def print_menu():
    print("\n" + "=" * 52)
    print("   Job Auto Apply  -  LinkedIn | Indeed | Naukri")
    print("   Created by zxdevelopers")
    print("=" * 52)
    for key, (name, _, _) in PLATFORMS.items():
        print(f"   [{key}]  {name}")
    print("   [4]  All platforms simultaneously")
    print("   [0]  Exit")
    print("=" * 52)


def get_bot(key: str, config: dict):
    import importlib
    _, mod_path, cls_name = PLATFORMS[key]
    mod = importlib.import_module(mod_path)
    return getattr(mod, cls_name)(config)


async def run_bot(key: str, config: dict):
    name = PLATFORMS[key][0]
    log  = logging.getLogger(name)
    log.info(f"{'='*40}")
    log.info(f"Starting {name} bot")
    log.info(f"{'='*40}")
    bot = get_bot(key, config)
    try:
        await bot.run()
    except Exception as e:
        log.error(f"Bot crashed: {e}", exc_info=True)


async def run_all(config: dict):
    results = await asyncio.gather(
        *(run_bot(k, config) for k in PLATFORMS),
        return_exceptions=True,
    )
    for key, result in zip(PLATFORMS, results):
        if isinstance(result, Exception):
            logging.getLogger(PLATFORMS[key][0]).error(f"Bot failed: {result}")


async def main():
    log_file = setup_logging()
    config   = load_config()

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["1", "2", "3", "4"], default=None)
    args = parser.parse_args()

    choice = args.platform
    if not choice:
        print_menu()
        choice = input("\n   Enter choice: ").strip()

    logging.info(f"Search keywords : {config['search'].get('keywords')}")
    logging.info(f"Location        : {config['search'].get('location')}")
    logging.info(f"Max applications: {config['search'].get('max_applications')}")

    if choice == "0":
        print("   Goodbye!")

    elif choice in PLATFORMS:
        name = PLATFORMS[choice][0]
        print(f"\n   Starting {name}...\n")
        await run_bot(choice, config)

    elif choice == "4":
        print("\n   Starting all three platforms simultaneously...\n")
        await run_all(config)

    else:
        print("   Invalid choice.")
        sys.exit(1)

    logging.info("=" * 52)
    logging.info("All bots finished.")
    logging.info(f"Full log saved to: {log_file.resolve()}")
    logging.info("=" * 52)


if __name__ == "__main__":
    asyncio.run(main())
