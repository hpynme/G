import os
import logging
# অন্য সব import এখানে
from dotenv import  load_dotenv #

import asyncio
import random
import time
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import io
import math 

# .env ফাইল থেকে এনভায়রনমেন্ট ভেরিয়েবল লোড করুন
load_dotenv()

# --- ১. লগিং সেটআপ ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- ২. এনভায়রনমেন্ট ভেরিয়েবল অ্যাক্সেস করা ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", "8080")) # যদি PORT সেট না থাকে, ডিফল্ট 8080 ব্যবহার করবে
# অন্যান্য ভেরিয়েবলও একইভাবে অ্যাক্সেস করতে পারেন
# যেমন: MY_API_KEY = os.environ.get("MY_API_KEY")


from telegram import (
    Update,
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto # ইমেজ ক্যাপশন সহ পাঠানোর জন্য
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)

# --- ১. লগিং সেটআপ ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logging.getLogger('httpx').setLevel(logging.WARNING) # httpx লাইব্রেরির ওয়ার্নিং কমানো
logger = logging.getLogger(__name__)

# --- ২. এনভায়রনমেন্ট ভেরিয়েবল লোড করা ---
# Render এ হোস্ট করার জন্য এই ভেরিয়েবলগুলো আপনার ENV VARS এ সেট করতে হবে।
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") # Render এর সার্ভিসের URL
PORT = int(os.environ.get("PORT", "8080")) # Render সাধারণত 8080 পোর্ট ব্যবহার করে

# --- ৩. গ্লোবাল স্টেট এবং ইউজার-স্পেসিফিক ডেটা (অস্থায়ী) ---
# এটি একটি ডিকশনারি যা ব্যবহারকারীর আইডি অনুযায়ী বিভিন্ন ডেটা সংরক্ষণ করে।
# প্রোডাকশনের জন্য পার্মানেন্ট ডাটাবেস ব্যবহার করা উচিত।
user_data = {} 
# user_data স্ট্রাকচার:
# {
#   chat_id: {
#     'quiz_active': bool,
#     'current_quiz_index': int,
#     'quiz_score': int,
#     'quiz_attempts': int,
#     'tasks': list, # [{'id': int, 'desc': str, 'completed': bool}]
#     'calculator_history': list, # [(expression, result)]
#     'last_activity': datetime,
#   }
# }

# বটের স্টার্ট টাইম
START_TIME = datetime.now()

# --- ৪. স্ট্যাটিক ডেটা (API এর বিকল্প) ---

# র‍্যান্ডম জোকস/ফ্যাক্টস
JOKES_AND_FACTS = [
    "কচ্ছপ তার পায়ের আঙুল দিয়ে শ্বাস নিতে পারে।",
    "একটি উটপাখির চোখ তার মস্তিষ্কের চেয়ে বড়।",
    "আপনি একটি শূকরকে আকাশের দিকে তাকাতে পারবেন না।",
    "মানুষ তার জীবনের প্রায় এক বছর শুধুমাত্র ফোন খুঁজতে ব্যয় করে।",
    "বিড়ালরা তাদের জীবনের প্রায় ৭০% ঘুমিয়ে কাটায়।",
    "আপনি যদি এক হাতে গরম জল এবং অন্য হাতে ঠান্ডা জল রাখেন তবে গরম জলটি ভারী মনে হবে।",
    "হাঁসদের 'কোয়াক' শব্দে কোনো প্রতিধ্বনি হয় না। কেউ জানে না কেন!",
    "একটি পেন্সিলের একটি লাইন ৩০ মাইল লম্বা হতে পারে।",
    "একজন মানুষ হাসতে দিনে ১৭টি পেশী ব্যবহার করে, রাগ করতে ৪৩টি।",
    "পৃথিবীর সবচেয়ে বড় মহাসাগর হলো প্রশান্ত মহাসাগর।"
]

