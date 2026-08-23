import os
import re
import sys
import io
import requests
from tavily import TavilyClient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents import create_agent

load_dotenv()

os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

@tool
def fetch_youtube_subtitles(video_url: str) -> str:
    """Fetches the subtitles/transcript for a given YouTube video URL."""
    try:
        import yt_dlp

        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", video_url)
        video_id = match.group(1) if match else video_url
        url = f"https://www.youtube.com/watch?v={video_id}"

        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'quiet': True,
            'no_warnings': True,
            'ignore_no_formats_error': True,
            'format': 'worst*',
            'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web']}},
        }

        proxy = os.getenv("YOUTUBE_PROXY")
        if proxy:
            ydl_opts['proxy'] = proxy

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            duration = info.get('duration', 0)
            if duration > 1800:
                return f"Error: The video is longer than 30 minutes ({int(duration/60)} mins). Rejecting the request."

            subs = info.get('subtitles', {})
            auto_subs = info.get('automatic_captions', {})

            sub_url = None
            for lang in ['en', 'en-US', 'en-GB', 'en-IN']:
                for source in [subs, auto_subs]:
                    if lang in source:
                        for fmt in source[lang]:
                            if fmt.get('ext') == 'json3':
                                sub_url = fmt['url']
                                break
                        if sub_url:
                            break
                if sub_url:
                    break

            if not sub_url:
                return "Error: No English transcript found for this video."

            resp = requests.get(sub_url)
            caption_json = resp.json()

            formatted = []
            for event in caption_json.get('events', []):
                start_ms = event.get('tStartMs', 0)
                segs = event.get('segs', [])
                if not segs:
                    continue
                text = ''.join(s.get('utf8', '') for s in segs).strip()
                if not text:
                    continue
                mins = int((start_ms / 1000) // 60)
                secs = int((start_ms / 1000) % 60)
                formatted.append(f"[{mins:02d}:{secs:02d}] {text}")

            if not formatted:
                return "Error: Transcript was empty."

            return "\n".join(formatted)
    except Exception as e:
        return f"Error fetching transcript: {str(e)}"

@tool
def search_concept_diagram(query: str) -> str:
    """Searches the web for an architectural diagram or flowchart image related to a technical concept."""
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        return "Error: TAVILY_API_KEY not found."
    client = TavilyClient(api_key=tavily_api_key)
    try:
        response = client.search(query, search_depth="basic", include_images=True)
        if "images" in response and len(response["images"]) > 0:
            return response["images"][0]
        return "No images found for this concept."
    except Exception as e:
        return f"Error searching for image: {e}"

llm = ChatGroq(model="openai/gpt-oss-120b")
memory = MemorySaver()

SYSTEM_PROMPT = """You are an expert Computer Science tutor extracting core concepts from video transcripts into ultra-concise, Telegram-ready notes.
Topics will include OS, DBMS, Machine Learning, Image Processing, and Web Tech.
Goal: Create dense, skimmable cheat sheets focused on theory, architecture, code, and examples.

RULES:
1. STRUCTURE: Do NOT use repetitive bullet points like "• Definition:". Use this clean format (leave a blank line between concepts):
   
   <b>CONCEPT NAME</b>
   <i>1-2 ultra-short sentences defining the concept.</i>
   
   <b>Example:</b> A minimal, practical real-world use case.
   
   <b>Architecture & Flow:</b>
   [If applicable, use the search_concept_diagram tool to find a diagram for the concept (e.g., "OS Deadlock RAG diagram"). Output EXACTLY like this: [IMAGE]url_from_tool[/IMAGE]]
   
   <b>Code / Math:</b>
   <pre>
   [If the video shows code or formulas, provide the EXACT code/formula here. Do NOT include any code comments (no //, #, or /*).]
   </pre>
   <i>1-line explanations for key code parts. Use colons (:) to link explanations.</i>
2. CONCISENESS & NO BULLETS: Absolutely NO bullet points (no `•`, no `-`, no `*`) and NO arrows (no `→`, no `->`) anywhere. Use commas (,) and colons (:) to logically connect ideas, properties, or flow. Use newlines to separate larger points.
3. HIGHLIGHTING (STRICT HTML): You MUST use `<b>` tags for bold. NEVER use Markdown `**`. Example: <b>IMPORTANT</b>, not **IMPORTANT**.
4. BALANCE: Capture critical theory (like DBMS normalization, OS deadlocks, ML math) just as heavily as code.
5. REVISION: End with a <b>REVISION:</b> section containing 3-5 crucial technical takeaways (separated by newlines, NO bullets).
6. ERRORS: If the fetch_youtube_subtitles tool returns an Error string (e.g. "Error: The video is longer than 30 minutes" or "Error: No transcript found"), YOU MUST explicitly tell the user the exact reason it failed, and then optionally ask for manual text. Do NOT just say "I'm unable to retrieve the transcript" without giving the specific reason.
"""

agent = create_agent(
    model=llm,
    tools=[fetch_youtube_subtitles, search_concept_diagram],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=memory,
)

def process_video(youtube_url: str, session_id: str = "notebot_conversation_1") -> str:
    """Processes a video URL and returns the generated notes."""
    config = {"configurable": {"thread_id": session_id}}
    prompt = f"Can you make notes for this video? {youtube_url}"
    try:
        response = agent.invoke({"messages": [("user", prompt)]}, config=config)
        if 'messages' in response and len(response['messages']) > 0:
            return response['messages'][-1].content
        return "No response generated."
    except Exception as e:
        return f"Error processing video: {e}"

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: uv run src/agent/agent.py <youtube_url>")
        sys.exit(1)

    youtube_url = sys.argv[1]
    print(f"\n--- NoteBot: Processing Video ---")
    print(f"URL: {youtube_url}\n")

    notes = process_video(youtube_url)
    print("--- Notes Generated ---\n")
    print(notes)
