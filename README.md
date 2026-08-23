# NoteBot

NoteBot is an AI-powered Telegram bot that acts as an expert Computer Science tutor. It extracts core concepts from YouTube videos (using their transcripts) and transforms them into ultra-concise, highly readable cheat sheets perfectly formatted for Telegram.

## Features
- **YouTube Transcript Extraction:** Automatically fetches and processes transcripts from YouTube URLs.
- **AI-Powered Summarization:** Uses `langchain-groq` (with models like `openai/gpt-oss-120b`) via LangGraph to generate dense, skimmable cheat sheets.
- **Technical Focus:** Designed specifically for OS, DBMS, Machine Learning, Image Processing, and Web Tech.
- **Diagram Search:** Integrates the `TavilyClient` to automatically search for and embed relevant technical diagrams (e.g., OS Deadlock RAG diagrams) directly into your notes.
- **Telegram Native:** Outputs structured HTML perfectly tailored for Telegram clients, avoiding markdown compatibility issues.

## Tech Stack
- **Framework:** `langchain`, `langgraph`
- **LLM:** Groq API (`langchain-groq`)
- **Search Engine:** Tavily API
- **Transcripts:** `youtube-transcript-api` (historically `yt-dlp` depending on the active commit)
- **Bot Interface:** `python-telegram-bot`
- **Dependency Management:** `uv`

## Setup

1. **Clone the repository**
2. **Install dependencies using `uv`:**
   ```bash
   uv pip install -r requirements.txt
   # OR
   uv sync
   ```
3. **Environment Variables:**
   Create a `.env` file in the root directory with the following keys:
   ```env
   GROQ_API_KEY=your_groq_api_key
   TAVILY_API_KEY=your_tavily_api_key
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   # Optional: YOUTUBE_PROXY=http://user:pass@ip:port
   ```

## Usage

To run the Telegram bot server:
```bash
uv run src/bot.py
```

To run the agent locally via CLI to test a video:
```bash
uv run src/agent/agent.py "https://www.youtube.com/watch?v=..."
```
