"""
Zevoir Query Chatbot — FastAPI Backend
----------------------------------------
Serves the chat UI and handles userId queries against the JSONPlaceholder API.

Run:
    uvicorn app:app --reload
Then open:
    http://localhost:8000
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import urllib.request
import urllib.error
import json
import ssl

# Fix for SSL certificate issues on some Macs
ssl._create_default_https_context = ssl._create_unverified_context

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Cache ──────────────────────────────────────────────────────────────────────
_todos_cache = None


# ── Chatbot keyword responses ──────────────────────────────────────────────────
CHATBOT_RESPONSES = {
    ("hi", "hello", "hey", "hiya", "howdy"): (
        "Hello! 👋 Welcome to Zevoir Support.\n"
        "How can I assist you today?"
    ),
    ("help", "i need help", "assist", "support", "i need assistance"): (
        "Sure! I'm here to help 😊\n"
        "Please choose one of the options below:\n\n"
        "1️⃣ Account Issues\n"
        "2️⃣ Order Status\n"
        "3️⃣ Technical Support\n"
        "4️⃣ Talk to a Human Agent\n\n"
        "Or type a userId (1-10) to get a todo summary!"
    ),
    ("where is my order", "order status", "track order", "my order"): (
        "I can help with that! 📦\n"
        "Please enter your Order ID to check the latest status."
    ),
    ("i can't login", "cant login", "i cant login", "login issue", "can't log in", "cant log in", "login problem", "forgot password"): (
        "No worries! 🔐\n"
        "You can reset your password using the 'Forgot Password' option.\n"
        "Would you like me to send you the reset link?"
    ),
    ("otp", "i didn't receive otp", "no otp", "resend otp", "didn't get otp"): (
        "Sometimes OTPs take a few seconds to arrive. ⏳\n"
        "Please wait 30 seconds and try again.\n"
        "Would you like me to resend the OTP?"
    ),
    ("services", "tell me about your services", "what do you offer", "what services"): (
        "We offer several services to help businesses grow:\n\n"
        "✅ AI Automation\n"
        "✅ Data Analytics\n"
        "✅ Chatbot Development\n"
        "✅ Dashboard & Reporting\n\n"
        "Would you like more details about any of these?"
    ),
    ("demo", "i want a demo", "book a demo", "schedule demo", "free demo"): (
        "Great! 🚀\n"
        "Please share your name, email, and company name,\n"
        "and our team will schedule a free demo for you."
    ),
    ("human", "talk to a person", "real person", "agent", "speak to someone", "talk to someone"): (
        "Sure 👍\n"
        "I'm connecting you with one of our support specialists.\n"
        "Please wait a moment..."
    ),
    ("thanks", "thank you", "thankyou", "thx", "ty", "thank u"): (
        "You're welcome! 😊\n"
        "If you need anything else, feel free to ask."
    ),
    ("yes", "yeah", "yep", "sure", "ok", "okay", "no", "nope", "nah"): (
        "Got it! 😊\n"
        "If you have any other questions, feel free to ask.\n"
        "Or type a userId from 1 to 10 to get a todo summary!"
    ),
    ("bye", "goodbye", "see you", "see ya", "cya", "take care", "good bye"): (
        "Thank you for visiting! 👋\n"
        "Have a wonderful day."
    ),
}

# Help response used for "contains help" check
HELP_RESPONSE = (
    "Sure! I'm here to help 😊\n"
    "Please choose one of the options below:\n\n"
    "1️⃣ Account Issues\n"
    "2️⃣ Order Status\n"
    "3️⃣ Technical Support\n"
    "4️⃣ Talk to a Human Agent\n\n"
    "Or type a userId (1-10) to get a todo summary!"
)


def check_chatbot_response(user_input: str):
    """
    Check if the user message matches any keyword.
    Also checks if message CONTAINS the word 'help' anywhere.
    Returns a response string if matched, or None if no match.
    """
    text = user_input.lower().strip()

    # Check exact match first
    for keywords, response in CHATBOT_RESPONSES.items():
        if text in keywords:
            return response

    # Check if message CONTAINS the word "help" anywhere
    # e.g. "help me", "can you help", "i need some help with this"
    if "help" in text:
        return HELP_RESPONSE

    return None


def fetch_todos() -> list:
    """
    Download all todos from JSONPlaceholder.
    Caches the result so repeated queries don't hit the network.
    """
    global _todos_cache

    if _todos_cache is not None:
        return _todos_cache

    url = "https://jsonplaceholder.typicode.com/todos"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ZevoirQueryChatbot/1.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            raw = response.read().decode("utf-8")

    except urllib.error.URLError as exc:
        raise ConnectionError(f"Network error: {exc.reason}")

    except Exception as exc:
        raise ConnectionError(f"Request failed: {exc}")

    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("API response was not a JSON array as expected.")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse JSON from API: {exc}")

    _todos_cache = data
    return data


def build_summary(user_id: int) -> str:
    """
    Filter todos by userId, compute stats, return a formatted summary.
    """
    todos = fetch_todos()
    user_todos = [t for t in todos if t.get("userId") == user_id]
    total = len(user_todos)

    if total == 0:
        return (
            f"Hmm, I couldn't find any todos for userId {user_id}. 🤔\n"
            "The valid userIds are 1 to 10. Give one of those a try!"
        )

    completed = sum(1 for t in user_todos if t.get("completed") is True)
    pending   = total - completed
    pct       = (completed / total) * 100

    first_five = "\n".join(
        f"  • {t.get('title', '(no title)')}"
        for t in user_todos[:5]
    )

    return (
        f"Here's the summary for userId {user_id}! 🎉\n\n"
        f"📋 Total todos:   {total}\n"
        f"✅ Completed:     {completed}\n"
        f"⏳ Pending:       {pending}\n"
        f"📊 Completion:    {pct:.2f}%\n\n"
        f"First 5 titles:\n{first_five}"
    )


# ── Schemas ────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    message: str

class QueryResponse(BaseModel):
    reply: str


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    """Serve the chat UI."""
    return FileResponse("static/index.html")


@app.post("/query", response_model=QueryResponse)
async def query(body: QueryRequest):
    """
    Receive a chat message, check for keywords first,
    then validate as userId and return a formatted reply.
    """
    user_input = body.message.strip()

    # Empty input check
    if not user_input:
        return QueryResponse(
            reply="Looks like you forgot to type something! 😊 Please enter a number between 1 and 10."
        )

    # Check keyword responses first (hi, bye, help, etc.)
    chatbot_reply = check_chatbot_response(user_input)
    if chatbot_reply:
        return QueryResponse(reply=chatbot_reply)

    # Must be a whole number
    try:
        user_id = int(user_input)
    except ValueError:
        return QueryResponse(
            reply=f'Oops! "{user_input}" does not look like a number. 😅\nPlease enter a whole number between 1 and 10.'
        )

    # Must be between 1 and 10
    if user_id < 1 or user_id > 10:
        return QueryResponse(
            reply=f"Hmm, {user_id} is out of range! 🙈\nThe valid userIds are 1 to 10. Please try one of those!"
        )

    # Fetch and compute
    try:
        reply = build_summary(user_id)
    except ConnectionError as exc:
        reply = (
            "Oh no! I couldn't reach the API right now. 😟\n"
            "Please check your internet connection and try again!\n\n"
            f"Details: {exc}"
        )
    except ValueError as exc:
        reply = (
            "Something unexpected came back from the API. 🤔\n"
            "Please try again in a moment!\n\n"
            f"Details: {exc}"
        )
    except Exception as exc:
        reply = f"Oops! Something went wrong on my end. 😬 Please try again!\n\nDetails: {exc}"

    return QueryResponse(reply=reply)


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Server liveness check."""
    return {
        "status": "ok",
        "cache_loaded": _todos_cache is not None,
        "cached_todos": len(_todos_cache) if _todos_cache else 0,
    }
