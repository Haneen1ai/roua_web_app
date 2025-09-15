import os
import signal
import sys
import threading
from dotenv import load_dotenv
from flask import Flask, render_template  # ما غيّرته
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface

# ⬇️ إضافة بسيطة: بنحتاج requests عشان نجيب توكن WebRTC من ElevenLabs
import requests
from flask import jsonify  # JSON، بس بنرجّع نص التوكن

# إعداد Flask
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

# ⬇️ إضافة بسيطة: مسار يعطي توكن المحادثة للواجهة
@app.route('/conversation-token', methods=['GET'])
def conversation_token():
    load_dotenv()
    API_KEY = os.environ.get('ELEVENLABS_API_KEY')
    AGENT_ID = os.environ.get('AGENT_ID')
    if not API_KEY or not AGENT_ID:
        return ("Missing ELEVENLABS_API_KEY or AGENT_ID", 400)

    r = requests.get(
        f"https://api.elevenlabs.io/v1/convai/conversation/token?agent_id={AGENT_ID}",
        headers={"xi-api-key": API_KEY},
        timeout=15
    )
    if r.status_code != 200:
        return (f"Failed to get conversation token: {r.text}", 502)

    token = r.json().get("token")
    return token or ("No token in response", 502)

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False)

def main():
    # شغل Flask في خيط منفصل
    threading.Thread(target=run_flask, daemon=True).start()

    load_dotenv()  # تحميل المتغيرات من .env

    AGENT_ID = os.environ.get('AGENT_ID')
    API_KEY = os.environ.get('ELEVENLABS_API_KEY')

    if not AGENT_ID:
        sys.stderr.write("❌ AGENT_ID environment variable must be set\n")
        sys.exit(1)

    if not API_KEY:
        sys.stderr.write("⚠️ ELEVENLABS_API_KEY not set, assuming the agent is public\n")

    client = ElevenLabs(api_key=API_KEY)

    conversation = Conversation(
        client,
        AGENT_ID,
        requires_auth=bool(API_KEY),
        audio_interface=DefaultAudioInterface(),
        callback_agent_response=lambda response: print(f"\n🟢 Agent: {response}"),
        callback_agent_response_correction=lambda original, corrected: print(f"\n✏️ Correction: {original} -> {corrected}"),
        callback_user_transcript=lambda transcript: print(f"\n🎤 You: {transcript}")
    )

    conversation.start_session()
    signal.signal(signal.SIGINT, lambda sig, frame: conversation.end_session())
    conversation_id = conversation.wait_for_session_end()
    print(f"\n📝 Conversation ID: {conversation_id}")

if __name__ == '__main__':
    main()