import csv
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import PollType
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Configuration - APNA TOKEN YAHAN DALEN
BOT_TOKEN = "8319497957:AAF5PAt9fVnOq07PLTA6JsSlFCsdkH1NMBg"
ADMIN_ID = 8122180934
CHANNEL_ID = -1001648113398
CHANNEL_USERNAME = "@stsgenius"
CHANNEL_LINK = "https://t.me/stsgenius"

# User data storage
user_data = {}
blocked_users = set()

def init_user(user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            'channels': [],
            'explanation': '',
            'waiting_for': None,
            'temp_csv': None
        }

async def is_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    if user_id in blocked_users:
        await update.message.reply_text("❌ You are blocked from using this bot.")
        return
    
    init_user(user_id)
    
    if not await is_member(update, context):
        keyboard = [[InlineKeyboardButton("Join Channel", url=CHANNEL_LINK)]]
        await update.message.reply_text(
            f"Hey {user.first_name}, Welcome to STS Genius Quiz Bot!\n\n"
            "⚠️ Please join our channel first to use this bot.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = [[InlineKeyboardButton("Help", callback_data="help")]]
    await update.message.reply_text(
        f"Hey Dear, Welcome to STS Genius Quiz Bot! 📚\n\nMore Information 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Contact Admin", url="https://t.me/sts_genius")],
        [InlineKeyboardButton("Contact Instagram", url="https://www.instagram.com/sts.genius")],
        [InlineKeyboardButton("About", callback_data="about")]
    ]
    
    message = "How Can I help you? 🤔"
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

async def uploadcsv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in blocked_users:
        return
        
    if not await is_member(update, context):
        await update.message.reply_text("⚠️ Please join our channel first!")
        return
    
    init_user(user_id)
    user_data[user_id]['waiting_for'] = 'csv'
    await update.message.reply_text(
        "📄 Please send your CSV file now.\n\n"
        "Format: Question, Option A, Option B, Option C, Option D, Answer, Explanation\n"
        "(Explanation is optional)"
    )

async def setexplanation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in blocked_users or not await is_member(update, context):
        return
    
    init_user(user_id)
    current_exp = user_data[user_id]['explanation']
    
    keyboard = [
        [InlineKeyboardButton("🖊️ Edit Explanation", callback_data="edit_explanation")],
        [InlineKeyboardButton("❌ Delete Explanation", callback_data="delete_explanation")]
    ]
    
    await update.message.reply_text(
        f"📌 Current Explanation: {current_exp if current_exp else '(Not set)'}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_user(user_id)
    user_data[user_id]['waiting_for'] = None
    user_data[user_id]['temp_csv'] = None
    await update.message.reply_text("❌ Operation cancelled. Back to main menu.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "help":
        await help_command(update, context)
    
    elif data == "about":
        about_text = (
            "🌹 Bot Commands Menu:\n\n"
            "/start - Start the bot and get a welcome message\n"
            "/uploadcsv - Upload your CSV file to generate MCQs\n"
            "/setexplanation - Set a tag to be added in poll explanation\n"
            "/help - How Can I help You"
        )
        await query.edit_message_text(about_text)
    
    elif data == "edit_explanation":
        user_data[user_id]['waiting_for'] = 'explanation'
        await query.edit_message_text(
            "📝 Send new Explanation (max 200 characters).\nSend /cancel to abort."
        )
    
    elif data == "delete_explanation":
        user_data[user_id]['explanation'] = ''
        await query.edit_message_text("✅ Explanation deleted successfully!")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_data or user_data[user_id].get('waiting_for') != 'csv':
        return
    
    try:
        file = await update.message.document.get_file()
        csv_bytes = await file.download_as_bytearray()
        csv_text = csv_bytes.decode('utf-8')
        
        csv_reader = csv.reader(io.StringIO(csv_text))
        rows = list(csv_reader)
        
        if len(rows) < 2:
            await update.message.reply_text("❌ CSV file is empty or invalid!")
            return
        
        bot_explanation = user_data[user_id].get('explanation', '')
        count = 0
        
        for i, row in enumerate(rows[1:], 1):
            if len(row) < 6:
                continue
            
            question = row[0].strip()
            options = [row[1].strip(), row[2].strip(), row[3].strip(), row[4].strip()]
            answer = row[5].strip().upper()
            csv_explanation = row[6].strip() if len(row) > 6 else ""
            
            # Prepare explanation
            final_explanation = ""
            if csv_explanation and bot_explanation:
                total = len(csv_explanation) + len(bot_explanation) + 2
                if total <= 200:
                    final_explanation = f"{csv_explanation}\n\n{bot_explanation}"
                else:
                    final_explanation = bot_explanation[:200]
            elif csv_explanation:
                final_explanation = csv_explanation[:200]
            elif bot_explanation:
                final_explanation = bot_explanation[:200]
            
            # Convert answer to index
            if answer in ['A', 'B', 'C', 'D']:
                answer_index = ord(answer) - ord('A')
            else:
                continue
            
            # Send poll
            await context.bot.send_poll(
                chat_id=update.message.chat_id,
                question=question,
                options=options,
                type=PollType.QUIZ,
                correct_option_id=answer_index,
                explanation=final_explanation if final_explanation else None
            )
            count += 1
        
        await update.message.reply_text(f"✅ Successfully sent {count} polls!")
        user_data[user_id]['waiting_for'] = None
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error processing CSV: {str(e)}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in user_data or not user_data[user_id].get('waiting_for'):
        return
    
    waiting_for = user_data[user_id]['waiting_for']
    
    if waiting_for == 'explanation':
        if len(text) > 200:
            await update.message.reply_text(
                "❌ Explanation is too long! Please send under 200 characters."
            )
            return
        
        user_data[user_id]['explanation'] = text
        user_data[user_id]['waiting_for'] = None
        await update.message.reply_text("✅ Explanation set successfully!")

def main():
    print("🚀 Starting STS Genius Quiz Bot...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("uploadcsv", uploadcsv))
    application.add_handler(CommandHandler("setexplanation", setexplanation))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Callback handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ Bot is now running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
