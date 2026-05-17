#!/usr/bin/env python3
"""
Job Auto Apply — Unified CLI launcher
Applies to jobs on LinkedIn, Indeed, and Naukri simultaneously.
"""

import sys
import yaml
import logging
import colorlog
import threading
from pathlib import Path

# ── Logging setup ─────────────────────────────────────────────

def setup_logging():
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    ))
    logging.basicConfig(level=logging.INFO, handlers=[handler])

# ── Config loader ─────────────────────────────────────────────

def load_config(path: str = "config.yaml") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        print(f"\n[ERROR] config.yaml not found.")
        print("  → Copy config.example.yaml to config.yaml and fill in your details.\n")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# ── Platform menu ─────────────────────────────────────────────

PLATFORMS = {
    "1": ("LinkedIn", "bots.linkedin_bot", "LinkedInBot"),
    "2": ("Indeed",   "bots.indeed_bot",   "IndeedBot"),
    "3": ("Naukri",   "bots.naukri_bot",   "NaukriBot"),
}

def print_menu():
    print("\n" + "=" * 50)
    print("  Job Auto Apply — Multi-Platform Bot")
    print("=" * 50)
    print("  Which platforms do you want to apply on?")
    print()
    for key, (name, _, _) in PLATFORMS.items():
        print(f"  [{key}] {name}")
    print("  [4] All platforms simultaneously")
    print("  [0] Exit")
    print("=" * 50)

def get_bot_instance(key: str, config: dict):
    import importlib
    _, module_path, class_name = PLATFORMS[key]
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls(config)

def run_bot(key: str, config: dict):
    bot = get_bot_instance(key, config)
    try:
        bot.run()
    except Exception as e:
        logging.getLogger(PLATFORMS[key][0]).error(f"Bot crashed: {e}", exc_info=True)

# ── Main ──────────────────────────────────────────────────────

def main():
    setup_logging()
    config = load_config()

    print_menu()
    choice = input("\n  Enter choice: ").strip()

    if choice == "0":
        print("  Goodbye!")
        sys.exit(0)

    elif choice in PLATFORMS:
        name = PLATFORMS[choice][0]
        print(f"\n  Starting {name} bot... (close the browser window to stop)\n")
        run_bot(choice, config)

    elif choice == "4":
        print("\n  Starting all platforms simultaneously...\n")
        threads = []
        for key in PLATFORMS:
            t = threading.Thread(
                target=run_bot,
                args=(key, config),
                name=PLATFORMS[key][0],
                daemon=True,
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

    else:
        print("  Invalid choice.")
        sys.exit(1)

    print("\n  All done! Check the logs above for results.")


if __name__ == "__main__":
    main()
