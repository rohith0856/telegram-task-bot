import os
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
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

scheduler = AsyncIOScheduler()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    if text == "📅 All Tasks":

        rows = cursor.execute("SELECT * FROM tasks").fetchall()

        msg = ""

        for r in rows:
            msg += f"{r[0]}. {r[1]} | {r[2]} {r[3]} ({r[4]})\n"

        await update.message.reply_text(msg)

    if text == "❌ Delete Task":

        await update.message.reply_text("Send task id to delete")

        context.user_data["delete"] = True
        return

    if context.user_data.get("delete"):

        cursor.execute("DELETE FROM tasks WHERE id=?", (text,))
        conn.commit()

        await update.message.reply_text("Task deleted")

        context.user_data["delete"] = False


async def reminder_job(context: ContextTypes.DEFAULT_TYPE):

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
                    chat_id=context.job.chat_id,
                    text=f"Reminder\nTask: {r[0]}\nTime: {r[2]}"
                )

        except:
            pass


async def daily_summary(context: ContextTypes.DEFAULT_TYPE):

    today = datetime.now().strftime("%Y-%m-%d")

    rows = cursor.execute(
        "SELECT task,time FROM tasks WHERE date=? AND status='pending'",
        (today,)
    ).fetchall()

    msg = "Today's Pending Tasks\n\n"

    for r in rows:
        msg += f"{r[0]} - {r[1]}\n"

    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=msg
    )


async def productivity_report(context: ContextTypes.DEFAULT_TYPE):

    completed = cursor.execute(
        "SELECT COUNT(*) FROM tasks WHERE status='done'"
    ).fetchone()[0]

    pending = cursor.execute(
        "SELECT COUNT(*) FROM tasks WHERE status='pending'"
    ).fetchone()[0]

    msg = f"Productivity Report\nCompleted: {completed}\nPending: {pending}"

    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=msg
    )


async def post_init(application):

    scheduler.add_job(reminder_job, "interval", seconds=30)
    scheduler.add_job(daily_summary, "cron", hour=18, minute=0)
    scheduler.add_job(productivity_report, "cron", hour=21, minute=30)

    scheduler.start()


app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, router))

app.run_polling()