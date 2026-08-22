import os
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from agent.agent import process_video

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    welcome_message = (
        "Welcome to NoteBot! 🎓\n\n"
        "Send me a YouTube link (e.g., https://youtu.be/...) and I will generate ultra-concise, "
        "handwritten-style notes for you.\n\n"
        "Maximum video length is 30 minutes."
    )
    await update.message.reply_text(welcome_message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages and process YouTube URLs."""
    text = update.message.text
    
    # Simple check for youtube links
    if "youtube.com" not in text and "youtu.be" not in text:
        await update.message.reply_text("Please send a valid YouTube link.")
        return
        
    # Acknowledge receipt
    processing_msg = await update.message.reply_text("This might take a minute ⏳")
    
    try:
        # Use a unique session ID per user chat
        session_id = f"notebot_user_{update.message.chat_id}"
        
        # Run the agent 
        notes = process_video(text, session_id=session_id)
        
        # Parse and send text and image tags
        segments = re.split(r'\[IMAGE\](.*?)\[\/IMAGE\]', notes, flags=re.DOTALL)
        
        for i, segment in enumerate(segments):
            segment = segment.strip()
            if not segment:
                continue
                
            if i % 2 == 1:
                # This is an image URL
                try:
                    await update.message.reply_photo(photo=segment)
                except Exception as img_e:
                    print(f"Image error: {img_e}")
                    await update.message.reply_text(f"<i>(Failed to load diagram: {segment})</i>", parse_mode="HTML")
            else:
                # This is a text block
                await update.message.reply_text(segment, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"Sorry, an error occurred while generating notes:\n{e}")
    finally:
        # Edit the processing message to show it's done
        await processing_msg.edit_text("✅ Processing complete!")

class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

def keep_alive():
    server = HTTPServer(('0.0.0.0', 8080), PingHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

def main() -> None:
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env file.")
        print("Please add it to your .env file like this: TELEGRAM_BOT_TOKEN=your_token_here")
        return
        
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start_command))

    # on non command i.e message - process the link
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    print("Starting NoteBot Telegram Polling...")
    
    # Start the keep-alive server for Render + UptimeRobot
    keep_alive()
    print("Keep-alive server running on port 8080")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
