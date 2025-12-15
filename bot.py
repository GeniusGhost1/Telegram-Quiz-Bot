import os
import csv
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.error import TelegramError

# Configuration
BOT_TOKEN = "8319497957:AAF5PAt9fVnOq07PLTA6JsSlFCsdkH1NMBg"
ADMIN_ID = 8122180934
CHANNEL_ID = -1001648113398
CHANNEL_USERNAME = "@stsgenius"
ADMIN_USERNAME = "@sts_genius"
CHANNEL_LINK = "https://t.me/stsgenius"
ADMIN_TELEGRAM_LINK = "https://t.me/sts_genius"
ADMIN_INSTAGRAM_LINK = "https://www.instagram.com/sts.genius"

# Storage (in production, use database)
user_data = {}
blocked_users = set()

def init_user(user_id):
    """Initialize user data"""
    if user_id not in user_data:
        user_data[user_id] = {
            'channels': [],
            'explanation': '',
            'waiting_for': None,
            'temp_csv': None
        }

async def is_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is channel member"""
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    
    if user_id in blocked_users:
        await update.message.reply_text("❌ You are blocked from using this bot.")
        return
    
    init_user(user_id)
    
    # Check channel membership
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
        f"Hey Dear, Welcome to STS Genius Quiz Bot! 📚\n\n"
        "More Information 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    keyboard = [
        [InlineKeyboardButton("Contact Admin", url=TELEGRAM_LINK)],
        [InlineKeyboardButton("Contact Instagram", url=INSTAGRAM_LINK)],
        [InlineKeyboardButton("About", callback_data="about")]
    ]
    
    message = "How Can I help you? 🤔"
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def uploadcsv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /uploadcsv command"""
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

async def getcsv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /getcsv command"""
    user_id = update.effective_user.id
    
    if user_id in blocked_users:
        return
    
    if not await is_member(update, context):
        await update.message.reply_text("⚠️ Please join our channel first!")
        return
    
    init_user(user_id)
    user_data[user_id]['waiting_for'] = 'poll_to_csv'
    await update.message.reply_text("📊 Send me Quizzes or Polls to convert to CSV format.")

async def setexplanation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setexplanation command"""
    user_id = update.effective_user.id
    
    if user_id in blocked_users:
        return
    
    if not await is_member(update, context):
        await update.message.reply_text("⚠️ Please join our channel first!")
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

