from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client()

interaction = client.interactions.create(
    model="gemini-4-argon",
    input="Explain how ctDNA can help monitor cancer therapy resistance.",
    generation_config={"thinking_level": "medium"},
)

print(interaction.output_text)
