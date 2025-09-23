# todo_bot.py
# متطلبات: pip install pyTelegramBotAPI
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import os
import threading
import time

TOKEN = "8409746019:AAFlaC9RdJX7pVdjRMlga9a1Bz49RfQf1LI"  # ضع التوكن هنا
DATA_FILE = "tasks_data.json"
LOCK = threading.Lock()

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

# -------------------------
# مساعدات لحفظ/قراءة البيانات
# -------------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with LOCK:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

def save_data(data):
    tmp = DATA_FILE + ".tmp"
    with LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)

def get_user_tasks(user_id):
    data = load_data()
    return data.get(str(user_id), [])

def set_user_tasks(user_id, tasks):
    data = load_data()
    data[str(user_id)] = tasks
    save_data(data)

# -------------------------
# أدوات مساعدة لواجهة المستخدم
# -------------------------
def tasks_to_message(tasks):
    if not tasks:
        return "قائمة المهام فارغة. استخدم /add لإضافة مهمة."
    lines = []
    for i, t in enumerate(tasks, start=1):
        status = "✅" if t.get("done") else "🟩"
        text = t.get("text", "")
        lines.append(f"{i}. {status} {text}")
    return "\n".join(lines)

def make_task_markup(user_id):
    tasks = get_user_tasks(user_id)
    markup = InlineKeyboardMarkup()
    for idx, task in enumerate(tasks):
        row = [
            InlineKeyboardButton(
                ("✅" if task.get("done") else "✔️") + f" #{idx+1}",
                callback_data=f"toggle|{idx}"
            ),
            InlineKeyboardButton("حذف", callback_data=f"delete|{idx}")
        ]
        markup.row(*row)
    if tasks:
        markup.row(InlineKeyboardButton("مسح الكل", callback_data="clear_all"))
    return markup

# -------------------------
# أوامر البوت
# -------------------------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "هلا! 👋\n"
        "هذا بوت بسيط لإدارة قائمة المهام.\n\n"
        "<b>الأوامر المتاحة:</b>\n"
        "/add «النص»  - إضافة مهمة جديدة (مثال: /add اشتري حليب)\n"
        "/list         - عرض قائمة المهام مع أزرار لإدارة كل مهمة\n"
        "/done رقم     - تعليم مهمة كمكتملة (مثال: /done 2)\n"
        "/delete رقم   - حذف مهمة (مثال: /delete 1)\n"
        "/clear        - مسح جميع المهام\n"
        "/help         - عرض هذه الرسالة\n\n"
        "يمكنك أيضاً الضغط على أزرار '✔️' أو 'حذف' بجانب كل مهمة لعمل ذلك بسرعة."
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['add'])
def add_task(message):
    user_id = message.from_user.id
    args = message.text.partition(' ')[2].strip()
    if not args:
        bot.reply_to(message, "اكتب نصّ المهمة بعد الأمر. مثال: /add اقرأ فصل من الكتاب")
        return
    tasks = get_user_tasks(user_id)
    tasks.append({"text": args, "done": False, "created_at": int(time.time())})
    set_user_tasks(user_id, tasks)
    bot.reply_to(message, f"تمت الإضافة ✅\n\n{args}")

@bot.message_handler(commands=['list'])
def list_tasks(message):
    user_id = message.from_user.id
    tasks = get_user_tasks(user_id)
    text = tasks_to_message(tasks)
    markup = make_task_markup(user_id) if tasks else None
    bot.reply_to(message, text, reply_markup=markup)

@bot.message_handler(commands=['done'])
def mark_done_cmd(message):
    user_id = message.from_user.id
    arg = message.text.partition(' ')[2].strip()
    if not arg.isdigit():
        bot.reply_to(message, "استخدم: /done <رقم المهمة>. مثال: /done 1")
        return
    idx = int(arg) - 1
    tasks = get_user_tasks(user_id)
    if idx < 0 or idx >= len(tasks):
        bot.reply_to(message, "رقم المهمة غير صالح.")
        return
    tasks[idx]['done'] = True
    set_user_tasks(user_id, tasks)
    bot.reply_to(message, f"تم تعليم المهمة #{idx+1} كمكتملة ✅")

@bot.message_handler(commands=['delete'])
def delete_cmd(message):
    user_id = message.from_user.id
    arg = message.text.partition(' ')[2].strip()
    if not arg.isdigit():
        bot.reply_to(message, "استخدم: /delete <رقم المهمة>. مثال: /delete 2")
        return
    idx = int(arg) - 1
    tasks = get_user_tasks(user_id)
    if idx < 0 or idx >= len(tasks):
        bot.reply_to(message, "رقم المهمة غير صالح.")
        return
    removed = tasks.pop(idx)
    set_user_tasks(user_id, tasks)
    bot.reply_to(message, f"تم حذف المهمة: {removed.get('text')}")

@bot.message_handler(commands=['clear'])
def clear_all_cmd(message):
    user_id = message.from_user.id
    set_user_tasks(user_id, [])
    bot.reply_to(message, "تم مسح جميع المهام.")

# -------------------------
# معالجة أزرار (CallbackQuery)
# -------------------------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    if data.startswith("toggle|"):
        idx = int(data.split("|",1)[1])
        tasks = get_user_tasks(user_id)
        if 0 <= idx < len(tasks):
            tasks[idx]['done'] = not tasks[idx].get('done', False)
            set_user_tasks(user_id, tasks)
            bot.answer_callback_query(call.id, "تم تحديث المهمة")
            text = tasks_to_message(tasks)
            markup = make_task_markup(user_id)
            try:
                bot.edit_message_text(text, chat_id=call.message.chat.id,
                                      message_id=call.message.message_id,
                                      reply_markup=markup)
            except Exception:
                bot.send_message(user_id, text, reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "المهمة غير موجودة")
    elif data.startswith("delete|"):
        idx = int(data.split("|",1)[1])
        tasks = get_user_tasks(user_id)
        if 0 <= idx < len(tasks):
            removed = tasks.pop(idx)
            set_user_tasks(user_id, tasks)
            bot.answer_callback_query(call.id, "تم الحذف")
            text = tasks_to_message(tasks)
            markup = make_task_markup(user_id) if tasks else None
            try:
                bot.edit_message_text(text, chat_id=call.message.chat.id,
                                      message_id=call.message.message_id,
                                      reply_markup=markup)
            except Exception:
                bot.send_message(user_id, text, reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "المهمة غير موجودة")
    elif data == "clear_all":
        set_user_tasks(user_id, [])
        bot.answer_callback_query(call.id, "تم مسح كل المهام")
        try:
            bot.edit_message_text("قائمة المهام فارغة. استخدم /add لإضافة مهمة.",
                                  chat_id=call.message.chat.id,
                                  message_id=call.message.message_id,
                                  reply_markup=None)
        except Exception:
            bot.send_message(user_id, "قائمة المهام فارغة. استخدم /add لإضافة مهمة.")

# -------------------------
# التقاط الرسائل الحرة
# -------------------------
@bot.message_handler(func=lambda m: True)
def fallback_handler(message):
    text = message.text.strip()
    user_id = message.from_user.id
    if text.lower().startswith(("add ", "/add ")):
        fake = telebot.types.Message.de_json(message.json, bot)
        fake.text = "/add " + text.partition(' ')[2]
        add_task(fake)
        return
    reply = (
        "أرسل /add «نص المهمة» لإضافة مهمة.\n"
        "أو استخدم /list لعرض قائمتك وإدارتها."
    )
    bot.reply_to(message, reply)

# -------------------------
# تشغيل البوت
# -------------------------
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()