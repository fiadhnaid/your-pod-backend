import os, json, logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI             # pip install openai>=1.13.3

# ── env & logging ────────────────────────────────────────────────────────────
load_dotenv()                         # reads .env
OPENAI_KEY = os.getenv("OPENAI_KEY")  # keep real key out of source control

client      = OpenAI(api_key=OPENAI_KEY)
CHAT_MODEL  = "gpt-4o-mini"           # fast + cheap, tweak as you like

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# ── Flask app bootstrap ──────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)                             # open CORS to everyone – fine for a hackathon

# 0. Health‑check (the one you already had)
@app.route("/")
def hello_world():
    return jsonify(message="🚀 Hello, Hackathon world!")

# ── helper: call OpenAI with JSON‑schema output ──────────────────────────────
def call_openai_for_podcasts(prompt: str) -> dict:
    """
    Sends a single prompt to OpenAI and enforces the response to match `response_schema`.
    Returns the parsed JSON (already a Python dict).
    """
    response_schema = {
        "type": "object",
        "properties": {
            "options": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "title":             {"type": "string"},
                        "description":       {"type": "string"},
                        "script":            {"type": "string"},
                        "voice_description": {"type": "string"}
                    },
                    "required": ["title", "description", "script", "voice_description"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["options"],
        "additionalProperties": False,
    }

    completion = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "podcast_options",   # 👈 required wrapper
                "schema": response_schema
            }
        },
    )
    structured = completion.choices[0].message
    if structured.refusal:            # GPT refused (unlikely here)
        raise RuntimeError("OpenAI refused the request")

    return json.loads(structured.content)   # already conforms to schema

# ── POST /generate_options ───────────────────────────────────────────────────
@app.route("/generate_options", methods=["POST"])
def generate_options():
    """
    Expected JSON from front‑end:
    {
      "growth_areas": ["leadership", "stakeholder management"],
      "why": "stepping into a senior role soon",
      "reference_text": "optional long paste from docs/books",
      "length_minutes": 6,
      "preferred_style": "conversational true‑crime vibe",
      "voice_tone": "narrated like Gossip Girl"
    }
    """
    payload = request.get_json(silent=True) or {}
    try:
        # 1️⃣ Validate minimal required fields
        if "growth_areas" not in payload or "length_minutes" not in payload:
            return jsonify(error="Missing required keys"), 400

        # 2️⃣ Craft prompt
        prompt = f"""
Act as a hyper‑personalised podcast generator.
Create **exactly three** podcast episode options.

User profile:
• Growth areas → {payload.get('growth_areas')}
• Why → {payload.get('why','(not specified)')}
• Preferred length → about {payload.get('length_minutes')} minutes
• They enjoy → {payload.get('preferred_style','(no particular style)')}
• Desired voice tone → {payload.get('voice_tone','(no preference)')}

Reference material (may be empty):
\"\"\"{payload.get('reference_text','')}\"\"\"

Return JSON with the schema I provide next. You must return the FULL SCRIPT FOR EACH PODCAST OPTION.
""".strip()

        # 3️⃣ Hit OpenAI (structured output enforced)
        result = call_openai_for_podcasts(prompt)

        # 4️⃣ Give it straight back to the front‑end
        return jsonify(result), 200

    except Exception as e:
        logging.exception("Error in /generate_options")
        return jsonify(error=str(e)), 500

# ── dev server entry‑point ───────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))   # change PORT env to dodge conflicts
    app.run(host="0.0.0.0", port=port, debug=True)
