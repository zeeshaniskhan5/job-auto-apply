# Job Auto Apply

Automate job applications across **LinkedIn**, **Indeed**, and **Naukri** from a single tool.

---

## Features

- One-click apply on LinkedIn Easy Apply, Indeed Smart Apply, and Naukri Apply
- Run all three platforms **simultaneously** or one at a time
- Smart Q&A engine — automatically answers screening questions
- Auto resume upload
- Persistent Chrome sessions — log in once, never again
- Human-like typing with randomized delays (anti-bot detection)
- Profile bump on Naukri (pushes your profile to top of recruiter searches)
- Fully configurable via a single `config.yaml` file

---

## Requirements

- Windows 10/11 (Mac/Linux also supported)
- [Python 3.8+](https://www.python.org/downloads/)
- [Google Chrome](https://www.google.com/chrome/) installed
- Your resume as a PDF file

---

## Setup (3 steps)

### Step 1 — Run Setup
Double-click `setup.bat`

This installs all dependencies and creates your `config.yaml`.

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
│   ├── base_bot.py          # Shared Selenium setup & helpers
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

- **First run:** The browser will open and log you in. After that, sessions are saved and login is automatic.
- **CAPTCHA:** If a CAPTCHA appears, solve it manually in the browser — the bot will continue after.
- **Max applications:** Set `max_applications` in `config.yaml` to control how many jobs each platform applies to per run.
- **Screening questions:** Add your custom answers under `answers:` in `config.yaml` using keywords from the questions you're asked.
- **Resume path:** Use the full absolute path, e.g. `C:/Users/YourName/Documents/resume.pdf`

---

## Disclaimer

This tool is for personal use only. Use it responsibly and in accordance with each platform's terms of service. Applying to jobs in bulk may result in account restrictions on some platforms.
