import os
import discord
from discord.ext import commands
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

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

@bot.event
async def on_ready():
    print("Sri Krishna is now online via OpenRouter Auto!")

@bot.command(name="krishna")
async def krishna(ctx, *, question: str):
    async with ctx.typing():
        try:
            # Menggunakan OpenRouter Auto
            response = client.chat.completions.create(
                model="openrouter/auto",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question}
                ],
                max_tokens=1000  # Menikkan limit token agar output tidak dipotong AI
            )
            
            answer = response.choices[0].message.content
            
            # Memecah pesan jika panjangnya melebihi batas 2000 karakter Discord
            if len(answer) > 2000:
                chunks = [answer[i:i+1900] for i in range(0, len(answer), 1900)]
                for chunk in chunks:
                    await ctx.send(chunk)
            else:
                await ctx.send(answer)

        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

bot.run(DISCORD_TOKEN)