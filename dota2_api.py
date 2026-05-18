import requests
from typing import Dict, List, Optional


class Dota2API:
    def __init__(self):
        self.base_url = "https://api.opendota.com/api"

    def get_player_by_steam_id(self, steam_id: str) -> Optional[Dict]:
        """Получает профиль игрока по Steam ID"""
        try:
            response = requests.get(f"{self.base_url}/players/{steam_id}")
            if response.status_code == 200:
                data = response.json()
                return {
                    'player_id': steam_id,
                    'nickname': data.get('profile', {}).get('personaname', 'Unknown'),
                    'avatar': data.get('profile', {}).get('avatarfull', ''),
                    'solo_mmr': data.get('solo_competitive_rank', 0),
                    'rank_tier': data.get('rank_tier', 0),
                    'leaderboard_rank': data.get('leaderboard_rank', 0)
                }
            return None
        except Exception as e:
            print(f"Error fetching player: {e}")
            return None

    def get_recent_matches(self, player_id: str, limit: int = 5) -> List[Dict]:
        """Получает последние матчи игрока"""
        try:
            response = requests.get(
                f"{self.base_url}/players/{player_id}/recentMatches"
            )
            if response.status_code == 200:
                matches = response.json()[:limit]
                return [self._parse_match(match) for match in matches]
            return []
        except Exception as e:
            print(f"Error fetching matches: {e}")
            return []

    def _parse_match(self, match: Dict) -> Dict:
        """Парсит данные матча в читаемый формат"""
        player_slot = match.get('player_slot', 0)
        radiant_win = match.get('radiant_win', False)

        # Определяем, на какой стороне играл игрок
        is_radiant = player_slot < 128
        won = (is_radiant and radiant_win) or (not is_radiant and not radiant_win)

        return {
            'match_id': match.get('match_id'),
            'hero': match.get('hero_id', 0),
            'kills': match.get('kills', 0),
            'deaths': match.get('deaths', 0),
            'assists': match.get('assists', 0),
            'kda': round(
                (match.get('kills', 0) + match.get('assists', 0)) /
                max(1, match.get('deaths', 0)), 1
            ),
            'last_hits': match.get('last_hits', 0),
            'gpm': match.get('gold_per_min', 0),
            'xpm': match.get('xp_per_min', 0),
            'duration_min': round(match.get('duration', 0) / 60),
            'won': won,
            'hero_damage': match.get('hero_damage', 0)
        }

    def analyze_performance(self, matches: List[Dict]) -> Dict:
        """Анализирует серию матчей и выдает рекомендации"""
        if not matches:
            return {'error': 'Нет данных для анализа'}

        total_kills = sum(m.get('kills', 0) for m in matches)
        total_deaths = sum(m.get('deaths', 0) for m in matches)
        total_assists = sum(m.get('assists', 0) for m in matches)
        avg_gpm = sum(m.get('gpm', 0) for m in matches) / len(matches)
        avg_lh = sum(m.get('last_hits', 0) for m in matches) / len(matches)
        wins = sum(1 for m in matches if m.get('won'))
        winrate = (wins / len(matches)) * 100

        # Генерация советов на основе статистики
        tips = []

        if avg_gpm < 400:
            tips.append("📈 Низкий GPM. Попробуй больше фармить лес и линии между драками.")
        if total_deaths / len(matches) > 8:
            tips.append("💀 Часто умираешь! Перед каждым действием думай о позиционировании.")
        if total_kills / len(matches) < 2 and winrate < 50:
            tips.append("🤝 Старайся больше участвовать в гангах и тимфайтах.")
        if avg_lh < 100:
            tips.append("🌾 Мало ластхитов. Удели 20 минут в день тренировке в лобби.")

        return {
            'matches_analyzed': len(matches),
            'avg_kills': round(total_kills / len(matches), 1),
            'avg_deaths': round(total_deaths / len(matches), 1),
            'avg_assists': round(total_assists / len(matches), 1),
            'avg_gpm': round(avg_gpm),
            'winrate': round(winrate, 1),
            'tips': tips if tips else ["Отличная игра! Продолжай в том же духе."]}
