# Job Auto Apply

> Created by **[zxdevelopers](https://github.com/zeeshaniskhan5)**

Automate job applications across **LinkedIn**, **Indeed**, and **Naukri** from a single tool.

---

## Features

- One-click apply on LinkedIn Easy Apply, Indeed Smart Apply, and Naukri Apply
- Run all three platforms **simultaneously** or one at a time
- Smart Q&A engine — automatically answers screening questions
- Auto resume upload
- Persistent Playwright browser sessions — log in once, never again
- Built-in stealth mode (bypasses bot detection automatically)
- Human-like typing with per-character randomized delays
- Profile bump on Naukri (pushes your profile to top of recruiter searches)
- Fully configurable via a single `config.yaml` file

---

## Requirements

- Windows 10/11 (Mac/Linux also supported)
- [Python 3.8+](https://www.python.org/downloads/)
- Your resume as a PDF file

> **No Chrome installation needed.** `setup.bat` installs Playwright's own Chromium automatically.

---

## Setup (3 steps)

### Step 1 — Run Setup
Double-click `setup.bat`

This will automatically:
1. Install Python packages (`playwright`, `pyyaml`, `colorlog`)
2. Download Playwright's Chromium browser
3. Create your `config.yaml` from the example template

### Step 2 — Edit config.yaml
Open `config.yaml` and fill in:
- Your name, phone, resume path, location, salary, experience
- LinkedIn / Indeed / Naukri email & password
- Job search keywords and location
- Custom answers to screening questions

### Step 3 — Run the Bot
Double-click `run.bat`

Choose a platform (or option 4 to run all at once):

```
[1] LinkedIn
[2] Indeed
[3] Naukri
[4] All platforms simultaneously
[0] Exit
```

---

## Project Structure

```
job-auto-apply/
├── bots/
│   ├── linkedin_bot.py      # LinkedIn Easy Apply automation
│   ├── indeed_bot.py        # Indeed Smart Apply automation
│   └── naukri_bot.py        # Naukri Apply automation
├── core/
│   ├── base_bot.py          # Shared Playwright async browser setup & helpers
│   └── qa_engine.py         # Keyword-based Q&A answering engine
├── profile/                 # Saved Chrome sessions (auto-created)
│   ├── linkedin/
│   ├── indeed/
│   └── naukri/
├── logs/
├── config.yaml              # Your configuration (fill this in)
├── config.example.yaml      # Template to copy from
├── main.py                  # CLI launcher
├── requirements.txt
├── setup.bat                # One-click Windows setup
└── run.bat                  # One-click Windows launcher
```

---

## Tips

- **First run:** The Playwright browser opens and logs you in. Sessions are saved in `profile/` — future runs skip login entirely.
- **All 3 simultaneously:** Choose option `[4]` — platforms run in parallel via `asyncio.gather()`, each in its own browser window.
- **CAPTCHA:** Solve it manually in the browser window — the bot waits and continues automatically after.
- **Max applications:** Set `max_applications` in `config.yaml` to control how many jobs each platform applies to per run.
- **Screening questions:** Add keyword → answer pairs under `answers:` in `config.yaml`. The bot matches question text to your keywords automatically.
- **Resume path:** Use the full absolute path with forward slashes, e.g. `C:/Users/YourName/Documents/resume.pdf`
- **No Chrome needed:** Playwright ships its own Chromium — your system Chrome is untouched.

---

## Disclaimer

This tool is for personal use only. Use it responsibly and in accordance with each platform's terms of service. Applying to jobs in bulk may result in account restrictions on some platforms.

---

## Credits

Built by **[zxdevelopers](https://github.com/zeeshaniskhan5)**
