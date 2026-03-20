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


# ── Text normaliser ────────────────────────────────────────────────────────────
# Fixes common typos, shortcuts and informal spellings before matching keywords.
SPELLING_FIXES = {
    # shorthand / slang
    "u":          "you",
    "ur":         "your",
    "r":          "are",
    "wanna":      "want to",
    "gonna":      "going to",
    "gotta":      "got to",
    "kinda":      "kind of",
    "lol":        "haha",
    "ngl":        "not going to lie",
    "tbh":        "to be honest",
    "imo":        "in my opinion",
    "idk":        "i don't know",
    "omg":        "oh my god",
    "brb":        "be right back",
    "btw":        "by the way",
    # common typos
    "buisness":   "business",
    "bussiness":  "business",
    "busines":    "business",
    "busness":    "business",
    "artifical":  "artificial",
    "inteligence":"intelligence",
    "intellegence":"intelligence",
    "automaton":  "automation",
    "automatiom": "automation",
    "analyitics": "analytics",
    "analatics":  "analytics",
    "analitics":  "analytics",
    "developement":"development",
    "developmnt": "development",
    "websit":     "website",
    "webiste":    "website",
    "sevices":    "services",
    "servises":   "services",
    "servces":    "services",
    "intrested":  "interested",
    "intersted":  "interested",
    "securtiy":   "security",
    "securty":    "security",
    "clod":       "cloud",
    "coud":       "cloud",
    "thnks":      "thanks",
    "thnk":       "thanks",
    "thanx":      "thanks",
    "byee":       "bye",
    "byeee":      "bye",
    "bbye":       "bye",
    "gooodbye":   "goodbye",
    "helo":       "hello",
    "hallo":      "hello",
    "heey":       "hey",
    "heyy":       "hey",
    "heyyy":      "hey",
}

def normalize(text: str) -> str:
    """
    Lowercase, strip, then fix common typos and shortcuts word by word.
    Also collapses repeated characters e.g. 'hmmm' -> 'hmm'.
    """
    text = text.lower().strip()
    # Fix word-by-word
    words = text.split()
    words = [SPELLING_FIXES.get(w, w) for w in words]
    return " ".join(words)


