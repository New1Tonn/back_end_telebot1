import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.dirname(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tele_project.settings')

import django
django.setup()

from asgiref.sync import sync_to_async
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from tele_app.models import Car, UserProfile

# Настройка токена (замените на ваш токен от BotFather)
TOKEN = '7662316234:AAEqpQZ5rHYW8a7JN9FS2-UBr_Z48saPB_I'

# Обертки для методов Django ORM
get_car_makes = sync_to_async(lambda: list(Car.objects.values_list('make', flat=True).distinct()))
filter_cars_by_make = sync_to_async(lambda make: list(Car.objects.filter(make=make)))
get_car_by_id = sync_to_async(Car.objects.get)

# Получение корзины пользователя
async def get_user_cart(user_id):
    user_profile, _ = await sync_to_async(UserProfile.objects.get_or_create)(user_id=user_id)
    return await sync_to_async(list)(user_profile.cart.all())

# Добавление машины в корзину
async def add_to_cart(user_id, car):
    user_profile, _ = await sync_to_async(UserProfile.objects.get_or_create)(user_id=user_id)
    await sync_to_async(user_profile.cart.add)(car)
    await sync_to_async(user_profile.save)()

# Получение общей стоимости корзины
async def get_cart_total(user_id):
    user_profile, _ = await sync_to_async(UserProfile.objects.get_or_create)(user_id=user_id)
    cars_in_cart = await sync_to_async(list)(user_profile.cart.all())
    return sum([car.price for car in cars_in_cart])

# Команда /start
async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("🚗 Машины", callback_data='cars')],
        [InlineKeyboardButton("🛒 Корзина", callback_data='view_cart')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите категорию:", reply_markup=reply_markup)

# Показ марок машин
async def show_makes(update, context):
    query = update.callback_query
    await query.answer()

    makes = await get_car_makes()
    if makes:
        keyboard = [
            [InlineKeyboardButton(make, callback_data=f'make_{make}')] for make in makes
        ]
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='back_to_start')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Выберите марку машины:", reply_markup=reply_markup)
    else:
        await query.answer("Нет доступных марок.", show_alert=True)

# Показ моделей машин
async def show_models(update, context):
    query = update.callback_query
    make = query.data.split('_')[1]
    await query.answer()

    cars = await filter_cars_by_make(make)
    if cars:
        keyboard = [
            [InlineKeyboardButton(f"{car.model} ({car.year})", callback_data=f'car_{car.id}')] for car in cars
        ]
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='back_to_makes')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=f"Выберите модель для {make}:", reply_markup=reply_markup)
    else:
        await query.answer("Нет доступных моделей для этой марки.", show_alert=True)

# Показ деталей машины
async def car_details(update, context):
    query = update.callback_query
    car_id = int(query.data.split('_')[1])
    car = await get_car_by_id(id=car_id)

    details = (f"🚗 Марка: {car.make}\n"
               f"🏎 Модель: {car.model}\n"
               f"📅 Год: {car.year}\n"
               f"💰 Цена: {car.price:,.0f} ₽")

    keyboard = [
        [InlineKeyboardButton("🛒 Добавить в корзину", callback_data=f'add_to_cart_{car.id}')],
        [InlineKeyboardButton("🔙 Назад", callback_data=f'back_to_models_{car.make}')]
    ]

    if len(car.description) > 1000:
        await query.message.reply_photo(photo=car.image, caption=details, reply_markup=InlineKeyboardMarkup(keyboard))
        await query.message.reply_text(f"📋 Полное описание:\n\n{car.description}")
    else:
        full_details = f"{details}\n📝 Описание: {car.description}"
        await query.message.reply_photo(photo=car.image, caption=full_details, reply_markup=InlineKeyboardMarkup(keyboard))

# Обработчик добавления в корзину
async def add_to_cart_handler(update, context):
    query = update.callback_query
    car_id = int(query.data.split('_')[3])
    car = await get_car_by_id(id=car_id)

    await add_to_cart(query.from_user.id, car)
    await query.answer("✅ Машина добавлена в корзину!")

# Просмотр корзины
async def view_cart(update, context):
    query = update.callback_query
    await query.answer()

    cart_items = await get_user_cart(query.from_user.id)
    if cart_items:
        details = "\n".join([f"🚗 {car.model} ({car.year}) - {car.price:,.0f} ₽" for car in cart_items])
        total = await get_cart_total(query.from_user.id)
        details += f"\n\n💰 Итого: {total:,.0f} ₽"
    else:
        details = "🚫 Ваша корзина пуста."

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back_to_start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"🛒 Ваша корзина:\n{details}", reply_markup=reply_markup)

# Возврат назад
async def go_back(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == 'back_to_start':
        await start(update, context)
    elif query.data.startswith('back_to_makes'):
        await show_makes(update, context)
    elif query.data.startswith('back_to_models'):
        make = query.data.split('_')[2]
        await show_models(update, context)

# Главная функция
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(show_makes, pattern='^cars$'))
    application.add_handler(CallbackQueryHandler(show_models, pattern='^make_'))
    application.add_handler(CallbackQueryHandler(car_details, pattern='^car_'))
    application.add_handler(CallbackQueryHandler(add_to_cart_handler, pattern='^add_to_cart_'))
    application.add_handler(CallbackQueryHandler(view_cart, pattern='^view_cart$'))
    application.add_handler(CallbackQueryHandler(go_back, pattern='^back_to_'))

    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
