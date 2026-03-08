import os
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = os.getenv("BOT_TOKEN")

conn = sqlite3.connect("tasks.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks(
id INTEGER PRIMARY KEY,
task TEXT,
date TEXT,
time TEXT,
status TEXT
)
""")
conn.commit()

keyboard = [
["➕ Add Task", "📋 Today Tasks"],
["📅 All Tasks", "❌ Delete Task"]
]

markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

CHAT_ID = None
scheduler = AsyncIOScheduler()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global CHAT_ID
    CHAT_ID = update.effective_chat.id

    await update.message.reply_text(
        "Task Manager Ready",
        reply_markup=markup
    )


async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "➕ Add Task":
        await update.message.reply_text(
            "Send task like:\nTask | 2026-03-10 | 7:30 PM"
        )
        return

    if "|" in text:

        try:

            task, date, time = [x.strip() for x in text.split("|")]

            cursor.execute(
                "INSERT INTO tasks(task,date,time,status) VALUES(?,?,?,?)",
                (task, date, time, "pending")
            )

            conn.commit()

            await update.message.reply_text("Task added")

        except:
            await update.message.reply_text("Format error")

        return

    if text == "📋 Today Tasks":

        today = datetime.now().strftime("%Y-%m-%d")

        rows = cursor.execute(
            "SELECT id,task,time FROM tasks WHERE date=? AND status='pending'",
            (today,)
        ).fetchall()

        if not rows:
            await update.message.reply_text("No tasks today")
            return

        msg = "Today's Tasks\n\n"

        for r in rows:
            msg += f"{r[0]}. {r[1]} - {r[2]}\n"

        await update.message.reply_text(msg)


async def reminder_job(context: ContextTypes.DEFAULT_TYPE):

    global CHAT_ID

    if CHAT_ID is None:
        return

    now = datetime.now()

    rows = cursor.execute(
        "SELECT task,date,time FROM tasks WHERE status='pending'"
    ).fetchall()

    for r in rows:

        try:

            dt = datetime.strptime(
                r[1] + " " + r[2],
                "%Y-%m-%d %I:%M %p"
            )

            diff = (dt - now).total_seconds()

            if 0 < diff < 60:

                await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=f"Reminder\nTask: {r[0]}\nTime: {r[2]}"
                )

        except:
            pass


async def post_init(application):

    scheduler.add_job(reminder_job, "interval", seconds=30)
    scheduler.start()


app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, router))

app.run_polling()