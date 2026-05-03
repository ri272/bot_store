import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
import database as db

# --- កន្លែងកំណត់ព័ត៌មានផ្ទាល់ខ្លួន ---
API_TOKEN = '8778038862:AAHFVrlAn27UvirkB4yFPal4-9lWBxnGNpY'  # ប្ដូរ Bot Token ពី @BotFather
ADMIN_ID = 1104788759              # ប្ដូរ ID របស់អ្នកពី @userinfobot
QR_IMAGE_PATH = 'khqr.jpg'   # ដាក់រូបភាព QR ក្នុង Folder តែមួយ

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- State Management ---
class OrderState(StatesGroup):
    waiting_for_screenshot = State()

class AdminState(StatesGroup):
    waiting_for_name = State()
    waiting_for_price = State()
    waiting_for_keys = State()

# --- វចនានុក្រមភាសា ---
STRINGS = {
    'km': {
        'welcome': "ស្វាគមន៍មកកាន់ <b>RITH STORE LICENSE</b>! 🙏",
        'stock': "📊 ពិនិត្យស្តុក",
        'info': "👤 ព័ត៌មានខ្ញុំ",
        'history': "📜 ប្រវត្តិទិញ",
        'lang': "🌐 Change Language",
        'payment_msg': "🛒 <b>ទំនិញ: {p}</b>\n💰 តម្លៃ: <b>${pr}</b>\n\nសូមបង់ប្រាក់មក QR ខាងលើ រួចផ្ញើ Screenshot បញ្ជាក់មកទីនេះ!",
        'confirm_wait': "🙏 អរគុណ! យើងបានទទួលរូបភាពហើយ Admin កំពុងពិនិត្យ។",
        'no_stock': "សុំទោស! ផលិតផលនេះអស់ពីស្តុកហើយ។"
    },
    'en': {
        'welcome': "Welcome to <b>RITH STORE LICENSE</b>! 🙏",
        'stock': "📊 Check Stock",
        'info': "👤 My Info",
        'history': "📜 My Orders",
        'lang': "🌐 ប្តូរភាសា",
        'payment_msg': "🛒 <b>Product: {p}</b>\n💰 Price: <b>${pr}</b>\n\nPlease pay via QR and send screenshot here!",
        'confirm_wait': "🙏 Thank you! We received your screenshot. Admin is verifying.",
        'no_stock': "Sorry! Out of stock."
    }
}

def get_customer_kb(uid):
    l = db.get_user_lang(uid)
    btns = []
    products = db.get_distinct_products_in_stock()
    for name, price, count in products:
        btns.append([InlineKeyboardButton(text=f"🛒 {name} - ${price} ({count})", callback_data=f"buy:{name}")])
    
    btns.append([InlineKeyboardButton(text=STRINGS[l]['stock'], callback_data="check_stock")])
    btns.append([InlineKeyboardButton(text=STRINGS[l]['info'], callback_data="my_info"),
                 InlineKeyboardButton(text=STRINGS[l]['history'], callback_data="my_history")])
    btns.append([InlineKeyboardButton(text=STRINGS[l]['lang'], callback_data="change_lang")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

# --- មុខងារ Start & Language ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇰🇭 ភាសាខ្មែរ", callback_data="setlang_km"),
         InlineKeyboardButton(text="🇺🇸 English", callback_data="setlang_en")]
    ])
    await message.answer("Please choose your language / សូមជ្រើសរើសភាសារបស់អ្នក៖", reply_markup=kb)

@dp.callback_query(F.data.startswith("setlang_"))
async def set_lang(callback: CallbackQuery):
    l = callback.data.split("_")[1]
    db.set_user_lang(callback.from_user.id, l)
    await callback.message.edit_text(STRINGS[l]['welcome'], reply_markup=get_customer_kb(callback.from_user.id), parse_mode="HTML")

@dp.callback_query(F.data == "change_lang")
async def change_l(callback: CallbackQuery):
    await cmd_start(callback.message)

# --- មុខងារ My Info & Stock ---
@dp.callback_query(F.data == "my_info")
async def my_info(callback: CallbackQuery):
    l = db.get_user_lang(callback.from_user.id)
    total = db.get_user_stats(callback.from_user.id)
    txt = f"👤 <b>ID:</b> <code>{callback.from_user.id}</code>\n<b>Name:</b> {callback.from_user.full_name}\n<b>Total Bought:</b> {total}"
    await callback.message.answer(txt, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "check_stock")
async def check_stock(callback: CallbackQuery):
    l = db.get_user_lang(callback.from_user.id)
    stocks = db.get_distinct_products_in_stock()
    text = f"📊 <b>{STRINGS[l]['stock']}</b>\n\n"
    if not stocks: text += "Empty"
    for name, price, count in stocks:
        text += f"- {name}: {count} keys (${price})\n"
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

