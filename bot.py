# -*- coding: utf-8 -*-
import os
import asyncio
import random
import json
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from dota2_api import Dota2API
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

dota_api = Dota2API()
user_states = {}
user_mmr = {}  # user_id -> [{"mmr": 3500, "date": "2024-01-01"}, ...]
user_challenges = {}  # user_id -> {"challenge_name": True/False, ...}
user_reminders = {}  # user_id -> [{"time": datetime, "text": "..."}, ...]

# ========== DATA ==========

HEROES = [
    {"name": "Anti-Mage", "role": "Carry", "difficulty": "Low", "tip": "Farm aggressively, split push, avoid fights until Manta + Battle Fury."},
    {"name": "Axe", "role": "Initiator", "difficulty": "Low", "tip": "Blink + Berserker's Call combo. Counter Helix is your main damage."},
    {"name": "Invoker", "role": "Mid", "difficulty": "High", "tip": "Practice spell combos in lobby. Tornado + Meteor + Blast is classic."},
    {"name": "Pudge", "role": "Roamer", "difficulty": "Medium", "tip": "Early smoke ganks. Hide in trees, hook priority targets."},
    {"name": "Crystal Maiden", "role": "Support", "difficulty": "Low", "tip": "Ward key spots. Use Frostbite on jungle creeps for farm."},
    {"name": "Juggernaut", "role": "Carry", "difficulty": "Low", "tip": "Spin + TP is unkillable. Omnislash with Maelstrom procs."},
    {"name": "Rubick", "role": "Support", "difficulty": "High", "tip": "Position safely, steal big ultimates. Spell Steal has low cooldown."},
    {"name": "Shadow Fiend", "role": "Mid", "difficulty": "Medium", "tip": "Practice razes. Requiem of Souls with Blink + BKB."},
    {"name": "Lion", "role": "Support", "difficulty": "Low", "tip": "Finger of Death stacks. Buy Blink for instant Hex initiation."},
    {"name": "Storm Spirit", "role": "Mid", "difficulty": "Medium", "tip": "Manage mana carefully. Overload procs are your main damage."},
]

TERMS = {
    "роуминг": "Roaming — перемещение героя между линиями для ганков и помощи союзникам.",
    "ганг": "Gank — внезапное нападение на вражеского героя с целью убийства.",
    "стак": "Stack — накопление нескольких лагерей лесных крипов в одном месте.",
    "сплит-пуш": "Split push — давление на разные линии одновременно.",
    "тайминг": "Timing — ключевой момент, когда герой получает важный предмет и готов к драке.",
    "кда": "KDA — соотношение убийств (Kills), смертей (Deaths) и ассистов (Assists).",
    "фарм": "Farm — добыча золота через убийство крипов.",
    "денай": "Deny — добивание своего крипа, чтобы враг не получил опыт и золото.",
    "байбек": "Buyback — выкуп героя после смерти за золото.",
    "тп": "TP — Teleport, телепортация с помощью свитка Town Portal Scroll.",
    "бкб": "BKB — Black King Bar, предмет дающий иммунитет к магии.",
    "мидас": "Hand of Midas — предмет для ускорения фарма.",
    "бабочка": "Butterfly — предмет на ловкость и уклонение.",
    "радианс": "Radiance — предмет, наносящий урон по области.",
}

TRAINING_TASKS = [
    "Забей 50 ластхитов за 5 минут в пустом лобби.",
    "Сыграй одну игру на герое, которого никогда не брал.",
    "Поставь 10 вардов в нестандартных местах.",
    "Сделай стак из трёх лагерей в лесу.",
    "Посмотри реплей своего последнего матча и найди 3 свои ошибки.",
    "Потренируйся блокировать крипов на миде 5 минут.",
    "Сделай артефакт на 2 минуты раньше обычного (ориентируйся по таймингам).",
    "Сыграй игру без единой смерти.",
    "Попробуй новый билд на знакомом герое.",
    "Перед каждой дракой проверяй ману и кулдауны союзников.",
]

CHALLENGES = {
    "5_games_week": "Сыграть 5 игр за неделю",
    "3_new_heroes": "Попробовать 3 новых героя",
    "10_wards": "Поставить 10 обсервер вардов за игру",
    "zero_deaths": "Сыграть игру без смертей",
    "100_lasthits": "Сделать 100 ластхитов за игру",
}

# ========== BOT ==========

