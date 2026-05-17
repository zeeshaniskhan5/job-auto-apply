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


def setup_logging():
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG":    "cyan",
            "INFO":     "green",
            "WARNING":  "yellow",
            "ERROR":    "red",
            "CRITICAL": "bold_red",
        },
    ))
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def load_config(path: str = "config.yaml") -> dict:
    p = Path(path)
    if not p.exists():
        print("\n[ERROR] config.yaml not found.")
        print("  → Copy config.example.yaml to config.yaml and fill in your details.\n")
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
    bot = get_bot(key, config)
    try:
        await bot.run()
    except Exception as e:
        logging.getLogger(PLATFORMS[key][0]).error(f"Bot crashed: {e}", exc_info=True)


async def run_all(config: dict):
    await asyncio.gather(
        *(run_bot(k, config) for k in PLATFORMS)
    )


async def main():
    setup_logging()
    config = load_config()
    print_menu()
    choice = input("\n   Enter choice: ").strip()

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

    print("\n   Done! Check the logs above for results.")


if __name__ == "__main__":
    asyncio.run(main())