# কুইজ ডেটা (মাল্টিপল চয়েস)
QUIZZES = [
    {
        "question": "বাংলাদেশের জাতীয় ফলের নাম কি?",
        "options": ["আম", "কাঁঠাল", "পেয়ারা", "লিচু"],
        "answer": "কাঁঠাল"
    },
    {
        "question": "সূর্য কোন দিকে ওঠে?",
        "options": ["পশ্চিম", "উত্তর", "পূর্ব", "দক্ষিণ"],
        "answer": "পূর্ব"
    },
    {
        "question": "পানির রাসায়নিক সংকেত কি?",
        "options": ["CO2", "O2", "H2O", "CH4"],
        "answer": "H2O"
    },
    {
        "question": "পৃথিবীর বৃহত্তম মহাদেশ কোনটি?",
        "options": ["আফ্রিকা", "এশিয়া", "ইউরোপ", "অস্ট্রেলিয়া"],
        "answer": "এশিয়া"
    },
    {
        "question": "কোন গ্রহ লাল গ্রহ নামে পরিচিত?",
        "options": ["মঙ্গল", "বুধ", "শুক্র", "বৃহস্পতি"],
        "answer": "মঙ্গল"
    },
    {
        "question": "কে অক্সিজেন আবিষ্কার করেন?",
        "options": ["জেমস ওয়াট", "জোসেফ প্রিস্টলি", "আইজ্যাক নিউটন", "আলবার্ট আইনস্টাইন"],
        "answer": "জোসেফ প্রিস্টলি"
    },
    {
        "question": "মানবদেহে কয়টি হাড় আছে?",
        "options": ["206", "216", "196", "226"],
        "answer": "206"
    },
    {
        "question": "বিশ্বের সবচেয়ে দ্রুততম স্থলপ্রাণী কোনটি?",
        "options": ["সিংহ", "চিতা", "বাঘ", "ফ্যালকন"],
        "answer": "চিতা"
    },
    {
        "question": "ক্যালেন্ডারে কোন মাসটি সবচেয়ে কম দিনের?",
        "options": ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "ডিসেম্বর"],
        "answer": "ফেব্রুয়ারি"
    },
    {
        "question": "শেক্সপিয়রের বিখ্যাত নাটক 'হ্যামলেট' কোন দেশের প্রেক্ষাপটে লেখা?",
        "options": ["ইংল্যান্ড", "ফ্রান্স", "ডেনমার্ক", "ইতালি"],
        "answer": "ডেনমার্ক"
    }
]

# --- ৫. হেল্পার ফাংশন ---

def get_user_state(user_id):
    """ব্যবহারকারীর জন্য ডেটা স্টেট তৈরি বা লোড করে।"""
    if user_id not in user_data:
        user_data[user_id] = {
            'quiz_active': False,
            'current_quiz_index': -1,
            'quiz_score': 0,
            'quiz_attempts': 0,
            'tasks': [],
            'calculator_history': [],
            'last_activity': datetime.now(),
        }
    user_data[user_id]['last_activity'] = datetime.now() # শেষ কার্যকলাপ আপডেট করা
    return user_data[user_id]

def update_bot_uptime():
    """বটের আপটাইম গণনা করে।"""
    uptime_seconds = (datetime.now() - START_TIME).total_seconds()
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(days)} দিন, {int(hours)} ঘন্টা, {int(minutes)} মিনিট, {int(seconds)} সেকেন্ড"

async def send_long_message(update: Update, text: str, parse_mode='HTML') -> None:
    """লম্বা মেসেজকে ছোট ছোট অংশে ভাগ করে পাঠায়।"""
    if len(text) <= 4096:
        await update.message.reply_text(text, parse_mode=parse_mode)
        return

    # মেসেজকে লাইন ব্রেক (নিউলাইন) দিয়ে ভাগ করার চেষ্টা
    parts = text.split('\n')
    current_part = ""
    for part in parts:
        if len(current_part) + len(part) + 1 > 4096: # +1 for newline
            await update.message.reply_text(current_part, parse_mode=parse_mode)
            current_part = part
        else:
            current_part += "\n" + part
    if current_part: # শেষ অংশটি পাঠানো
        await update.message.reply_text(current_part, parse_mode=parse_mode)


