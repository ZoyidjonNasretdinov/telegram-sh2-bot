# bot_fixed.py
import telebot
import json
import os
import random
import sys
from datetime import datetime
from telebot import types
from dotenv import load_dotenv

# .env faylini lokalda yuklash (Render kabi muhitlarda ENV orqali olinadi)
load_dotenv()

# --- Fayl va token sozlamalari ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    # TOKEN bo'lmasa, aniq xabar qoldiramiz va chiqamiz (Render loglarida ko'rinadi)
    print("❌ ERROR: BOT_TOKEN env variable is not set. Please add it in Render dashboard or .env locally.")
    sys.exit(1)

bot = telebot.TeleBot(TOKEN)

# adminning idisi
ADMIN_IDS = [7926224444, 1229135388]

user_state = {}

# --- JSON bilan ishlovchi yordamchi funksiyalar ---
def load_data():
    """
    data.json mavjud bo'lmasa yoki korrupt bo'lsa, default struktura qaytaradi.
    """
    if not os.path.exists(DATA_FILE):
        return {"tests": [], "results": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"⚠️ Warning: Failed to load JSON ({e}). Returning empty structure.")
        return {"tests": [], "results": []}

def save_data(data):
    """
    Faylga yozishdan oldin katalog mavjudligini ta'minlaymiz.
    """
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        # Xatolikni log qilamiz (Render yoki lokal loglarda ko'rinadi)
        print(f"❌ ERROR: Failed to save data.json: {e}")

# --- Utility funksiyalar ---
def generate_test_id():
    prefix = random.choice("TABCDEF")
    digits = ''.join(random.choices("0123456789", k=4))
    return prefix + digits

def extract_answers(text):
    # text ichidagi harflarni massiv qilib oladi
    return [ch.lower() for ch in text if ch.lower() in ['a', 'b', 'c', 'd', 'e']]

# --- Reply menyular ---
def admin_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Test qo'shish", "📊 Natijalarni ko'rish")
    markup.add("🗑 Testni o'chirish")
    return markup

def back_button():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⬅️ Orqaga")
    return markup

def generate_tests_menu():
    data = load_data()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # created_at ni string bo'lib saqlaysiz — sort ishlaydi
    for test in sorted(data.get("tests", []), key=lambda x: x.get("created_at", ""), reverse=True):
        markup.add(f"{test.get('test_name')} ({test.get('test_id')})")
    markup.add("⬅️ Orqaga")
    return markup

# --- Handlers ---
@bot.message_handler(commands=['start', 'admin'])
def start(message):
    username = message.from_user.username or f"id_{message.from_user.id}"

    if message.from_user.id in ADMIN_IDS:
        bot.send_message(message.chat.id, "🧑‍💼 Salom, admin!", reply_markup=admin_main_menu())
    else:
        bot.send_message(message.chat.id, "Assalomu alaykum! Ism familiyangizni kiriting:")
        # username-ni boshlang'ich holatda saqlaymiz
        user_state[message.chat.id] = {"step": "get_name", "username": username}

