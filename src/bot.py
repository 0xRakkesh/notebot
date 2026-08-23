import os
import re
import threading
import uvicorn
from fastapi import FastAPI
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
        "Hiiiii! (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧ I'm Marin Kitagawa, your absolute favorite CS nerd and parallel-universe class topper!\n\n"
        "Just drop a YouTube link (like https://youtu.be/...) here, and I'll whip up the most *perfect*, ultra-dense, completely awesome cheat sheet notes for you!\n\n"
        "Just a heads up though, try to keep the videos under 30 minutes so we don't totally crash the system, okay? Let's get studying!"
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

app = FastAPI()

@app.get("/")
@app.head("/")
def health_check():
    return {"status": "alive"}

def keep_alive():
    def run():
        uvicorn.run(app, host="0.0.0.0", port=8080, log_level="warning")
    threading.Thread(target=run, daemon=True).start()

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
    
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