# --- ৬. কমান্ড হ্যান্ডলার ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start কমান্ডের উত্তর দেয়।"""
    user = update.effective_user
    user_state = get_user_state(user.id) # স্টেট ইনিশিয়ালাইজ করার জন্য

    welcome_message = (
        f"হাই {user.mention_html()}! 👋\n"
        "আমি একটি মাল্টি-ফাংশনাল বট, যা কোনো এক্সটার্নাল API কী ছাড়াই কাজ করে।\n"
        "আমার কমান্ডগুলো দেখতে /help লিখুন।"
    )
    await update.message.reply_html(
        welcome_message,
        reply_markup=ForceReply(selective=True),
    )
    logger.info(f"User {user.full_name} started the bot.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help কমান্ডের উত্তর দেয়।"""
    help_text = (
        "এখানে আমার উপলব্ধ কমান্ডগুলো দেওয়া হলো:\n\n"
        "  • `/start` - বটের সাথে কথোপকথন শুরু করুন।\n"
        "  • `/help` - এই সাহায্য মেসেজটি দেখান।\n"
        "  • `/echo <text>` - আপনার মেসেজটি ফিরিয়ে দেবো।\n"
        "  • `/joke` - একটি র‍্যান্ডম জোকস বা মজার তথ্য বলুন।\n"
        "  • `/botinfo` - বটের বর্তমান অবস্থা এবং আপটাইম দেখুন।\n"
        "  • `/calc <expression>` - গাণিতিক হিসাব করুন (যেমন: `/calc 2+2*5`)।\n"
        "  • `/quiz` - একটি সাধারণ জ্ঞান কুইজ শুরু করুন।\n"
        "  • `/image <text>` - আপনার টেক্সট দিয়ে একটি ছবি তৈরি করুন।\n"
        "  • `/addtask <task_description>` - আপনার টাস্ক লিস্টে একটি টাস্ক যোগ করুন।\n"
        "  • `/showtasks` - আপনার সব টাস্ক দেখান।\n"
        "  • `/removetask <number>` - টাস্ক লিস্ট থেকে একটি টাস্ক মুছে ফেলুন।\n\n"
        "আমি আপনার জন্য আরও অনেক কিছু করতে প্রস্তুত! 😊"
    )
    await send_long_message(update, help_text, parse_mode='Markdown')
    logger.info(f"User {update.effective_user.full_name} requested help.")

async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/echo কমান্ডের উত্তর দেয়।"""
    if not context.args:
        await update.message.reply_text("দয়া করে `/echo` এর পরে কিছু লিখুন। যেমন: `/echo হ্যালো পৃথিবী`")
        return
    text_to_echo = " ".join(context.args)
    await update.message.reply_text(f"আপনি লিখেছেন: `{text_to_echo}`", parse_mode='Markdown')
    logger.info(f"Echo command by {update.effective_user.full_name}: '{text_to_echo}'")

async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/joke কমান্ডের উত্তর দেয়। একটি র‍্যান্ডম জোকস বা ফ্যাক্টস দেয়।"""
    random_fact = random.choice(JOKES_AND_FACTS)
    await update.message.reply_text(f"আপনার জন্য একটি মজার তথ্য:\n\n_{random_fact}_", parse_mode='Markdown')
    logger.info(f"User {update.effective_user.full_name} requested a joke/fact.")

async def bot_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/botinfo কমান্ডের উত্তর দেয়। বটের আপটাইম এবং অন্যান্য তথ্য দেখায়।"""
    uptime = update_bot_uptime()
    
    # মেমরি ব্যবহারের তথ্য (যদি পাওয়া যায়, এটি রেন্ডার এনভায়রনমেন্টে নাও পাওয়া যেতে পারে)
    # এই অংশটি শুধুমাত্র ধারণা দেওয়ার জন্য, প্রকৃত RAM ব্যবহার মনিটর করা Render এর বাইরে কঠিন।
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / (1024 * 1024) # MB এ
        memory_info = f"  • মেমরি ব্যবহার: {memory_usage:.2f} MB\n"
    except ImportError:
        memory_info = "  • মেমরি ব্যবহারের তথ্য উপলব্ধ নয় (psutil ইনস্টল নেই)।\n"

    info_text = (
        "**বট ইনফো:**\n"
        f"  • বটের নাম: @{(await context.bot.get_me()).username}\n"
        f"  • বটের আইডি: {(await context.bot.get_me()).id}\n"
        f"  • আপটাইম: {uptime}\n"
        f"{memory_info}"
        f"  • সক্রিয় ব্যবহারকারী সেশন: {len(user_data)} জন (অস্থায়ী ডেটা)\n"
        "  • হোস্ট: Render (ফ্রি টিয়ার)\n\n"
        "এটি সম্পূর্ণ পাইথন দিয়ে তৈরি এবং কোনো এক্সটার্নাল API কী ব্যবহার করে না!"
    )
    await send_long_message(update, info_text, parse_mode='Markdown')
    logger.info(f"User {update.effective_user.full_name} requested bot info.")


async def calculate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/calc কমান্ডের উত্তর দেয়। গাণিতিক হিসাব করে।"""
    user_id = update.effective_user.id
    user_state = get_user_state(user_id)

    if not context.args:
        await update.message.reply_text("দয়া করে `/calc` এর পরে একটি গাণিতিক এক্সপ্রেশন দিন। যেমন: `/calc 5*10+2`")
        return

    expression = "".join(context.args).replace('^', '**') # ঘাতকে পাইথনের উপযোগী করা
    
    # অনুমোদিত অক্ষরের একটি সেট তৈরি করা
    allowed_chars = "0123456789.+-*/()% " # "%" for modulo
    
    # এক্সপ্রেশন ভ্যালিডেট করা
    for char in expression:
        if char not in allowed_chars and not char.isalpha(): #isalpha() এখানে অতিরিক্ত সুরক্ষা, যদিও থাকা উচিত নয়
            await update.message.reply_text("❌ শুধুমাত্র সংখ্যা, মৌলিক গাণিতিক অপারেটর (+, -, *, /, %, (), .) ব্যবহার করুন।")
            logger.warning(f"Invalid char '{char}' in calc expression from {user_id}: '{expression}'")
            return
    
    # কিছু অনিরাপদ প্যাটার্ন পরীক্ষা করা
    if any(keyword in expression for keyword in ['import', 'os', 'sys', 'subprocess', 'exec', 'eval', '__']):
        await update.message.reply_text("❌ আপনার এক্সপ্রেশনটি অনিরাপদ কোড মনে হচ্ছে। দয়া করে শুধুমাত্র গাণিতিক হিসাব দিন।")
        logger.warning(f"Potentially unsafe calc expression from {user_id}: '{expression}'")
        return

    try:
        # গণনার জন্য একটি সীমিত গ্লোবাল এবং লোকাল এনভায়রনমেন্ট
        # এটি eval() এর নিরাপত্তা ঝুঁকি কমাতে সাহায্য করে, কিন্তু সম্পূর্ণ নিরাপদ নয়।
        safe_dict = {
            '__builtins__': {
                'abs': abs, 'round': round, 'sum': sum, 'min': min, 'max': max,
                'pow': pow, # pow() ফাংশন, যদিও আমরা ** ব্যবহার করছি
            },
            'math': {
                'sqrt': math.sqrt, 'log': math.log, 'sin': math.sin, 'cos': math.cos,
                'tan': math.tan, 'pi': math.pi, 'e': math.e,
            }
        }
        result = eval(expression, {"__builtins__": None}, safe_dict) # গ্লোবাল/লোকাল ডিকশনারি সেট করা
        
        # ফলাফলকে ২ দশমিক স্থান পর্যন্ত সীমাবদ্ধ করা যদি ফ্লোট হয়
        if isinstance(result, float):
            result = round(result, 2)

        await update.message.reply_text(f"আপনার হিসাবের ফলাফল: `{result}`", parse_mode='Markdown')
        user_state['calculator_history'].append((expression, result))
        logger.info(f"Calc by {user_id}: {expression} = {result}")

    except (SyntaxError, ZeroDivisionError, TypeError, NameError) as e:
        await update.message.reply_text(f"❌ ভুল এক্সপ্রেশন বা হিসাবের ত্রুটি: `{e}`")
        logger.error(f"Calc error from {user_id} for '{expression}': {e}")
    except Exception as e:
        logger.error(f"Unexpected calculation error from {user_id} for '{expression}': {e}")
        await update.message.reply_text("❌ হিসাব করতে সমস্যা হয়েছে। দয়া করে আবার চেষ্টা করুন।")


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/quiz কমান্ডের উত্তর দেয়। একটি র‍্যান্ডম কুইজ শুরু করে।"""
    user_id = update.effective_user.id
    user_state = get_user_state(user_id)

    if user_state['quiz_active']:
        await update.message.reply_text("আপনি ইতিমধ্যেই একটি কুইজ খেলছেন! আপনার উত্তর দিন অথবা অপেক্ষা করুন।")
        return

    random_quiz_index = random.randrange(len(QUIZZES))
    user_state['current_quiz_index'] = random_quiz_index
    user_state['quiz_active'] = True
    user_state['quiz_attempts'] = 0 # প্রতিটি নতুন কুইজের জন্য প্রচেষ্টা রিসেট

    quiz_item = QUIZZES[random_quiz_index]
    question = quiz_item["question"]
    options = quiz_item["options"]
    
    # অপশনগুলো শাফেল করা যাতে প্রতিবার একই ক্রমে না আসে
    random.shuffle(options)

    keyboard = []
    for i, option in enumerate(options):
        # Callback data ফরম্যাট: quiz_answer_<quiz_index>_<option_text>
        # এখানে আমরা option_text সরাসরি না দিয়ে, তার শাফেল করা ইনডেক্স ব্যবহার করতে পারি
        keyboard.append([InlineKeyboardButton(option, callback_data=f"quiz_answer_{random_quiz_index}_{option}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"**কুইজ শুরু!**\n\n{question}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    logger.info(f"User {user_id} started quiz {random_quiz_index}.")

async def quiz_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """কুইজের ইনলাইন বাটন প্রেস হ্যান্ডেল করে।"""
    query = update.callback_query
    await query.answer() # কলব্যাক ক্যোয়ারি অ্যান্সার করা আবশ্যক

    user_id = query.from_user.id
    user_state = get_user_state(user_id)

    if not user_state['quiz_active']:
        await query.edit_message_text("এই কুইজ সেশনটি আর সক্রিয় নেই। নতুন কুইজের জন্য /quiz কমান্ড ব্যবহার করুন।")
        return

    data_parts = query.data.split('_')
    if len(data_parts) < 3 or data_parts[0] != "quiz" or data_parts[1] != "answer":
        await query.edit_message_text("কিছু একটা ভুল হয়েছে। দয়া করে আবার চেষ্টা করুন।")
        return
    
    quiz_index_str = data_parts[2]
    selected_option = "_".join(data_parts[3:]) # অপশনে আন্ডারস্কোর থাকলে তা ঠিকভাবে নেওয়ার জন্য

    try:
        quiz_index = int(quiz_index_str)
    except ValueError:
        await query.edit_message_text("কিছু একটা ভুল হয়েছে। কুইজ আইডি সঠিক নয়।")
        logger.error(f"Invalid quiz index in callback data: {query.data}")
        return

    if quiz_index != user_state['current_quiz_index']:
        await query.edit_message_text("আপনি ভুল কুইজে উত্তর দেওয়ার চেষ্টা করছেন। নতুন কুইজের জন্য /quiz ব্যবহার করুন।")
        return

    quiz_item = QUIZZES[quiz_index]
    correct_answer = quiz_item["answer"]

    user_state['quiz_attempts'] += 1

    if selected_option == correct_answer:
        user_state['quiz_score'] += 1
        await query.edit_message_text(f"✅ সঠিক উত্তর! আপনি জিতলেন!\n\nআপনার বর্তমান স্কোর: {user_state['quiz_score']}\nনতুন কুইজের জন্য /quiz ব্যবহার করুন।")
        user_state['quiz_active'] = False
        user_state['current_quiz_index'] = -1
        logger.info(f"User {user_id} answered quiz {quiz_index} correctly.")
    else:
        if user_state['quiz_attempts'] < 2: # ২ বার চেষ্টা করার সুযোগ
            await query.edit_message_text(f"❌ ভুল উত্তর! আবার চেষ্টা করুন।\n\nপ্রশ্ন:\n{quiz_item['question']}", reply_markup=query.message.reply_markup)
            logger.info(f"User {user_id} answered quiz {quiz_index} incorrectly (attempt {user_state['quiz_attempts']}).")
        else:
            await query.edit_message_text(f"❌ ভুল উত্তর! সঠিক উত্তরটি হলো: `{correct_answer}`\n\nআপনার বর্তমান স্কোর: {user_state['quiz_score']}\nনতুন কুইজের জন্য /quiz ব্যবহার করুন।")
            user_state['quiz_active'] = False
            user_state['current_quiz_index'] = -1
            logger.info(f"User {user_id} failed quiz {quiz_index} after multiple attempts.")


async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/image কমান্ডের উত্তর দেয়। টেক্সট থেকে ছবি তৈরি করে।"""
    if not context.args:
        await update.message.reply_text("দয়া করে `/image` এর পরে কিছু টেক্সট দিন। যেমন: `/image আমি বাংলাদেশ`")
        return

    text_to_draw = " ".join(context.args)
    
    # ছবির সেটিংস
    img_width, img_height = 800, 400
    background_color = (30, 30, 50) # গাঢ় নীল-বেগুনি
    text_color = (255, 255, 255) # সাদা
    padding = 20 # টেক্সট বর্ডার থেকে কিছুটা দূরে রাখার জন্য

    # একটি ছবি তৈরি করুন
    img = Image.new('RGB', (img_width, img_height), color = background_color)
    d = ImageDraw.Draw(img)

    try:
        # ফন্ট লোড করুন। আপনার প্রজেক্টের রুট ডিরেক্টরিতে 'arial.ttf' ফাইলটি রাখুন।
        # যদি ফাইলটি না থাকে, তাহলে PIL এর ডিফল্ট ফন্ট ব্যবহার করা হবে।
        font_path = "arial.ttf" 
        font_size = 50
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
            logger.warning("arial.ttf font not found, using default font. Image quality might be affected.")
            # ডিফল্ট ফন্টের জন্য ফন্ট সাইজ কমানো যেতে পারে
            font_size = 20 
    except Exception as e:
        logger.error(f"Error loading font for image: {e}")
        font = ImageFont.load_default() # ফলব্যাক: ডিফল্ট ফন্ট ব্যবহার করুন
        font_size = 20


    # টেক্সটকে একাধিক লাইনে বিভক্ত করা যদি এটি খুব লম্বা হয়
    lines = []
    if font != ImageFont.load_default(): # কাস্টম ফন্টের জন্য ভালো ওয়ার্ড র‍্যাপ চেষ্টা
        words = text_to_draw.split(' ')
        current_line = []
        for word in words:
            test_line = " ".join(current_line + [word])
            # new getbbox method
            bbox = d.textbbox((0,0), test_line, font=font)
            test_line_width = bbox[2] - bbox[0]
            if test_line_width < img_width - 2 * padding:
                current_line.append(word)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
    else: # ডিফল্ট ফন্টের জন্য সহজ ওয়ার্ড র‍্যাপ (কম নির্ভুল)
        # একটা আনুমানিক অক্ষর সীমা
        char_limit_per_line = int((img_width - 2 * padding) / (font_size * 0.6)) # আনুমানিক অক্ষর প্রস্থ
        temp_text = text_to_draw
        while len(temp_text) > char_limit_per_line:
            break_point = temp_text[:char_limit_per_line].rfind(' ')
            if break_point == -1 or break_point == 0: # নো স্পেস বা প্রথম অক্ষরই ব্রেক
                break_point = char_limit_per_line
            lines.append(temp_text[:break_point].strip())
            temp_text = temp_text[break_point:].strip()
        lines.append(temp_text)

    # সব লাইনের মোট উচ্চতা গণনা
    total_text_height = 0
    for line in lines:
        bbox = d.textbbox((0, 0), line, font=font)
        total_text_height += (bbox[3] - bbox[1]) + 5 # 5 পিক্সেল লাইন স্পেসিং

    start_y = (img_height - total_text_height) / 2 # প্রথম লাইনের Y পজিশন

    for line in lines:
        bbox = d.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        text_height_line = bbox[3] - bbox[1]

        x = (img_width - text_width) / 2
        d.text((x, start_y), line, font=font, fill=text_color)
        start_y += text_height_line + 5 # পরবর্তী লাইনের জন্য Y পজিশন আপডেট

    # ছবিকে বাইট স্ট্রিম হিসেবে সংরক্ষণ করুন
    bio = io.BytesIO()
    img.save(bio, 