@bot.message_handler(func=lambda m: m.text == "➕ Test qo'shish")
def add_test_start(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    bot.send_message(message.chat.id, "🧾 Test nomini kiriting:", reply_markup=back_button())
    user_state[message.chat.id] = {"step": "get_test_name"}

@bot.message_handler(func=lambda m: m.text == "📊 Natijalarni ko'rish")
def show_test_list(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    data = load_data()
    if not data.get("tests"):
        bot.send_message(message.chat.id, "📭 Hozircha testlar mavjud emas.", reply_markup=admin_main_menu())
        return
    bot.send_message(message.chat.id, "📋 Testlar ro'yxati:", reply_markup=generate_tests_menu())

@bot.message_handler(func=lambda m: m.text == "⬅️ Orqaga")
def go_back(message):
    bot.send_message(message.chat.id, "🏠 Bosh menyu", reply_markup=admin_main_menu())

@bot.message_handler(func=lambda m: m.text == "🗑 Testni o'chirish")
def delete_test_start(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    data = load_data()
    if not data.get("tests"):
        bot.send_message(message.chat.id, "📭 O'chirish uchun testlar mavjud emas.", reply_markup=admin_main_menu())
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for test in sorted(data.get("tests", []), key=lambda x: x.get("created_at", ""), reverse=True):
        markup.add(f"❌ {test.get('test_name')} ({test.get('test_id')})")
    markup.add("⬅️ Orqaga")
    bot.send_message(message.chat.id, "🗑 O'chirmoqchi bo'lgan testni tanlang:", reply_markup=markup)
    user_state[message.chat.id] = {"step": "delete_test"}

@bot.message_handler(func=lambda m: m.chat.id in user_state and user_state[m.chat.id]["step"] == "delete_test")
def delete_selected_test(message):
    if message.text == "⬅️ Orqaga":
        user_state.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "🏠 Bosh menyu", reply_markup=admin_main_menu())
        return

    data = load_data()
    test_id = None
    for test in data.get("tests", []):
        # matn oxirida (ID) yoki ID o'z ichida bo'lsa topamiz
        if message.text.endswith(f"({test.get('test_id')})") or (test.get('test_id') and test.get('test_id') in message.text):
            test_id = test.get('test_id')
            break

    if not test_id:
        bot.send_message(message.chat.id, "❌ Test topilmadi, qayta urinib ko'ring.")
        return

    test = next((t for t in data.get("tests", []) if t.get("test_id") == test_id), None)
    if not test:
        bot.send_message(message.chat.id, "❌ Test topilmadi.")
        return

    data["tests"] = [t for t in data.get("tests", []) if t.get("test_id") != test_id]
    data["results"] = [r for r in data.get("results", []) if r.get("test_id") != test_id]
    save_data(data)

    user_state.pop(message.chat.id, None)
    bot.send_message(
        message.chat.id,
        f"✅ Test muvaffaqiyatli o'chirildi!\n🆔 {test_id}\n📘 {test.get('test_name')}",
        reply_markup=admin_main_menu()
    )

@bot.message_handler(func=lambda m: m.chat.id in user_state and user_state[m.chat.id]["step"] == "get_test_name")
def get_test_name(message):
    user_state[message.chat.id]["test_name"] = message.text
    user_state[message.chat.id]["step"] = "get_correct_answers"
    bot.send_message(message.chat.id, "✅ Endi to'g'ri javoblarni kiriting (masalan: 1a2b3c...30a):")

@bot.message_handler(func=lambda m: m.chat.id in user_state and user_state[m.chat.id]["step"] == "get_correct_answers")
def save_test(message):
    data = load_data()
    step_data = user_state.pop(message.chat.id, None)
    if not step_data:
        bot.send_message(message.chat.id, "❌ Xatolik — yana urinib ko'ring.")
        return

    test_name = step_data.get("test_name", "No name")
    text = message.text.strip()

    if '-' in text:
        test_id, answers = text.split('-', 1)
        test_id = test_id.strip()
    else:
        test_id = generate_test_id()
        answers = text

    correct = ''.join(extract_answers(answers))
    new_test = {
        "test_id": test_id,
        "test_name": test_name,
        "correct_answers": correct,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # eski bilan replace qilish
    data["tests"] = [t for t in data.get("tests", []) if t.get("test_id") != test_id]
    data["tests"].append(new_test)
    save_data(data)

    bot.send_message(
        message.chat.id,
        f"✅ Test saqlandi!\n🆔 {test_id}\n📘 {test_name}",
        reply_markup=admin_main_menu()
    )

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    data = load_data()

    # --- Admin testlarni ko'rishi ---
    if message.from_user.id in ADMIN_IDS:
        for test in data.get("tests", []):
            display_text = f"{test.get('test_name')} ({test.get('test_id')})"
            if message.text and message.text.strip() == display_text:
                test_id = test.get('test_id')
                results = [r for r in data.get("results", []) if r.get("test_id") == test_id]

                if not results:
                    bot.send_message(
                        message.chat.id,
                        f"📭 Bu testni hali hech kim ishlamagan.\n🆔 {test_id} ({test.get('test_name')})",
                        reply_markup=generate_tests_menu()
                    )
                    return

                text = f"📊 <b>{test.get('test_name')}</b>\n🆔 {test_id}\n\n"
                for r in results:
                    text += (
                        f"🧑‍🎓 {r.get('student_name')} (@{r.get('username')})\n"
                        f"✅ {r.get('correct_count')} | ❌ {r.get('incorrect_count')}\n"
                        f"🕓 {r.get('date')}\n\n"
                    )
                bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=generate_tests_menu())
                return

    # --- O'quvchi ismi qabul qilish ---
    if message.chat.id in user_state and user_state[message.chat.id].get("step") == "get_name":
        # username may be already set earlier in start handler
        user_state[message.chat.id]["student_name"] = message.text.strip()
        user_state[message.chat.id]["step"] = "get_test_answers"
        bot.send_message(
            message.chat.id,
            "✅ Endi test ID va javoblaringizni yuboring (masalan: XXXXX 1a2b3c...30a):"
        )
        return

    # --- Test javoblarini qabul qilish ---
    if message.chat.id in user_state and user_state[message.chat.id].get("step") == "get_test_answers":
        step_data = user_state.get(message.chat.id, {})
        student_name = step_data.get("student_name", "NoName")
        username = step_data.get("username", f"id_{message.from_user.id}")
        text = message.text.strip()

        # javobni tekshirish
        parts = text.replace("\n", " ").split()
        if len(parts) < 2:
            bot.send_message(message.chat.id, "❌ Noto'g'ri javob. Masalan: XXXXX 1a2b3c...")
            return

        test_id, user_answers = parts[0], ''.join(parts[1:])
        test = next((t for t in data.get("tests", []) if t.get("test_id") == test_id), None)
        if not test:
            bot.send_message(message.chat.id, "❌ Bu test topilmadi.")
            return

        today = datetime.now().strftime("%Y-%m-%d")
        for r in data.get("results", []):
            if (
                r.get("username") == username and
                r.get("test_id") == test_id and
                r.get("date", "").startswith(today)
            ):
                bot.send_message(message.chat.id, "⚠️ Siz bu testni bugun allaqachon topshirgansiz.")
                return

        correct_list = extract_answers(test.get("correct_answers", ""))
        user_list = extract_answers(user_answers)
        total = min(len(user_list), len(correct_list))
        correct = sum(1 for i in range(total) if user_list[i] == correct_list[i])
        incorrect = len(correct_list) - correct

        result = {
            "student_name": student_name,
            "username": username,
            "test_id": test_id,
            "correct_count": correct,
            "incorrect_count": incorrect,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        data.setdefault("results", []).append(result)
        save_data(data)

        bot.send_message(
            message.chat.id,
            f"📊 Natijangiz:\n🧑‍🎓 {student_name} (@{username})\n🆔 {test_id}\n✅ {correct}\n❌ {incorrect}"
        )

        # Adminga yuborish
        for admin in ADMIN_IDS:
            try:
                bot.send_message(admin, f"📥 {student_name} (@{username})\n🆔 {test_id}\n✅ {correct}\n❌ {incorrect}")
            except Exception as e:
                print(f"⚠️ Warning: failed to notify admin {admin}: {e}")

        user_state.pop(message.chat.id, None)
        return

# --- Bot ishga tushishi ---
if __name__ == "__main__":
    print("🤖 JSON versiya bot ishga tushdi (xavfsiz versiya)...")
    bot.polling(none_stop=True)
