import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.dirname(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tele_project.settings')

import django
django.setup()

from asgiref.sync import sync_to_async
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

User = get_user_model()

# States for the conversation
PHONE, EMAIL, NAME = range(3)

# Настройка токена (замените на ваш токен от BotFather)
TOKEN = '7662316234:AAEqpQZ5rHYW8a7JN9FS2-UBr_Z48saPB_I'

# Синхронные методы с асинхронной оберткой
create_user = sync_to_async(User.objects.create_user)
get_or_create_user_profile = sync_to_async(UserProfile.objects.get_or_create)
get_user_by_username = sync_to_async(User.objects.get)

async def start(update, context):
    # Проверяем, существует ли пользователь с данным Telegram ID
    telegram_user_id = update.effective_user.id
    user_profile = await sync_to_async(UserProfile.objects.filter(telegram_user_id=telegram_user_id).first)()
    
    if user_profile:
        # Пользователь уже зарегистрирован
        user = await get_user_by_username(username=user_profile.user.username)
        await welcome_registered_user(update, context, user)
        return ConversationHandler.END
    
    # Начинаем процесс регистрации
    await update.message.reply_text(
        "Привет! Давайте зарегистрируем вас. \n"
        "Пожалуйста, введите ваш номер телефона в формате +7XXXXXXXXXX:"
    )
    return PHONE

async def process_phone(update, context):
    phone_number = update.message.text.strip()
    
    # Простая базовая валидация номера телефона
    if not phone_number.startswith('+7') or len(phone_number) != 12:
        await update.message.reply_text(
            "Неверный формат номера телефона. Пожалуйста, введите номер в формате +7XXXXXXXXXX:"
        )
        return PHONE
    
    context.user_data['phone_number'] = phone_number
    
    await update.message.reply_text("Теперь введите ваш email:")
    return EMAIL

async def process_email(update, context):
    email = update.message.text.strip()
    
    try:
        validate_email(email)
    except ValidationError:
        await update.message.reply_text("Неверный формат email. Пожалуйста, введите корректный email:")
        return EMAIL
    
    context.user_data['email'] = email
    
    await update.message.reply_text("Введите ваше имя:")
    return NAME

async def process_name(update, context):
    name = update.message.text.strip()
    
    if len(name) < 2:
        await update.message.reply_text("Пожалуйста, введите корректное имя:")
        return NAME
    
    # Создаем пользователя
    try:
        user = await create_user(
            username=context.user_data['email'],
            email=context.user_data['email'],
            first_name=name,
            phone_number=context.user_data['phone_number']
        )
        
        # Создаем профиль пользователя с Telegram ID
        user_profile, _ = await get_or_create_user_profile(user=user)
        user_profile.telegram_user_id = update.effective_user.id
        await sync_to_async(user_profile.save)()
        
        await welcome_registered_user(update, context, user)
        return ConversationHandler.END
    
    except Exception as e:
        await update.message.reply_text(f"Ошибка регистрации: {str(e)}")
        return ConversationHandler.END

async def welcome_registered_user(update, context, user):
    keyboard = [
        [InlineKeyboardButton("🚗 Машины", callback_data='cars')],
        [InlineKeyboardButton("🛒 Корзина", callback_data='view_cart')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = f"Привет, {user.first_name}! 👋 Чем могу помочь?"
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    else:
        query = update.callback_query
        await query.message.reply_text(welcome_text, reply_markup=reply_markup)

async def cancel(update, context):
    await update.message.reply_text("Регистрация отменена.")
    return ConversationHandler.END

def main():
    application = Application.builder().token(TOKEN).build()

    # Создаем ConversationHandler для регистрации
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_phone)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_email)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_name)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)

    # Остальные обработчики из предыдущего кода
    application.add_handler(CallbackQueryHandler(show_makes, pattern='^cars$'))
    application.add_handler(CallbackQueryHandler(show_models, pattern='^make_'))
    application.add_handler(CallbackQueryHandler(car_details, pattern='^car_'))
    application.add_handler(CallbackQueryHandler(add_to_cart_handler, pattern='^add_to_cart_'))
    application.add_handler(CallbackQueryHandler(view_cart, pattern='^view_cart$'))
    application.add_handler(CallbackQueryHandler(go_back, pattern='^back_to_'))

    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()