# --- ដំណើរការទិញទំនិញ ---
@dp.callback_query(F.data.startswith("buy:"))
async def process_buy(callback: CallbackQuery, state: FSMContext):
    l = db.get_user_lang(callback.from_user.id)
    p_name = callback.data.split(":")[1]
    key_data = db.get_available_key(p_name)
    
    if key_data:
        _, _, price = key_data
        await state.update_data(buying_product=p_name)
        try:
            qr = FSInputFile(QR_IMAGE_PATH)
            await callback.message.answer_photo(qr, caption=STRINGS[l]['payment_msg'].format(p=p_name, pr=price), parse_mode="HTML")
            await state.set_state(OrderState.waiting_for_screenshot)
        except:
            await callback.message.answer("QR Code Error! Please contact admin.")
    else:
        await callback.answer(STRINGS[l]['no_stock'], show_alert=True)
    await callback.answer()

# --- ទទួលរូបថតបង់ប្រាក់ ---
@dp.message(OrderState.waiting_for_screenshot, F.photo)
async def handle_payment_screenshot(message: types.Message, state: FSMContext):
    l = db.get_user_lang(message.from_user.id)
    data = await state.get_data()
    p_name = data.get('buying_product')
    
    key_data = db.get_available_key(p_name)
    if not key_data:
        await message.answer(STRINGS[l]['no_stock'])
        return

    key_id = key_data[0]
    username = f"@{message.from_user.username}" if message.from_user.username else "N/A"
    
    admin_caption = (
        f"🔔 <b>ការកម្ម៉ង់ថ្មី!</b>\n\n"
        f"📦 ផលិតផល: <b>{p_name}</b>\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"👤 ឈ្មោះ: {message.from_user.full_name}\n"
        f"🔗 Username: {username}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Approve & Send Key", callback_data=f"apv:{message.from_user.id}:{key_id}")]
    ])
    
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=admin_caption, reply_markup=kb, parse_mode="HTML")
    await message.answer(STRINGS[l]['confirm_wait'], parse_mode="HTML")
    await state.clear()

# --- ADMIN APPROVE (ផ្ញើ Key ស្វ័យប្រវត្តិ) ---
@dp.callback_query(F.data.startswith("apv:"))
async def admin_approve(callback: CallbackQuery):
    _, customer_id, key_id = callback.data.split(":")
    
    # ពិនិត្យក្នុង Database ម្ដងទៀតឱ្យច្បាស់
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute('SELECT license_key, product_name FROM licenses WHERE id = ? AND is_sold = 0', (key_id,))
    res = cursor.fetchone()
    conn.close()

    if res:
        l_key, p_name = res
        db.mark_as_sold(key_id, customer_id)
        
        # ផ្ញើ Key ឱ្យភ្ញៀវ
        await bot.send_message(customer_id, f"✅ <b>ការបង់ប្រាក់ត្រូវបានអនុម័ត!</b>\n📦 ផលិតផល: {p_name}\n🔑 Key: <code>{l_key}</code>", parse_mode="HTML")
        # Update សារក្នុង Chat Admin
        await callback.message.edit_caption(caption=callback.message.caption + f"\n\n✅ <b>Approved! Key Sent:</b> <code>{l_key}</code>", parse_mode="HTML")
    else:
        await callback.answer("❌ Key នេះលក់រួចហើយ ឬមាន Error!", show_alert=True)

# --- ADMIN ADD PRODUCT ---
@dp.message(Command("add"), F.from_user.id == ADMIN_ID)
async def admin_add_start(message: types.Message, state: FSMContext):
    await message.answer("🛠 <b>Admin</b>: បញ្ចូលឈ្មោះផលិតផល:")
    await state.set_state(AdminState.waiting_for_name)

@dp.message(AdminState.waiting_for_name)
async def ad_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("💰 បញ្ចូលតម្លៃ (ឧទាហរណ៍: 5.5):")
    await state.set_state(AdminState.waiting_for_price)

@dp.message(AdminState.waiting_for_price)
async def ad_price(message: types.Message, state: FSMContext):
    try:
        await state.update_data(price=float(message.text))
        await message.answer("🔑 បញ្ចូល Keys (ចុះបន្ទាត់ដើម្បីដាក់ច្រើន Key ក្នុងពេលតែមួយ):")
        await state.set_state(AdminState.waiting_for_keys)
    except: await message.answer("សូមបញ្ចូលជាលេខ!")

@dp.message(AdminState.waiting_for_keys)
async def ad_keys(message: types.Message, state: FSMContext):
    data = await state.get_data()
    keys = message.text.split('\n')
    db.add_multiple_keys(data['name'], keys, data['price'])
    await message.answer(f"✅ រក្សាទុកជោគជ័យ! {len(keys)} keys សម្រាប់ {data['name']}")
    await state.clear()

async def main():
    db.init_db()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())