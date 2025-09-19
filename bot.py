from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
from google.oauth2.service_account import Credentials
import gspread
import datetime
from collections import defaultdict

# === GOOGLE SHEETS SETUP ===
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

SHEET_URL = "https://docs.google.com/spreadsheets/d/13HO2PNGk0gK8QrFNLmrHwEwNF4vZP1eH6tJzw5k40SI/edit?gid=0#gid=0"  # replace with your sheet URL
sheet = client.open_by_url(SHEET_URL).sheet1

TOKEN = "8350479223:AAETthoMW4cd8OuyT1DxABYYfgrcqEw4Z3A"

# Conversation states
CHOOSING, ITEM, AMOUNT, NOTES = range(4)
user_data = {}

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["👨‍🌾 Sirma", "👨‍🌾 Kenny"],
                ["📝 Planned", "📊 Totals"],
                ["📅 Weekly Summary"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "👋 Welcome! Choose contributor, or view totals/weekly summary:",
        reply_markup=reply_markup
    )
    return CHOOSING

# Handle choice of person or report
async def choose_person(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text

    if "Totals" in choice:
        await send_totals(update, context)
        return CHOOSING
    elif "Weekly Summary" in choice:
        await send_weekly_summary(update, context)
        return CHOOSING

    # Otherwise handle expense entry
    user_data["person"] = choice
    await update.message.reply_text("✍️ Enter the item description:", reply_markup=ReplyKeyboardRemove())
    return ITEM

# Handle item input
async def get_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data["item"] = update.message.text
    await update.message.reply_text("💰 Enter the amount (KES):")
    return AMOUNT

# Handle amount input
async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_data["amount"] = int(update.message.text)
    except:
        await update.message.reply_text("⚠️ Please enter a valid number for the amount.")
        return AMOUNT
    await update.message.reply_text("📝 Enter any notes (or type '-' if none):")
    return NOTES

# Handle notes input and save to Google Sheets
async def get_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notes = update.message.text
    if notes.strip() == "-":
        notes = ""
    user_data["notes"] = notes

    # === Week calculation ===
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    project_start = datetime.date(2025, 8, 30)
    today = datetime.date.today()
    days_diff = (today - project_start).days
    week = (days_diff // 7) + 1

    # Write to Google Sheets
    person = user_data["person"]
    item = user_data["item"]
    amount = user_data["amount"]

    if "sirma" in person.lower():
        sheet.append_row([date, week, item, amount, "", "", notes])
    elif "kenny" in person.lower():
        sheet.append_row([date, week, item, "", amount, "", notes])
    else:  # Planned
        sheet.append_row([date, week, item, "", "", amount, notes])

    await update.message.reply_text(
        f"✅ Added {item} ({amount} KES) for {person} (Week {week}, Notes: {notes})"
    )

    # Show menu again
    keyboard = [["👨‍🌾 Sirma", "👨‍🌾 Kenny"],
                ["📝 Planned", "📊 Totals"],
                ["📅 Weekly Summary"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Want to add another? Choose contributor:", reply_markup=reply_markup)

    return CHOOSING

# === Totals function ===
async def send_totals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = sheet.get_all_values()
        headers = data[0]
        rows = data[1:]

        sirma_col = headers.index("Sirma (KES)")
        kenny_col = headers.index("Kenny (KES)")
        planned_col = headers.index("Planned (KES)")

        def safe_int(val):
            try:
                return int(val)
            except:
                return 0

        sirma_total = sum(safe_int(row[sirma_col]) for row in rows)
        kenny_total = sum(safe_int(row[kenny_col]) for row in rows)
        planned_total = sum(safe_int(row[planned_col]) for row in rows)
        grand_total = sirma_total + kenny_total + planned_total

        msg = (
            f"📊 *Current Totals:*\n\n"
            f"👨‍🌾 Sirma: {sirma_total:,} KES\n"
            f"👨‍🌾 Kenny: {kenny_total:,} KES\n"
            f"📝 Planned: {planned_total:,} KES\n"
            f"💰 *Grand Total: {grand_total:,} KES*"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error fetching totals: {e}")

# === Weekly Summary function ===
async def send_weekly_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = sheet.get_all_values()
        headers = data[0]
        rows = data[1:]

        week_col = headers.index("Week")
        sirma_col = headers.index("Sirma (KES)")
        kenny_col = headers.index("Kenny (KES)")
        planned_col = headers.index("Planned (KES)")

        def safe_int(val):
            try:
                return int(val)
            except:
                return 0

        weekly = defaultdict(lambda: {"sirma": 0, "kenny": 0, "planned": 0})

        for row in rows:
            week = row[week_col]
            weekly[week]["sirma"] += safe_int(row[sirma_col])
            weekly[week]["kenny"] += safe_int(row[kenny_col])
            weekly[week]["planned"] += safe_int(row[planned_col])

        msg = "📅 *Weekly Summary:*\n\n"
        for week, vals in sorted(weekly.items(), key=lambda x: int(x[0])):
            total = vals["sirma"] + vals["kenny"] + vals["planned"]
            msg += (
                f"🗓 Week {week}:\n"
                f"   👨‍🌾 Sirma: {vals['sirma']:,} KES\n"
                f"   👨‍🌾 Kenny: {vals['kenny']:,} KES\n"
                f"   📝 Planned: {vals['planned']:,} KES\n"
                f"   💰 Total: {total:,} KES\n\n"
            )

        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error fetching weekly summary: {e}")

# /cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚪 Cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        CHOOSING: [MessageHandler(filters.Regex("^(👨‍🌾 Sirma|👨‍🌾 Kenny|📝 Planned|📊 Totals|📅 Weekly Summary)$"), choose_person)],
        ITEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_item)],
        AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
        NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_notes)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Build app
app = Application.builder().token(TOKEN).build()
app.add_handler(conv_handler)

print("🤖 Bot with Weekly Summary is running...")
app.run_polling()
