import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

conn = sqlite3.connect("tasks.db")
c = conn.cursor()

c.execute("""
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
["➕ Add Task","📋 Today Tasks"],
["📅 All Tasks","✅ Complete Task"]
]

reply_markup = ReplyKeyboardMarkup(keyboard,resize_keyboard=True)

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello Rohith! Task Manager Ready.",
        reply_markup=reply_markup
    )

async def message_handler(update:Update,context:ContextTypes.DEFAULT_TYPE):
    text=update.message.text

    if text=="📋 Today Tasks":
        rows=c.execute("SELECT task,time FROM tasks WHERE status='pending'").fetchall()

        if not rows:
            await update.message.reply_text("No tasks today")
            return

        msg="Today's Tasks\n\n"
        for i,r in enumerate(rows,1):
            msg+=f"{i}. {r[0]} - {r[1]}\n"

        await update.message.reply_text(msg)

    elif text=="➕ Add Task":
        await update.message.reply_text("Send task like:\nTask | Date | Time\nExample:\nStudy | 2026-03-08 | 19:00")

    elif "|" in text:
        task,date,time=[x.strip() for x in text.split("|")]

        c.execute("INSERT INTO tasks(task,date,time,status) VALUES(?,?,?,?)",
                  (task,date,time,"pending"))

        conn.commit()

        await update.message.reply_text("Task added")

    elif text=="📅 All Tasks":
        rows=c.execute("SELECT id,task,date,time,status FROM tasks").fetchall()

        msg="All Tasks\n\n"
        for r in rows:
            msg+=f"{r[0]}. {r[1]} {r[2]} {r[3]} ({r[4]})\n"

        await update.message.reply_text(msg)

    elif text=="✅ Complete Task":
        await update.message.reply_text("Send task ID to complete")

    elif text.isdigit():
        c.execute("UPDATE tasks SET status='done' WHERE id=?",(text,))
        conn.commit()

        await update.message.reply_text("Task completed")

app=ApplicationBuilder().token("8602038532:AAGW0-d3ME7R3TuJVo6yQtHUZGfwrr5Abkc").build()

app.add_handler(CommandHandler("start",start))
app.add_handler(MessageHandler(filters.TEXT,message_handler))

app.run_polling()