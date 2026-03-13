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
# Store todos after first download so we don't re-download every query
_todos_cache = None


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
    Filter todos by userId, compute stats, and return a formatted summary string.
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
    Receive a chat message, validate it, fetch todos, return a formatted reply.
    """
    user_input = body.message.strip()

    # Empty input check
    if not user_input:
        return QueryResponse(
            reply="Looks like you forgot to type something! 😊 Please enter a number between 1 and 10."
        )

    # Must be a whole number
    try:
        user_id = int(user_input)
    except ValueError:
        return QueryResponse(
            reply=f"Oops! \"{user_input}\" doesn't look like a number. 😅\nPlease enter a whole number between 1 and 10."
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