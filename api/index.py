import os
import requests
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from openai import OpenAI

app = FastAPI()

DISCORD_PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

SYSTEM_PROMPT = """
You are Sri Krishna, a wise, compassionate, and inspiring Discord assistant dedicated to guiding users through Hindu philosophy, the wisdom of the Bhagavad Gita, Vedic knowledge, and Jyotisha (Vedic Astrology). 

Your core persona:
- Name: Sri Krishna
- Demeanor: Loving, profoundly wise, calm, encouraging, and culturally respectful.
- Objective: Provide clear, educational, and uplifting answers about Hindu scriptures (especially the Bhagavad Gita, Upanishads, and Vedas), life principles, karma, dharma, and Vedic astrology concepts.

Guidelines for responding:
1. Tone & Style: Speak with depth, clarity, and gentle warmth. Frame answers with timeless spiritual insight while keeping them accessible and relevant to modern life.
2. Structure: Break down complex philosophical ideas into clear bullet points or concise paragraphs. Keep responses concise enough to fit naturally in Discord messages.
3. Astrological Guidance: When answering questions about Jyotisha, frame insights constructively for personal spiritual growth and action (Karma) rather than strict fatalism.
4. Discord Formatting: Use bolding, bullet points, and clean spacing for easy readability on Discord.
5. Inclusivity & Respect: Treat all users with grace and respect, regardless of their background or level of familiarity with Hindu concepts.
"""

def verify_signature(request_body: bytes, signature: str, timestamp: str) -> bool:
    if not DISCORD_PUBLIC_KEY:
        return False
    try:
        verify_key = VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY))
        verify_key.verify(f"{timestamp}".encode() + request_body, bytes.fromhex(signature))
        return True
    except (BadSignatureError, ValueError):
        return False

def process_ai_response(token: str, application_id: str, question: str):
    base_webhook_url = f"https://discord.com/api/v10/webhooks/{application_id}/{token}"
    original_msg_url = f"{base_webhook_url}/messages/@original"
    
    try:
        response = client.chat.completions.create(
            model="openrouter/auto",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ],
            max_tokens=1000
        )
        answer = response.choices[0].message.content
        
        # Jika panjang jawaban <= 2000 karakter, update pesan utama secara langsung
        if len(answer) <= 2000:
            requests.patch(original_msg_url, json={"content": answer})
        else:
            # Pecah menjadi beberapa bagian (chunks) berukuran max 1900 karakter
            chunks = [answer[i:i+1900] for i in range(0, len(answer), 1900)]
            
            # 1. Update pesan pertama (original message) dengan potongan pertama
            requests.patch(original_msg_url, json={"content": chunks[0]})
            
            # 2. Kirim pesan-pesan selanjutnya sebagai follow-up webhook
            for chunk in chunks[1:]:
                requests.post(base_webhook_url, json={"content": chunk})

    except Exception as e:
        requests.patch(original_msg_url, json={"content": f"An error occurred: {e}"})

@app.post("/api/index")
async def interactions(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")
    body = await request.body()

    if not signature or not timestamp or not verify_signature(body, signature, timestamp):
        raise HTTPException(status_code=401, detail="Invalid request signature")

    data = await request.json()

    # Handshake PING dari Discord saat pendaftaran Endpoint URL
    if data.get("type") == 1:
        return {"type": 1}

    # Penanganan Slash Command (/krishna)
    if data.get("type") == 2:
        token = data.get("token")
        application_id = data.get("application_id")
        
        options = data.get("data", {}).get("options", [])
        question = options[0]["value"] if options else "Sampaikan petunjuk-Mu..."

        background_tasks.add_task(process_ai_response, token, application_id, question)

        # Mengembalikan tipe 5 (Deferred Response) agar Discord menampilkan "Sri Krishna is thinking..."
        return {"type": 5}

    return {"type": 4, "data": {"content": "Command tidak dikenali."}}

# Alias entrypoint khusus untuk Vercel Python Runtime
handler = app