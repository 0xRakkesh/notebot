import os
import re
import threading
import uvicorn
import time
from fastapi import FastAPI
from dotenv import load_dotenv
from telegram import Update
from telegram.error import Conflict
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from agent.agent import process_video, process_document

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    welcome_message = (
        "Hiiiii! (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧ I'm Marin Kitagawa, your absolute favorite CS nerd and parallel-universe class topper!\n\n"
        "Just drop a YouTube link (like https://youtu.be/...) here, and I'll whip up the most *perfect*, ultra-dense, completely awesome cheat sheet notes for you!\n\n"
        "Just a heads up though, try to keep the videos under 1 hour so we don't totally crash the system, okay? Let's get studying!"
    )
    await update.message.reply_text(welcome_message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages and process YouTube URLs."""
    text = update.message.text
    import telegram.error
    
    # Simple check for youtube links
    if "youtube.com" not in text and "youtu.be" not in text:
        await update.message.reply_text("Please send a valid YouTube link.")
        return
        
    # Acknowledge receipt
    processing_msg = await update.message.reply_text("This might take a few minutes for longer videos! ⏳")
    
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
                try:
                    await update.message.reply_text(segment, parse_mode="HTML")
                except telegram.error.BadRequest as e:
                    if "Can't parse entities" in str(e):
                        # Fallback to sending raw text if HTML is malformed
                        print(f"HTML Parse error caught: {e}. Falling back to raw text.")
                        await update.message.reply_text(
                            "Here is a section of notes (HTML formatting disabled due to parse error):\n\n" + segment
                        )
                    else:
                        raise e
    except Exception as e:
        await update.message.reply_text(f"Sorry, an error occurred while generating notes:\n{e}")
    finally:
        # Edit the processing message to show it's done
        await processing_msg.edit_text("✨ Processing complete!")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming documents (PDF, PPT)."""
    document = update.message.document
    if not document:
        return
        
    file_name = document.file_name.lower() if document.file_name else ""
    if not (file_name.endswith('.pdf') or file_name.endswith('.ppt') or file_name.endswith('.pptx')):
        await update.message.reply_text("Please send a valid PDF or PowerPoint (.pptx) file.")
        return
        
    processing_msg = await update.message.reply_text("Downloading and processing your document... This might take a minute! ⏳")
    
    try:
        # Download the file
        file = await context.bot.get_file(document.file_id)
        
        # Create a temporary file path
        temp_file_path = f"temp_{document.file_id}_{file_name}"
        await file.download_to_drive(temp_file_path)
        
        # Use a unique session ID per user chat
        session_id = f"notebot_user_{update.message.chat_id}"
        
        # Process the document
        notes = process_document(temp_file_path, session_id=session_id)
        
        # Clean up the file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        # Parse and send text and image tags
        import telegram.error
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
                try:
                    await update.message.reply_text(segment, parse_mode="HTML")
                except telegram.error.BadRequest as e:
                    if "Can't parse entities" in str(e):
                        # Fallback to sending raw text if HTML is malformed
                        print(f"HTML Parse error caught: {e}. Falling back to raw text.")
                        await update.message.reply_text(
                            "Here is a section of notes (HTML formatting disabled due to parse error):\n\n" + segment
                        )
                    else:
                        raise e
    except Exception as e:
        await update.message.reply_text(f"Sorry, an error occurred while generating notes:\n{e}")
    finally:
        # Edit the processing message to show it's done
        await processing_msg.edit_text("✨ Processing complete!")

app = FastAPI()

@app.get("/")
@app.head("/")
def health_check():
    return {"status": "alive"}

def keep_alive():
    def run():
        port = int(os.getenv("PORT", 8080))
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
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
    
    # Handle document uploads (PDF/PPT)
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Run the bot until the user presses Ctrl-C
    print("Starting NoteBot Telegram Polling...")
    
    # Start the keep-alive server for Render + UptimeRobot
    keep_alive()
    print(f"Keep-alive server running on port {os.getenv('PORT', 8080)}")
    
    max_retries = 15
    for i in range(max_retries):
        try:
            application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
            break
        except Conflict:
            print(f"Conflict error: Old instance still running. Retrying in 5s... ({i+1}/{max_retries})")
            time.sleep(5)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
