import os
import sqlite3
from datetime import datetime, timedelta
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = os.getenv("BOT_TOKEN")

conn = sqlite3.connect("tasks.db", check_same_thread=False)
c = conn.cursor()

c.execute(
    """
CREATE TABLE IF NOT EXISTS tasks(
id INTEGER PRIMARY KEY,
task TEXT,
category TEXT,
date TEXT,
time TEXT,
status TEXT,
recurring TEXT
)
"""
)

conn.commit()

main_keyboard = [
    ["➕ Add Task", "📋 Today Tasks"],
    ["📅 All Tasks", "❌ Delete Task"],
]

markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)

scheduler = AsyncIOScheduler()
scheduler.start()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Task Manager Ready", reply_markup=markup)


async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send task name")
    context.user_data["state"] = "task"


async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "➕ Add Task":
        await add_task(update, context)
        return

    if context.user_data.get("state") == "task":
        context.user_data["task"] = text

        keyboard = [
            [
                InlineKeyboardButton("📚 Study", callback_data="cat_study"),
                InlineKeyboardButton("💻 Project", callback_data="cat_project"),
            ],
            [
                InlineKeyboardButton("🏫 College", callback_data="cat_college"),
                InlineKeyboardButton("🧠 Personal", callback_data="cat_personal"),
            ],
        ]

        await update.message.reply_text(
            "Choose category", reply_markup=InlineKeyboardMarkup(keyboard)
        )

        context.user_data["state"] = "category"
        return

    if text == "📋 Today Tasks":

        today = datetime.now().strftime("%Y-%m-%d")

        rows = c.execute(
            "SELECT id,task,time FROM tasks WHERE date=? AND status='pending'",
            (today,),
        ).fetchall()

        if not rows:
            await update.message.reply_text("No tasks today")
            return

        msg = "Today's Tasks\n\n"

        for r in rows:
            msg += f"{r[0]}. {r[1]} - {r[2]}\n"

        await update.message.reply_text(msg)

    if text == "📅 All Tasks":

        rows = c.execute("SELECT * FROM tasks").fetchall()

        msg = ""

        for r in rows:
            msg += f"{r[0]}. {r[1]} | {r[3]} {r[4]} ({r[5]})\n"

        await update.message.reply_text(msg)

    if text == "❌ Delete Task":

        await update.message.reply_text("Send task id to delete")

        context.user_data["state"] = "delete"

        return

    if context.user_data.get("state") == "delete":

        c.execute("DELETE FROM tasks WHERE id=?", (text,))
        conn.commit()

        await update.message.reply_text("Task deleted")

        context.user_data["state"] = None


async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    category = query.data.split("_")[1]

    context.user_data["category"] = category

    keyboard = [
        [
            InlineKeyboardButton("Today", callback_data="date_today"),
            InlineKeyboardButton("Tomorrow", callback_data="date_tomorrow"),
        ]
    ]

    await query.edit_message_text(
        "Select date", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "date_today":
        date = datetime.now().strftime("%Y-%m-%d")

    else:
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    context.user_data["date"] = date

    await query.edit_message_text("Send time like 07:30 PM")

    context.user_data["state"] = "time"


async def save_task(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if context.user_data.get("state") != "time":
        return

    time = update.message.text

    task = context.user_data["task"]
    category = context.user_data["category"]
    date = context.user_data["date"]

    c.execute(
        "INSERT INTO tasks(task,category,date,time,status,recurring) VALUES(?,?,?,?,?,?)",
        (task, category, date, time, "pending", "none"),
    )

    conn.commit()

    await update.message.reply_text("Task added", reply_markup=markup)

    context.user_data["state"] = None


async def reminder_job(context: ContextTypes.DEFAULT_TYPE):

    now = datetime.now()

    rows = c.execute("SELECT task,date,time FROM tasks WHERE status='pending'").fetchall()

    for r in rows:

        dt = datetime.strptime(r[1] + " " + r[2], "%Y-%m-%d %I:%M %p")

        diff = (dt - now).total_seconds()

        if 0 < diff < 60:

            await context.bot.send_message(
                chat_id=context.job.chat_id,
                text=f"Reminder\nTask: {r[0]}\nTime: {r[2]}",
            )


async def daily_summary(context: ContextTypes.DEFAULT_TYPE):

    today = datetime.now().strftime("%Y-%m-%d")

    rows = c.execute(
        "SELECT task,time FROM tasks WHERE date=? AND status='pending'", (today,)
    ).fetchall()

    msg = "Today's Pending Tasks\n\n"

    for r in rows:
        msg += f"{r[0]} - {r[1]}\n"

    await context.bot.send_message(chat_id=context.job.chat_id, text=msg)


async def productivity_report(context: ContextTypes.DEFAULT_TYPE):

    completed = c.execute(
        "SELECT COUNT(*) FROM tasks WHERE status='done'"
    ).fetchone()[0]

    pending = c.execute(
        "SELECT COUNT(*) FROM tasks WHERE status='pending'"
    ).fetchone()[0]

    msg = f"Today's Productivity\nCompleted: {completed}\nPending: {pending}"

    await context.bot.send_message(chat_id=context.job.chat_id, text=msg)


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, router))
app.add_handler(CallbackQueryHandler(category_handler, pattern="cat_"))
app.add_handler(CallbackQueryHandler(date_handler, pattern="date_"))
app.add_handler(MessageHandler(filters.TEXT, save_task))

scheduler.add_job(reminder_job, "interval", seconds=30)
scheduler.add_job(daily_summary, "cron", hour=18, minute=0)
scheduler.add_job(productivity_report, "cron", hour=21, minute=30)

app.run_polling()