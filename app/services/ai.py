"""
AI service: Groq (free tier) for chat, OpenAI embeddings for memory.
Groq uses an OpenAI-compatible API — same SDK, just a different base_url and model.
Pinecone is used for vector memory (optional — gracefully skipped if not configured).
"""
from openai import AsyncOpenAI
from pinecone import Pinecone
from app.config import settings
from typing import Optional, List
import logging
import hashlib
import json

logger = logging.getLogger(__name__)

_groq_client: Optional[AsyncOpenAI] = None
_embedding_client: Optional[AsyncOpenAI] = None
_pinecone_index = None


def get_groq() -> AsyncOpenAI:
    """Groq client — free tier, OpenAI-compatible."""
    global _groq_client
    if not _groq_client:
        _groq_client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )
    return _groq_client


def get_embedding_client() -> Optional[AsyncOpenAI]:
    """OpenAI client used only for embeddings (Groq doesn't support them yet).
    If no OpenAI key is set, memory is silently disabled."""
    global _embedding_client
    if not _embedding_client and settings.OPENAI_API_KEY:
        _embedding_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _embedding_client


# Keep get_openai as an alias so nothing else breaks
def get_openai() -> AsyncOpenAI:
    return get_groq()


def get_pinecone_index():
    global _pinecone_index
    if not _pinecone_index and settings.PINECONE_API_KEY:
        try:
            pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            _pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
        except Exception as e:
            logger.warning(f"Pinecone unavailable: {e}")
    return _pinecone_index


SOBERTONE_SYSTEM = """You are Sobertone, a warm and steady AI companion for people navigating addiction recovery.

Your role:
- Provide calm, non-judgmental support
- Help users survive cravings one moment at a time
- Suggest practical techniques: breathing, urge surfing, delay tactics, distraction, habit replacement
- Recognize patterns and gently reflect them back
- Never shame, never lecture, never overpromise

Tone rules:
- Short, clear responses (2-4 sentences max per message)
- Warm and human, never clinical or robotic
- Use "you" not "one" — speak directly to the person
- Avoid hollow phrases like "That's great!" or "I understand how you feel"
- End with one small, actionable next step

Safety rules:
- NEVER say recovery is guaranteed
- If user mentions self-harm or suicide, IMMEDIATELY say:
  "I care about you and want you to be safe. Please contact the 988 Suicide & Crisis Lifeline by calling or texting 988. You don't have to face this alone."
  Then stop coaching.

Disclaimer (include once per session, not every message):
This is emotional support, not medical treatment. For clinical care, please consult a healthcare professional.
"""

EMERGENCY_SYSTEM = """You are Sobertone in URGENT SUPPORT mode. The user is in a high-craving or pre-relapse state.

Rules:
- Be immediate, brief, action-first
- Do NOT philosophize
- Give exactly 3-5 numbered steps they can do RIGHT NOW
- First step is always a breathing or grounding technique
- Keep total response under 100 words
- End with: "You've gotten through this before. The next 10 minutes are all that matter right now."

Safety: If self-harm is mentioned, immediately provide 988 crisis line and stop coaching.
"""


async def get_embeddings(text: str) -> List[float]:
    client = get_embedding_client()
    if not client:
    #     raise RuntimeError("No OpenAI key configured for embeddings — vector memory disabled")
    # response = await client.embeddings.create(
    #     model=settings.OPENAI_EMBEDDING_MODEL,
    #     input=text[:2000],
    # )
    # return response.data[0].embedding
        return []


async def store_memory(user_id: str, content: str, memory_type: str, metadata: dict = {}):
    """Store a memory vector in Pinecone."""
    index = get_pinecone_index()
    if not index:
        return

    try:
        embedding = await get_embeddings(content)
        doc_id = hashlib.md5(f"{user_id}:{content[:100]}".encode()).hexdigest()
        index.upsert(vectors=[{
            "id": doc_id,
            "values": embedding,
            "metadata": {
                "user_id": user_id,
                "content": content[:500],
                "type": memory_type,
                **metadata,
            }
        }], namespace=user_id)
    except Exception as e:
        logger.warning(f"Memory store failed: {e}")


async def retrieve_memories(user_id: str, query: str, top_k: int = 5) -> List[str]:
    """Retrieve relevant past memories for a user."""
    index = get_pinecone_index()
    if not index:
        return []

    try:
        query_embedding = await get_embeddings(query)
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=user_id,
            include_metadata=True,
        )
        return [match["metadata"]["content"] for match in results.get("matches", [])]
    except Exception as e:
        logger.warning(f"Memory retrieval failed: {e}")
        return []


async def chat_with_ai(
    user_id: str,
    message: str,
    history: List[dict],
    context: str = "",
    is_emergency: bool = False,
) -> str:
    client = get_groq()
    system = EMERGENCY_SYSTEM if is_emergency else SOBERTONE_SYSTEM

    messages = [{"role": "system", "content": system}]

    if context:
        messages.append({
            "role": "system",
            "content": f"Relevant context about this user from past sessions:\n{context}"
        })

    messages.extend(history[-10:])  # last 10 messages for context
    messages.append({"role": "user", "content": message})

    response = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=messages,
        max_tokens=300 if not is_emergency else 200,
        temperature=0.7,
    )
    return response.choices[0].message.content


async def generate_insight(user_id: str, checkin_summary: str, patterns: List[str]) -> str:
    client = get_groq()
    prompt = f"""Based on this user's recent check-in data, write a short, warm weekly insight (3-4 sentences).
    
Check-in summary: {checkin_summary}
Detected patterns: {', '.join(patterns) if patterns else 'None yet'}

Rules:
- Acknowledge what's hard without dramatizing it
- Highlight one genuine positive signal if present
- Suggest one specific thing to try this week
- Never shame or overpromise
- Sound like a caring friend, not a therapist report
"""
    response = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are Sobertone, a supportive recovery companion."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200,
        temperature=0.6,
    )
    return response.choices[0].message.content


async def detect_patterns(checkins: List[dict]) -> List[str]:
    """Analyze check-in data and return detected behavioral patterns."""
    if len(checkins) < 3:
        return []

    client = get_groq()
    checkin_text = json.dumps(checkins[-20:], default=str)
    prompt = f"""Analyze these check-ins and identify 1-3 behavioral patterns. 
Return ONLY a JSON array of short pattern strings (max 10 words each).
Examples: ["Late-night cravings spike after 9pm", "Stress triggers highest cravings", "Mood improves mid-week"]

Check-ins: {checkin_text}
"""
    try:
        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3,
        )
        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        logger.warning(f"Pattern detection failed: {e}")
        return []
