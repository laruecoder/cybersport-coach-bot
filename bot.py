import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from config import BOT_TOKEN, STEAM_API_KEY
from dota2_api import Dota2API
from cs2_api import CS2API

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация API
dota_api = Dota2API()
cs2_api = CS2API(STEAM_API_KEY)

# Хранилище состояний пользователей
user_states = {}


class CyberCoachBot:
    def __init__(self):
        self.app = Application.builder().token(BOT_TOKEN).build()
        self._register_handlers()

    def _register_handlers(self):
        """Регистрирует все обработчики команд"""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("dota", self.dota_menu))
        self.app.add_handler(CommandHandler("cs2", self.cs2_menu))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_message
        ))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Приветственное сообщение с выбором игры"""
        keyboard = [
            [InlineKeyboardButton("🎮 Dota 2", callback_data='game_dota')],
            [InlineKeyboardButton("🔫 CS2", callback_data='game_cs2')],
            [InlineKeyboardButton("ℹ️ О боте", callback_data='about')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🏆 *CyberSport Coach — твой персональный тренер*\n\n"
            "Анализирую твою игру, нахожу слабые места и помогаю "
            "подняться на новый уровень!\n\n"
            "Выбери игру для начала:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Справка по командам"""
        help_text = """
🎮 *Доступные команды:*

/start — Главное меню
/dota — Меню Dota 2 анализатора
/cs2 — Меню CS2 анализатора
/help — Это сообщение

📊 *Как пользоваться:*
1. Выбери игру
2. Отправь ссылку на Steam-профиль
3. Получи детальный анализ и советы!

⚠️ *Важно:* 
- Для CS2 профиль должен быть публичным
- Для Dota 2 используй OpenDota API (публичные данные)
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def dota_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню анализа Dota 2"""
        keyboard = [
            [InlineKeyboardButton("📊 Анализ последних игр", callback_data='dota_analyze')],
            [InlineKeyboardButton("👤 Поиск игрока", callback_data='dota_find')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🎮 *Dota 2 Анализатор*\n"
            "Выбери действие:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def cs2_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню анализа CS2"""
        keyboard = [
            [InlineKeyboardButton("📊 Полная статистика", callback_data='cs2_stats')],
            [InlineKeyboardButton("🎯 Анализ аима", callback_data='cs2_aim')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🔫 *CS2 Анализатор*\n"
            "Выбери действие:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()

        if query.data == 'game_dota':
            await query.edit_message_text(
                "🎮 Отлично! Отправь мне ссылку на Steam-профиль "
                "(например, https://steamcommunity.com/id/твойник)\n"
                "Или 32-битный Steam ID для анализа Dota 2.",
                parse_mode='Markdown'
            )
            user_states[query.from_user.id] = 'awaiting_dota_profile'

        elif query.data == 'game_cs2':
            await query.edit_message_text(
                "🔫 Отлично! Отправь мне ссылку на Steam-профиль "
                "(например, https://steamcommunity.com/id/твойник)\n"
                "⚠️ Профиль должен быть *публичным*!",
                parse_mode='Markdown'
            )
            user_states[query.from_user.id] = 'awaiting_cs2_profile'

        elif query.data == 'back_main':
            keyboard = [
                [InlineKeyboardButton("🎮 Dota 2", callback_data='game_dota')],
                [InlineKeyboardButton("🔫 CS2", callback_data='game_cs2')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "Главное меню. Выбери игру:",
                reply_markup=reply_markup
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        user_id = update.effective_user.id
        message_text = update.message.text.strip()

        # Проверяем состояние пользователя
        state = user_states.get(user_id)

        if not state:
            await update.message.reply_text(
                "Используй /start для начала работы с ботом."
            )
            return

        # Обработка в зависимости от состояния
        if 'dota' in state:
            await self._process_dota(update, message_text)
        elif 'cs2' in state:
            await self._process_cs2(update, message_text)

    async def _process_dota(self, update: Update, message_text: str):
        """Обрабатывает запросы по Dota 2"""
        await update.message.reply_text("🔍 Анализирую твои матчи в Dota 2...")

        # Определяем Steam ID
        steam_id = message_text
        if 'steamcommunity.com' in message_text:
            await update.message.reply_text(
                "Для Dota 2 используй 32-битный Steam ID. "
                "Можешь найти его в игре или на dotabuff.com"
            )
            return

        # Получаем данные игрока
        player = dota_api.get_player_by_steam_id(steam_id)
        if not player:
            await update.message.reply_text(
                "❌ Игрок не найден. Проверь Steam ID."
            )
            return

        # Получаем последние матчи
        matches = dota_api.get_recent_matches(steam_id)
        if not matches:
            await update.message.reply_text(
                "📭 Не удалось загрузить матчи. Возможно, профиль скрыт."
            )
            return

        # Анализируем
        analysis = dota_api.analyze_performance(matches)

        # Формируем ответ
        response = f"👤 *{player['nickname']}*\n\n"
        response += f"📊 *Анализ последних {analysis['matches_analyzed']} игр:*\n\n"
        response += f"⚔️ Средний KDA: {analysis['avg_kills']}/{analysis['avg_deaths']}/{analysis['avg_assists']}\n"
        response += f"💰 Средний GPM: {analysis['avg_gpm']}\n"
        response += f"🏆 Винрейт: {analysis['winrate']}%\n\n"
        response += "*🎯 Рекомендации:*\n"
        for tip in analysis['tips']:
            response += f"{tip}\n"

        await update.message.reply_text(response, parse_mode='Markdown')

    async def _process_cs2(self, update: Update, message_text: str):
        """Обрабатывает запросы по CS2"""
        await update.message.reply_text("🔍 Загружаю статистику CS2...")

        # Получаем Steam ID из URL или напрямую
        steam_id = cs2_api.get_steam_id_from_url(message_text)
        if not steam_id:
            await update.message.reply_text(
                "❌ Неверная ссылка на профиль. Отправь ссылку вида:\n"
                "https://steamcommunity.com/id/твойник"
            )
            return

        # Получаем статистику
        stats = cs2_api.get_player_stats(steam_id)
        if not stats:
            await update.message.reply_text(
                "❌ Не удалось получить статистику. Убедись, что:\n"
                "1. Профиль Steam публичный\n"
                "2. У тебя есть часы игры в CS2\n"
                "3. Ты не скрыл статистику в настройках приватности"
            )
            return

        # Анализируем
        analysis = cs2_api.analyze_performance(stats)

        # Формируем ответ
        response = "🔫 *CS2 Статистика*\n\n"
        response += f"📊 *Общая статистика:*\n"
        response += f"⚔️ K/D: {stats['kd_ratio']}\n"
        response += f"🎯 Headshot %: {stats['headshot_pct']}%\n"
        response += f"🏆 Винрейт: {stats['winrate']}%\n"
        response += f"💀 Всего убийств: {stats['total_kills']}\n"
        response += f"⭐ MVP: {stats['mvps']}\n"
        response += f"📈 Матчей сыграно: {stats['total_matches']}\n\n"
        response += f"🎯 *Точность:* {stats['accuracy']}%\n"
        response += f"💣 Поставлено бомб: {stats['bombs_planted']}\n\n"
        response += "*📋 Рекомендации тренера:*\n"
        for tip in analysis['tips']:
            response += f"{tip}\n"

        await update.message.reply_text(response, parse_mode='Markdown')

    def run(self):
        """Запускает бота"""
        logger.info("Запуск CyberSport Coach...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    bot = CyberCoachBot()
    bot.run()