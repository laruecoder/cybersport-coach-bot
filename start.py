import os
import sys

for var in list(os.environ.keys()):
    if 'proxy' in var.lower() or var in ['ALL_PROXY', 'HTTP_PROXY', 'HTTPS_PROXY', 'SOCKS_PROXY']:
        del os.environ[var]

from config import BOT_TOKEN, STEAM_API_KEY
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from dota2_api import Dota2API
from cs2_api import CS2API
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

dota_api = Dota2API()
cs2_api = CS2API(STEAM_API_KEY)
user_states = {}

class CyberCoachBot:
    def __init__(self):
        request = HTTPXRequest(proxy="socks5://127.0.0.1:10808")
        self.app = ApplicationBuilder().token(BOT_TOKEN).request(request).build()
        self._register_handlers()
    
    def _register_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("dota", self.dota_cmd))
        self.app.add_handler(CommandHandler("cs2", self.cs2_cmd))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start(self, update, context):
        keyboard = [
            [InlineKeyboardButton("Dota 2", callback_data='game_dota')],
            [InlineKeyboardButton("CS2", callback_data='game_cs2')]
        ]
        await update.message.reply_text(
            "CyberSport Coach\nChoose a game:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def help_command(self, update, context):
        await update.message.reply_text("Commands: /start /dota /cs2 /help")
    
    async def dota_cmd(self, update, context):
        user_states[update.effective_user.id] = 'dota'
        await update.message.reply_text("Send Steam ID for Dota 2 analysis:")
    
    async def cs2_cmd(self, update, context):
        user_states[update.effective_user.id] = 'cs2'
        await update.message.reply_text("Send Steam profile link (must be public):")
    
    async def button_handler(self, update, context):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if query.data == 'game_dota':
            user_states[user_id] = 'dota'
            await query.edit_message_text("Send Steam ID for Dota 2 analysis:")
        elif query.data == 'game_cs2':
            user_states[user_id] = 'cs2'
            await query.edit_message_text("Send Steam profile link (must be public):")
    
    async def handle_message(self, update, context):
        user_id = update.effective_user.id
        text = update.message.text.strip()
        state = user_states.get(user_id)
        
        if state == 'dota':
            await update.message.reply_text("Analyzing Dota 2...")
            matches = dota_api.get_recent_matches(text)
            if matches:
                a = dota_api.analyze_performance(matches)
                resp = f"Games: {a['matches_analyzed']}\nKDA: {a['avg_kills']}/{a['avg_deaths']}/{a['avg_assists']}\nGPM: {a['avg_gpm']}\nWinrate: {a['winrate']}%\n\nTips:\n"
                for t in a['tips']:
                    resp += f"{t}\n"
                await update.message.reply_text(resp)
            else:
                await update.message.reply_text("Failed to load matches.")
        
        elif state == 'cs2':
            await update.message.reply_text("Loading CS2 profile...")
            sid = cs2_api.get_steam_id_from_url(text)
            if sid:
                summary = cs2_api.get_player_summary(sid)
                if summary:
                    games = cs2_api.get_owned_games(sid)
                    analysis = cs2_api.analyze_cs2_profile(summary, games)
                    
                    resp = f"*{summary['nickname']}*\n"
                    resp += f"Country: {summary['country']}\n"
                    resp += f"Created: {summary['creation_date']}\n"
                    resp += f"Status: {summary['status']}\n"
                    resp += f"Profile: {summary['visibility']}\n"
                    resp += f"Last online: {summary['last_online']}\n"
                    
                    if analysis['cs2_info']:
                        resp += analysis['cs2_info']
                    
                    if games and games['top_games']:
                        resp += "\n\n*Top Games:*\n"
                        for g in games['top_games'][:3]:
                            resp += f"- {g['name']}: {g['hours']}h\n"
                    
                    resp += "\n*CS2 Training Tips:*\n"
                    for tip in analysis['tips'][:4]:
                        resp += f"- {tip}\n"
                    
                    await update.message.reply_text(resp, parse_mode='Markdown')
                else:
                    await update.message.reply_text("Profile not found or completely private.")
            else:
                await update.message.reply_text("Invalid link. Use: steamcommunity.com/id/USERNAME")
        else:
            await update.message.reply_text("Use /start to begin.")
    
    def run(self):
        logger.info("Starting CyberSport Coach...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = CyberCoachBot()
    bot.run()