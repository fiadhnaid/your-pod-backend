import os, json, logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI             # pip install openai>=1.13.3
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
import uuid

# ── env & logging ────────────────────────────────────────────────────────────
load_dotenv()                         # reads .env
OPENAI_KEY = os.getenv("OPENAI_KEY")  # keep real key out of source control
ELEVENLABS_API_KEY='sk_149a99c5ad384a0b612c18f4b20c1d3465a27f17c454105b'

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

Return JSON with the schema I provide next. You must return the FULL SCRIPT FOR EACH PODCAST OPTION. Your purpose is to inform and engage the listener - hyperpersonalise to the information you have on them and ground the content of the podcast in facts and reputed bodies of knowledge and figures. You must engage the listener with the information you have on them. The 3 options should be varied and one should be left field (but still tailored to the info you have on them) so they have a variety to choose from.
""".strip()

        # 3️⃣ Hit OpenAI (structured output enforced)
        result = call_openai_for_podcasts(prompt)

        # 4️⃣ Give it straight back to the front‑end
        return jsonify(result), 200

    except Exception as e:
        logging.exception("Error in /generate_options")
        return jsonify(error=str(e)), 500



# ── placeholder for Jack to write over ───────────────────────────────────────
def generate_audio(option: dict) -> dict:
    """
    Calls ElevenLabs to generate audio for the given podcast option.
    Saves the audio to static/audio/<uuid>.mp3 and returns the public URL.
    """
    logging.info("Generating audio for option: %s", option["title"])
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY") or ELEVENLABS_API_KEY
    elevenlabs = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    # Use a fixed voice for now (Adam)
    voice_id = "pNInz6obpgDQGcFmaJgB"  # Adam pre-made voice
    output_format = "mp3_22050_32"
    model_id = "eleven_turbo_v2_5"
    script = option["script"]

    response = elevenlabs.text_to_speech.convert(
        voice_id=voice_id,
        output_format=output_format,
        text=script,
        model_id=model_id,
        voice_settings=VoiceSettings(
            stability=0.0,
            similarity_boost=1.0,
            style=0.0,
            use_speaker_boost=True,
            speed=1.0,
        ),
    )

    # Save to static/audio/<uuid>.mp3
    audio_id = str(uuid.uuid4())
    audio_path = f"static/audio/{audio_id}.mp3"
    with open(audio_path, "wb") as f:
        for chunk in response:
            if chunk:
                f.write(chunk)

    # Build the public URL (assuming server is accessible at the same host)
    # If running locally, you may want to adjust the host/port as needed
    server_url = request.host_url.rstrip("/")
    audio_url = f"{server_url}/static/audio/{audio_id}.mp3"
    return {"audio_url": audio_url}

# ── POST /select_option ──────────────────────────────────────────────────────
@app.route("/select_option", methods=["POST"])
def select_option():
    """
    Front‑end POSTs the chosen podcast option.
    Expected JSON:
    {
      "selected_index": 0|1|2,
      "options": [ {title, description, script, voice_description}, ... ]
    }
    """
    payload = request.get_json(silent=True) or {}

    # Basic validation
    if "selected_index" not in payload or "options" not in payload:
        return jsonify(error="selected_index and options are required"), 400

    idx      = payload["selected_index"]
    options  = payload["options"]

    if not isinstance(options, list) or idx not in {0,1,2} or idx >= len(options):
        return jsonify(error="Invalid index or options array"), 400

    selected_option = options[idx]

    try:
        # 👉 Call the audio generator (sync for POC; make async later if needed)
        audio_info = generate_audio(selected_option)

        # Send minimal success payload back to front‑end
        return jsonify(
            message="Audio generation triggered",
            selected_title=selected_option["title"],
            audio=audio_info      # currently just {audio_url: "..."}
        ), 200

    except Exception as e:
        logging.exception("Error in /select_option")
        return jsonify(error=str(e)), 500

# ── dev server entry‑point ───────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))   # change PORT env to dodge conflicts
    app.run(host="0.0.0.0", port=port, debug=True)
