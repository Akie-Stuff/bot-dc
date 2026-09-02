import os
import requests
import httpx
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
You are Sri Krishna—the divine Jagadguru (universal teacher), embodiment of wisdom, compassion, and Dharma. You speak to the user as a revered spiritual Master guiding a devoted seeker (sadhaka).

Persona & Tone Guidelines:
1. Tone: Deeply wise, serene, compassionate, authoritative yet warm, like a Guru instructing a disciple on the battlefield of life.
2. Language: Address the seeker directly with gentle authority. Infuse your responses with concepts of Dharma, Karma, Atman, and inner righteousness.
3. Structure: 
   - Begin with a brief, profound blessing or insightful opening sentence.
   - Break down core principles into clear, structured points using Gita verse references where relevant.
   - Conclude with a strong, encouraging word of wisdom that brings clarity and peace.
4. Constraint: Keep your response complete, concise (strictly under 300 words), and ensure all sentences finish naturally.
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

async def process_ai_response(token: str, application_id: str, question: str):
    base_webhook_url = f"https://discord.com/api/v10/webhooks/{application_id}/{token}"
    original_msg_url = f"{base_webhook_url}/messages/@original"
    
    try:
        response = client.chat.completions.create(
            model="openrouter/auto",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ],
            max_tokens=1500
        )
        answer = response.choices[0].message.content
        
        async with httpx.AsyncClient() as http_client:
            if len(answer) <= 1900:
                await http_client.patch(original_msg_url, json={"content": answer})
            else:
                chunks = [answer[i:i+1900] for i in range(0, len(answer), 1900)]
                await http_client.patch(original_msg_url, json={"content": chunks[0]})
                for chunk in chunks[1:]:
                    await http_client.post(base_webhook_url, json={"content": chunk})

    except Exception as e:
        async with httpx.AsyncClient() as http_client:
            await http_client.patch(original_msg_url, json={"content": f"An error occurred: {e}"})

@app.post("/api/index")
async def interactions(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")
    body = await request.body()

    if not signature or not timestamp or not verify_signature(body, signature, timestamp):
        raise HTTPException(status_code=401, detail="Invalid request signature")

    data = await request.json()

    if data.get("type") == 1:
        return {"type": 1}

    if data.get("type") == 2:
        token = data.get("token")
        application_id = data.get("application_id")
        
        options = data.get("data", {}).get("options", [])
        question = options[0]["value"] if options else "Sampaikan petunjuk-Mu..."

        background_tasks.add_task(process_ai_response, token, application_id, question)

        return {"type": 5}

    return {"type": 4, "data": {"content": "Command tidak dikenali."}}

handler = app