# ── Chatbot keyword responses ──────────────────────────────────────────────────
CHATBOT_RESPONSES = {
    ("hi", "hello", "hey", "hiya", "howdy", "hai", "hii", "hiii"): (
        "Hey there! 👋 Welcome to Zevoir Technologies.\n"
        "What brings you here today?"
    ),
    ("help", "i need help", "assist", "support", "i need assistance", "can you help", "i need some help"): (
        "Sure! I'm here to help 😊\n"
        "Please choose one of the options below:\n\n"
        "1️⃣ Account Issues\n"
        "2️⃣ Order Status\n"
        "3️⃣ Technical Support\n"
        "4️⃣ Talk to a Human Agent\n\n"
        "Or type a userId (1-10) to get a todo summary!"
    ),
    ("i need help with my business", "help with my business", "my business", "business", "my company", "for my business"): (
        "That's great! 😊 Are you looking for a website, AI solution, or something else?"
    ),
    ("ai", "maybe ai", "ai solution", "artificial intelligence", "i want ai", "we need ai", "i need ai"): (
        "Awesome choice 🚀 AI can really boost efficiency.\n"
        "Are you thinking about automation, chatbots, or data insights?"
    ),
    ("automation", "chatbot automation", "data insights", "ai automation", "i want automation"): (
        "Great choice! 💡 We've helped many businesses save time and costs with AI automation.\n"
        "Would you like to see how it works for your industry?"
    ),
    ("where is my order", "order status", "track order", "my order", "order update"): (
        "I can help with that! 📦\n"
        "Please enter your Order ID to check the latest status."
    ),
    ("i can't login", "cant login", "i cant login", "login issue", "can't log in", "cant log in", "login problem", "forgot password", "cant sign in", "can't sign in"): (
        "No worries! 🔐\n"
        "You can reset your password using the 'Forgot Password' option.\n"
        "Would you like me to send you the reset link?"
    ),
    ("otp", "i didn't receive otp", "no otp", "resend otp", "didn't get otp", "otp not received"): (
        "Sometimes OTPs take a few seconds to arrive. ⏳\n"
        "Please wait 30 seconds and try again.\n"
        "Would you like me to resend the OTP?"
    ),
    ("services", "what services do you offer", "tell me about your services", "what do you offer", "what services", "your services", "list services"): (
        "We help businesses grow with:\n\n"
        "🤖 AI & Automation\n"
        "📊 Data Analytics\n"
        "☁️ Cloud Services\n"
        "💻 Web & Mobile Development\n\n"
        "What are you most interested in?"
    ),
    ("web development", "web dev", "website development", "website", "build website", "make a website", "i need a website"): (
        "Nice 👍 Are you planning a new website or upgrading an existing one?"
    ),
    ("new website", "build a website", "create a website", "i want a new website"): (
        "Perfect! We can design and build a fast, modern site for you.\n"
        "Would you like a quick consultation?"
    ),
    ("can you build a chatbot", "build a chatbot", "chatbot", "create a chatbot", "i need a chatbot", "build me a chatbot"): (
        "Absolutely! 🤖 We create smart chatbots for customer support, automation, and sales."
    ),
    ("will it work like you", "like you", "work like you", "similar to you", "will it work like this"): (
        "Pretty close 😄 It can answer questions, guide users, and even capture leads."
    ),
    ("sounds good", "sounds great", "that sounds good", "nice", "great", "perfect", "awesome", "wow"): (
        "Great! Want me to connect you with our AI team for a demo?"
    ),
    ("i have a lot of data", "a lot of data", "data but no insights", "no insights", "raw data", "we have data", "tons of data"): (
        "That's where we come in 📊 We turn raw data into clear, actionable insights."
    ),
    ("how", "how?", "how do you do it", "how does it work", "how does this work"): (
        "We build dashboards, reports, and predictive models so you can make smarter decisions."
    ),
    ("interesting", "that's interesting", "thats interesting", "cool", "i see", "ok i see", "makes sense"): (
        "Want to see a sample dashboard or discuss your use case?"
    ),
    ("data analytics", "analytics", "data analysis", "data"): (
        "📊 We turn raw data into clear, actionable insights.\n"
        "We build dashboards, reports, and predictive models so you can make smarter decisions.\n\n"
        "Want to see a sample dashboard?"
    ),
    ("do you provide cloud services", "cloud services", "cloud", "aws", "azure", "google cloud", "cloud hosting", "i need cloud"): (
        "Yes ☁️ We help businesses move to cloud platforms like AWS, Azure, and Google Cloud."
    ),
    ("is it secure", "secure", "security", "is it safe", "safe", "how secure is it", "data security"): (
        "Absolutely 🔐 We focus on security, scalability, and reliability."
    ),
    ("i'm interested", "im interested", "i am interested", "interested", "i want to know more", "tell me more"): (
        "That's great to hear! 😊 Can I have your name and email so our team can reach out?"
    ),
    ("i'm just exploring", "im just exploring", "just exploring", "exploring", "just looking", "just browsing", "i'm browsing"): (
        "No problem at all 😊 Take your time. I'm here if you need anything!"
    ),
    ("what makes you different", "makes you different", "why choose you", "why zevoir", "what's different", "why should i choose you"): (
        "Great question! 🚀 We focus on smart solutions, fast delivery, and real business impact."
    ),
    ("demo", "i want a demo", "book a demo", "schedule demo", "free demo", "can i see a demo", "show me a demo"): (
        "Great! 🚀\n"
        "Please share your name, email, and company name,\n"
        "and our team will schedule a free demo for you."
    ),
    ("human", "talk to a person", "real person", "agent", "speak to someone", "talk to someone", "connect me to a human", "i want to talk to a person"): (
        "Sure 👍\n"
        "I'm connecting you with one of our support specialists.\n"
        "Please wait a moment..."
    ),
    ("thanks", "thank you", "thankyou", "thx", "ty", "thank u", "many thanks", "thanks a lot", "thank you so much"): (
        "You're welcome! 😊\n"
        "If you need anything else, just ask.\n"
        "Let's build something amazing together!"
    ),
    ("yes", "yeah", "yep", "yup", "ok", "okay", "no", "nope", "nah", "alright", "sure", "got it", "understood"): (
        "Got it! 😊\n"
        "If you have any other questions, feel free to ask.\n"
        "Or type a userId from 1 to 10 to get a todo summary!"
    ),
    ("bye", "goodbye", "ok bye", "okay bye", "see you", "see ya", "cya", "take care", "good bye", "bbye", "tata", "later", "talk later"): (
        "Thank you for visiting! 👋\n"
        "Have a wonderful day. Let's build something amazing together!"
    ),
    ("hmm", "hm", "hmmm", "hmmmm", "umm", "uhm", "uh", "uhh", "well", "let me think"): (
        "Take your time! 🤔 No rush at all.\n"
        "Whenever you're ready, I'm here to help.\n"
        "You can ask about our services, AI, cloud, or anything else!"
    ),
}

# Help response for "contains help" check
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
    Normalise input (fix typos/shortcuts), then match against keywords.
    Also catches any message that CONTAINS the word 'help'.
    Returns a response string or None.
    """
    text = normalize(user_input)

    # Exact / phrase match
    for keywords, response in CHATBOT_RESPONSES.items():
        if text in keywords:
            return response

    # Partial keyword match — catches "i need ai help" or "ok bye then" etc.
    for keywords, response in CHATBOT_RESPONSES.items():
        for kw in keywords:
            if kw in text:
                return response

    # Fallback: message contains "help" anywhere
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
