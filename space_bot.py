import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "ВАШ_ТОКЕН_ЗДЕСЬ")

ITEMS = {
    "main_1": {"name": "303 Roland", "category": "main", "taken_by": None},
    "main_2": {"name": "Такая штучка", "category": "main", "taken_by": None},
    "main_3": {"name": "Другая штучка", "category": "main", "taken_by": None},
    "hallway_1": {"name": "Mini jack", "category": "hallway", "taken_by": None},
    "hallway_2": {"name": "Плоскогубцы", "category": "hallway", "taken_by": None},
    "hallway_3": {"name": "Шнур", "category": "hallway", "taken_by": None},
    "garage_1": {"name": "Пила", "category": "garage", "taken_by": None},
    "garage_2": {"name": "Топор", "category": "garage", "taken_by": None},
    "garage_3": {"name": "Дрель", "category": "garage", "taken_by": None},
    "cowork_1": {"name": "Книжка про музыку", "category": "coworking", "taken_by": None},
    "cowork_2": {"name": "Книжка про приколы", "category": "coworking", "taken_by": None},
    "cowork_3": {"name": "Паяльник", "category": "coworking", "taken_by": None},
}

CATEGORIES = {
    "main":      "Main",
    "coworking": "Coworking",
    "garage":    "Garage",
    "hallway":   "Hallway",
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_user_name(user) -> str:
    if user.username:
        return f"@{user.username}"
    full = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return full or f"User#{user.id}"


def get_items_by_category(category: str) -> dict:
    return {k: v for k, v in ITEMS.items() if v["category"] == category}


def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"cat_{cat}")]
        for cat, label in CATEGORIES.items()
    ]
    return InlineKeyboardMarkup(buttons)


def items_keyboard(category: str, user_id: int):
    items = get_items_by_category(category)
    buttons = []
    for item_id, item in items.items():
        if item["taken_by"] is None:
            label = item["name"]
        elif item["taken_by"]["id"] == user_id:
            label = f"{item['name']} — у меня"
        else:
            label = f"{item['name']} — {item['taken_by']['name']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"item_{item_id}")])
    buttons.append([InlineKeyboardButton("← Back", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(buttons)


def item_action_keyboard(item_id: str, user_id: int):
    item = ITEMS[item_id]
    category = item["category"]
    buttons = []
    if item["taken_by"] is None:
        buttons.append([InlineKeyboardButton("✋ Take", callback_data=f"take_{item_id}")])
    elif item["taken_by"]["id"] == user_id:
        buttons.append([InlineKeyboardButton("↩️ Return", callback_data=f"return_{item_id}")])
    buttons.append([InlineKeyboardButton("← Back", callback_data=f"cat_{category}")])
    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Choose a space:", reply_markup=main_menu_keyboard())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    user_id = user.id
    user_name = get_user_name(user)

    if data == "back_to_menu":
        await query.edit_message_text("Choose a space:", reply_markup=main_menu_keyboard())

    elif data.startswith("cat_"):
        category = data[4:]
        cat_label = CATEGORIES.get(category, category)
        items = get_items_by_category(category)
        taken = sum(1 for i in items.values() if i["taken_by"] is not None)
        free = len(items) - taken
        text = f"{cat_label}  •  {free} available, {taken} taken"
        await query.edit_message_text(text, reply_markup=items_keyboard(category, user_id))

    elif data.startswith("item_"):
        item_id = data[5:]
        item = ITEMS.get(item_id)
        if not item:
            await query.edit_message_text("Item not found.")
            return
        name = item["name"]
        if item["taken_by"] is None:
            status = "✅ In space"
        elif item["taken_by"]["id"] == user_id:
            status = "🔄 You have it"
        else:
            status = f"❌ Taken by {item['taken_by']['name']}"
        text = f"*{name}*\n\n{status}"
        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=item_action_keyboard(item_id, user_id))

    elif data.startswith("take_"):
        item_id = data[5:]
        item = ITEMS.get(item_id)
        if item["taken_by"] is not None:
            await query.answer(f"Already taken by {item['taken_by']['name']}", show_alert=True)
            return
        ITEMS[item_id]["taken_by"] = {"id": user_id, "name": user_name}
        text = f"✋ You took: *{item['name']}*"
        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=item_action_keyboard(item_id, user_id))

    elif data.startswith("return_"):
        item_id = data[7:]
        item = ITEMS.get(item_id)
        if item["taken_by"] is None:
            await query.answer("Already in space!", show_alert=True)
            return
        if item["taken_by"]["id"] != user_id:
            await query.answer("You didn't take this item!", show_alert=True)
            return
        ITEMS[item_id]["taken_by"] = None
        text = f"↩️ Returned: *{item['name']}*\n\nThanks!"
        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=item_action_keyboard(item_id, user_id))


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    logger.info("Bot started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