class DotaCoachBot:
    def __init__(self):
        request = HTTPXRequest()
        self.app = ApplicationBuilder().token(BOT_TOKEN).request(request).build()
        self._register_handlers()
    
    def _register_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("random", self.random_hero))
        self.app.add_handler(CommandHandler("task", self.training_task))
        self.app.add_handler(CommandHandler("terms", self.terms_list))
        self.app.add_handler(CommandHandler("mmr", self.mmr_command))
        self.app.add_handler(CommandHandler("challenge", self.challenge_command))
        self.app.add_handler(CommandHandler("remind", self.remind_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start(self, update, context):
        await update.message.reply_text(
            "🎮 *Dota 2 Coach*\n\n"
            "Отправь Steam ID для анализа матчей.\n"
            "Пример: `113372543`\n\n"
            "📋 *Команды:*\n"
            "/random — случайный герой с советами\n"
            "/task — тренировочное задание\n"
            "/terms — словарь терминов\n"
            "/mmr — отслеживание MMR\n"
            "/challenge — челленджи\n"
            "/remind — напоминание\n"
            "/help — помощь",
            parse_mode='Markdown'
        )
    
    async def help_command(self, update, context):
        await update.message.reply_text(
            "📋 *Все команды:*\n\n"
            "🎯 *Анализ матчей:* отправь Steam ID\n"
            "🦸 /random — случайный герой\n"
            "💪 /task — задание для тренировки\n"
            "📖 /terms — словарь терминов\n"
            "📊 /mmr 3500 — сохранить MMR\n"
            "📊 /mmr stats — посмотреть историю\n"
            "🏆 /challenge — список челленджей\n"
            "⏰ /remind 30min текст — напоминание\n\n"
            "Бот работает через OpenDota API.",
            parse_mode='Markdown'
        )
    
    # ===== RANDOM HERO =====
    async def random_hero(self, update, context):
        hero = random.choice(HEROES)
        resp = f"🦸 *{hero['name']}*\n"
        resp += f"🎭 Роль: {hero['role']}\n"
        resp += f"📈 Сложность: {hero['difficulty']}\n"
        resp += f"💡 Совет: {hero['tip']}"
        await update.message.reply_text(resp, parse_mode='Markdown')
    
    # ===== TRAINING TASK =====
    async def training_task(self, update, context):
        task = random.choice(TRAINING_TASKS)
        await update.message.reply_text(f"💪 *Задание:*\n{task}", parse_mode='Markdown')
    
    # ===== TERMS =====
    async def terms_list(self, update, context):
        term_names = list(TERMS.keys())
        terms_text = ", ".join(term_names)
        await update.message.reply_text(
            f"📖 *Доступные термины:*\n{terms_text}\n\n"
            "Отправь мне любой термин, и я объясню его.",
            parse_mode='Markdown'
        )
    
    # ===== MMR =====
    async def mmr_command(self, update, context):
        user_id = update.effective_user.id
        args = context.args
        
        if not args:
            await update.message.reply_text(
                "📊 *MMR Tracking*\n"
                "/mmr 3500 — сохранить текущий MMR\n"
                "/mmr stats — показать историю\n"
                "/mmr graph — показать прогресс",
                parse_mode='Markdown'
            )
            return
        
        if args[0].lower() == 'stats':
            if user_id not in user_mmr or not user_mmr[user_id]:
                await update.message.reply_text("У тебя пока нет записей MMR. Используй /mmr 3500")
                return
            
            history = user_mmr[user_id]
            resp = "📊 *История MMR:*\n"
            for entry in history[-10:]:
                resp += f"• {entry['mmr']} — {entry['date']}\n"
            
            if len(history) > 1:
                first = history[0]['mmr']
                last = history[-1]['mmr']
                diff = last - first
                emoji = "📈" if diff > 0 else "📉" if diff < 0 else "➡️"
                resp += f"\n{emoji} Изменение: {'+' if diff > 0 else ''}{diff} MMR"
            
            await update.message.reply_text(resp, parse_mode='Markdown')
        
        elif args[0].isdigit():
            mmr = int(args[0])
            if user_id not in user_mmr:
                user_mmr[user_id] = []
            user_mmr[user_id].append({
                "mmr": mmr,
                "date": datetime.now().strftime("%d.%m.%Y")
            })
            await update.message.reply_text(f"✅ MMR {mmr} сохранён!")
    
    # ===== CHALLENGES =====
    async def challenge_command(self, update, context):
        args = context.args
        user_id = update.effective_user.id
        
        if user_id not in user_challenges:
            user_challenges[user_id] = {}
        
        if not args:
            resp = "🏆 *Челленджи:*\n"
            for key, desc in CHALLENGES.items():
                status = "✅" if user_challenges[user_id].get(key) else "⬜"
                resp += f"{status} {desc}\n"
            resp += "\nОтметь выполненный: `/challenge done 5_games_week`"
            await update.message.reply_text(resp, parse_mode='Markdown')
        
        elif args[0] == 'done' and len(args) > 1:
            challenge_key = args[1]
            if challenge_key in CHALLENGES:
                user_challenges[user_id][challenge_key] = True
                await update.message.reply_text(f"✅ Челлендж '{CHALLENGES[challenge_key]}' выполнен!")
            else:
                await update.message.reply_text("Неизвестный челлендж. Используй /challenge для списка.")
    
    # ===== REMINDER =====
    async def remind_command(self, update, context):
        user_id = update.effective_user.id
        args = context.args
        
        if not args:
            await update.message.reply_text(
                "⏰ *Напоминания*\n"
                "/remind 30min Покушать\n"
                "/remind 2h Тренировка\n"
                "/remind list — список активных",
                parse_mode='Markdown'
            )
            return
        
        if args[0] == 'list':
            if user_id not in user_reminders or not user_reminders[user_id]:
                await update.message.reply_text("Нет активных напоминаний.")
                return
            resp = "⏰ *Активные напоминания:*\n"
            for r in user_reminders[user_id]:
                resp += f"• {r['text']} — в {r['time'].strftime('%H:%M')}\n"
            await update.message.reply_text(resp, parse_mode='Markdown')
            return
        
        # Parse time like "30min" or "2h"
        time_str = args[0]
        reminder_text = " ".join(args[1:]) if len(args) > 1 else "Напоминание"
        
        minutes = 0
        if time_str.endswith('min'):
            try:
                minutes = int(time_str.replace('min', ''))
            except:
                pass
        elif time_str.endswith('h'):
            try:
                minutes = int(time_str.replace('h', '')) * 60
            except:
                pass
        
        if minutes <= 0:
            await update.message.reply_text("Укажи время: 30min или 2h")
            return
        
        reminder_time = datetime.now() + timedelta(minutes=minutes)
        
        if user_id not in user_reminders:
            user_reminders[user_id] = []
        
        user_reminders[user_id].append({
            "time": reminder_time,
            "text": reminder_text
        })
        
        await update.message.reply_text(
            f"⏰ Напомню про '{reminder_text}' в {reminder_time.strftime('%H:%M')}"
        )
        
        # Schedule the reminder
        asyncio.create_task(self._send_reminder(update, context, user_id, reminder_time, reminder_text))
    
    async def _send_reminder(self, update, context, user_id, reminder_time, text):
        delay = (reminder_time - datetime.now()).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⏰ *Напоминание:* {text}",
                parse_mode='Markdown'
            )
    
    # ===== HANDLE MESSAGES (Steam ID or Terms) =====
    async def handle_message(self, update, context):
        text = update.message.text.strip()
        
        # Check if it's a term
        if text.lower() in TERMS:
            await update.message.reply_text(f"📖 *{text}:*\n{TERMS[text.lower()]}", parse_mode='Markdown')
            return
        
        # Check if it's a Steam ID (numbers only, 7-9 digits)
        if text.isdigit() and len(text) >= 7:
            await update.message.reply_text("🔍 Анализирую матчи Dota 2...")
            matches = dota_api.get_recent_matches(text)
            if not matches:
                await update.message.reply_text(
                    "❌ Матчи не найдены.\n"
                    "• Проверь Steam ID\n"
                    "• Профиль может быть скрыт\n"
                    "• Нет недавних игр"
                )
                return
            
            a = dota_api.analyze_performance(matches)
            resp = f"📊 *Анализ {a['matches_analyzed']} игр:*\n\n"
            resp += f"⚔️ KDA: {a['avg_kills']}/{a['avg_deaths']}/{a['avg_assists']}\n"
            resp += f"💰 Средний GPM: {a['avg_gpm']}\n"
            resp += f"🏆 Винрейт: {a['winrate']}%\n\n"
            resp += "📋 *Советы:*\n"
            for t in a['tips']:
                resp += f"• {t}\n"
            await update.message.reply_text(resp, parse_mode='Markdown')
        
        else:
            await update.message.reply_text(
                "Я понимаю:\n"
                "• Steam ID (цифры) — анализ матчей\n"
                "• Термины Dota 2 — объяснение\n\n"
                "Используй /help для списка команд."
            )

async def main():
    bot = DotaCoachBot()
    logger.info("Starting Dota 2 Coach...")
    await bot.app.initialize()
    await bot.app.start()
    await bot.app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())