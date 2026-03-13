# TodoBot — Chatbot-Style Todo Summary App

A chatbot interface where you type a userId and the bot replies with
a todo summary fetched from the JSONPlaceholder API.

Built with FastAPI (Python backend) and HTML/CSS/JavaScript (frontend).

## Requirements

- Python 3.9 or newer
- FastAPI
- Uvicorn

## Setup & Run

### Step 1 — Install the dependencies

Open your terminal and run:

pip install fastapi uvicorn

### Step 2 — Start the server

-- Also get info where file downloaded like this:- /Users/venkataumakantkodali/Downloads/todobot
then run cd /Users/venkataumakantkodali/Downloads/todobot

cd todobot
uvicorn app:app --reload

### Step 3 — Open the app

Open your browser and go to:

http://localhost:8000

Note: If port 8000 is already in use, run this instead:

    uvicorn app:app --reload --port 8080

Then open http://localhost:8080


## How to Use

- Type a number between 1 and 10 (e.g. 1) and press Enter or click SEND
- The bot will reply with a todo summary for that userId
- Type abc or hello to see the validation error message
- Type 0 or 999 to see the out of range message
- Click the Clear button to reset the chat


## Project Structure

todobot/
├── app.py            → FastAPI backend (fetching, logic, routes)
├── static/
│   └── index.html    → Chat UI (HTML + CSS + JavaScript)
└── README.md


## API Endpoints

| Method | Path      | Description                        |
|--------|-----------|------------------------------------|
| GET    | /         | Serves the chat UI                 |
| POST   | /query    | Accepts {"message":"1"}, returns reply |
| GET    | /health   | Server status and cache info       |


## Features

- Chat style UI with user and bot message history
- Animated loading dots while fetching
- Input validation — empty, non-integer, and out of range inputs handled
- API error handling — network failures handled gracefully
- Response caching — todos downloaded once per session
- Clear chat button
- Works across multiple queries in one session