async def setchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setchannel command"""
    user_id = update.effective_user.id
    
    if user_id in blocked_users:
        return
    
    if not await is_member(update, context):
        await update.message.reply_text("⚠️ Please join our channel first!")
        return
    
    init_user(user_id)
    channels = user_data[user_id]['channels']
    
    keyboard = [
        [InlineKeyboardButton("➕ Add Channel", callback_data="add_channel")],
    ]
    
    if channels:
        keyboard.append([InlineKeyboardButton("✏️ Edit Channels", callback_data="edit_channels")])
        keyboard.append([InlineKeyboardButton("🗑️ Delete Channel", callback_data="delete_channel")])
    
    channel_list = "\n".join([f"• {ch}" for ch in channels]) if channels else "No channels added yet."
    
    await update.message.reply_text(
        f"📺 Your Channels:\n{channel_list}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def authorize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /authorize command (Admin only)"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ This command is only for admin.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 User Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🚫 Block User", callback_data="admin_block")],
        [InlineKeyboardButton("✅ Unblock User", callback_data="admin_unblock")],
        [InlineKeyboardButton("📺 Channel List", callback_data="admin_channels")]
    ]
    
    await update.message.reply_text(
        "🔐 Admin Panel\n\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command"""
    user_id = update.effective_user.id
    init_user(user_id)
    user_data[user_id]['waiting_for'] = None
    user_data[user_id]['temp_csv'] = None
    await update.message.reply_text("❌ Operation cancelled. Back to main menu.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
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
            "/getcsv - Send Quizzes or Polls to CSV\n"
            "/setexplanation - Set a tag to be added in poll explanation\n"
            "/setchannel - Set the target channel for sending content\n"
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
    
    elif data == "add_channel":
        user_data[user_id]['waiting_for'] = 'add_channel'
        await query.edit_message_text(
            "📺 Send the channel ID or username (e.g., @channelname or -1001234567890)\n"
            "Make sure the bot is admin in that channel!"
        )
    
    elif data.startswith("send_"):
        # Handle CSV upload destination
        destination = data.split("_")[1]
        csv_data = user_data[user_id]['temp_csv']
        
        if destination == "bot":
            await send_polls(query.message, context, csv_data, user_id, "bot")
        elif destination == "channel":
            await show_channel_selection(query, user_id)
        elif destination == "both":
            await send_polls(query.message, context, csv_data, user_id, "both")
    
    elif data.startswith("admin_"):
        await handle_admin_actions(update, context, data)

async def show_channel_selection(query, user_id):
    """Show channel selection for CSV upload"""
    channels = user_data[user_id]['channels']
    
    if not channels:
        await query.edit_message_text("❌ No channels added yet! Use /setchannel first.")
        return
    
    keyboard = [[InlineKeyboardButton(ch, callback_data=f"channel_{ch}")] for ch in channels]
    await query.edit_message_text(
        "📺 Select a channel to send polls:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle CSV file upload"""
    user_id = update.effective_user.id
    
    if user_data[user_id]['waiting_for'] != 'csv':
        return
    
    file = await update.message.document.get_file()
    csv_bytes = await file.download_as_bytearray()
    csv_text = csv_bytes.decode('utf-8')
    
    # Parse CSV
    csv_reader = csv.reader(io.StringIO(csv_text))
    rows = list(csv_reader)
    
    if len(rows) < 2:
        await update.message.reply_text("❌ CSV file is empty or invalid!")
        return
    
    user_data[user_id]['temp_csv'] = rows
    
    keyboard = [
        [InlineKeyboardButton("Bot", callback_data="send_bot")],
        [InlineKeyboardButton("Channel", callback_data="send_channel")],
        [InlineKeyboardButton("Both", callback_data="send_both")]
    ]
    
    await update.message.reply_text(
        "✅ CSV uploaded successfully!\n\n"
        "Do you want to upload these quizzes to the bot or forward them to a channel?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_polls(message, context, csv_data, user_id, destination):
    """Send polls from CSV data"""
    bot_explanation = user_data[user_id]['explanation']
    
    for i, row in enumerate(csv_data[1:], 1):
        if len(row) < 6:
            continue
        
        question = row[0]
        options = [row[1], row[2], row[3], row[4]]
        answer = row[5].strip().upper()
        csv_explanation = row[6] if len(row) > 6 else ""
        
        # Prepare explanation
        final_explanation = ""
        if csv_explanation and bot_explanation:
            total = len(csv_explanation) + len(bot_explanation) + 2
            if total <= 200:
                final_explanation = f"{csv_explanation}\n\n{bot_explanation}"
            else:
                remaining = 200 - len(bot_explanation) - 2
                final_explanation = f"{csv_explanation[:remaining]}\n\n{bot_explanation}"
        elif csv_explanation:
            final_explanation = csv_explanation[:200]
        elif bot_explanation:
            final_explanation = bot_explanation[:200]
        
        # Convert answer to index
        answer_index = ord(answer) - ord('A')
        
        try:
            if destination in ["bot", "both"]:
                await context.bot.send_poll(
                    chat_id=message.chat_id,
                    question=question,
                    options=options,
                    type=Poll.QUIZ,
                    correct_option_id=answer_index,
                    explanation=final_explanation if final_explanation else None
                )
            
            if destination in ["channel", "both"]:
                channels = user_data[user_id]['channels']
                for channel in channels:
                    await context.bot.send_poll(
                        chat_id=channel,
                        question=question,
                        options=options,
                        type=Poll.QUIZ,
                        correct_option_id=answer_index,
                        explanation=final_explanation if final_explanation else None
                    )
        except Exception as e:
            await message.reply_text(f"❌ Error sending poll {i}: {str(e)}")
    
    await message.reply_text(f"✅ Successfully sent {len(csv_data)-1} polls!")
    user_data[user_id]['waiting_for'] = None
    user_data[user_id]['temp_csv'] = None

async def handle_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Convert poll to CSV"""
    user_id = update.effective_user.id
    
    if user_data[user_id]['waiting_for'] != 'poll_to_csv':
        return
    
    poll = update.message.poll
    
    if poll.type != Poll.QUIZ:
        await update.message.reply_text("❌ Please send a quiz poll only!")
        return
    
    # Create CSV
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)
    csv_writer.writerow(["Question", "Option A", "Option B", "Option C", "Option D", "Answer"])
    
    answer_letter = chr(ord('A') + poll.correct_option_id)
    row = [poll.question] + [opt.text for opt in poll.options] + [answer_letter]
    csv_writer.writerow(row)
    
    # Send CSV file
    csv_bytes = csv_buffer.getvalue().encode('utf-8')
    await update.message.reply_document(
        document=io.BytesIO(csv_bytes),
        filename="quiz.csv",
        caption="✅ Here is your CSV file!"
    )
    
    user_data[user_id]['waiting_for'] = None

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in user_data or not user_data[user_id]['waiting_for']:
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
    
    elif waiting_for == 'add_channel':
        user_data[user_id]['channels'].append(text)
        user_data[user_id]['waiting_for'] = None
        await update.message.reply_text(f"✅ Channel {text} added successfully!")

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin panel actions"""
    query = update.callback_query
    data = query.data
    
    if data == "admin_stats":
        total_users = len(user_data)
        all_channels = set()
        for uid in user_data:
            all_channels.update(user_data[uid]['channels'])
        
        stats_text = (
            f"📊 Bot Statistics\n\n"
            f"👥 Total Users: {total_users}\n"
            f"📺 Total Channels: {len(all_channels)}\n"
            f"🚫 Blocked Users: {len(blocked_users)}"
        )
        await query.edit_message_text(stats_text)
    
    elif data == "admin_broadcast":
        user_data[ADMIN_ID]['waiting_for'] = 'broadcast'
        await query.edit_message_text("📢 Send the message to broadcast to all users:")
    
    elif data == "admin_channels":
        all_channels = set()
        for uid in user_data:
            all_channels.update(user_data[uid]['channels'])
        
        channel_list = "\n".join(all_channels) if all_channels else "No channels"
        await query.edit_message_text(f"📺 All Channels:\n\n{channel_list}")

def main():
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("uploadcsv", uploadcsv))
    application.add_handler(CommandHandler("getcsv", getcsv))
    application.add_handler(CommandHandler("setexplanation", setexplanation))
    application.add_handler(CommandHandler("setchannel", setchannel))
    application.add_handler(CommandHandler("authorize", authorize))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.POLL, handle_poll))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Callback handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Start bot
    print("Bot started successfully! 🚀")
    application.run_polling()

if __name__ == '__main__':
    main()
