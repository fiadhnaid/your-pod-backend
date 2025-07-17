# Career‑Podcast Backend (Flask POC)

## Quick start
```bash
git clone <repo‑url>
cd career‑podcast‑backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your API keys here
python app.py          # Runs on http://localhost:5000/



# 1) Verify you have Python 3
###############################################################################
which python3           # should print something like /usr/bin/python3
python3 --version       # e.g. Python 3.11.x

# If those commands fail, install Python first (Homebrew: `brew install python`).

###############################################################################
# 2) Create a virtual environment *inside* the project
###############################################################################
python3 -m venv .venv   # creates ./venv directory hierarchy

# Activate it (zsh on macOS):
source .venv/bin/activate
# You should now see "(.venv)" at the start of your prompt.

###############################################################################
# 3) Install required packages into the venv
###############################################################################
pip install --upgrade pip           # optional but keeps things tidy
pip install -r requirements.txt     # installs Flask + python‑dotenv

PORT=5001 python app.py

