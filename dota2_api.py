# -*- coding: utf-8 -*-
import requests
from typing import Dict, List, Optional

class Dota2API:
    def __init__(self):
        self.base_url = "https://api.opendota.com/api"
    
    def get_recent_matches(self, player_id: str, limit: int = 5) -> List[Dict]:
        try:
            response = requests.get(
                f"{self.base_url}/players/{player_id}/recentMatches",
                timeout=10
            )
            if response.status_code == 200:
                matches = response.json()[:limit]
                return [self._parse_match(match) for match in matches]
            return []
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    def _parse_match(self, match: Dict) -> Dict:
        player_slot = match.get('player_slot', 0)
        radiant_win = match.get('radiant_win', False)
        is_radiant = player_slot < 128
        won = (is_radiant and radiant_win) or (not is_radiant and not radiant_win)
        return {
            'match_id': match.get('match_id'),
            'kills': match.get('kills', 0),
            'deaths': match.get('deaths', 0),
            'assists': match.get('assists', 0),
            'kda': round((match.get('kills', 0) + match.get('assists', 0)) / max(1, match.get('deaths', 0)), 1),
            'last_hits': match.get('last_hits', 0),
            'gpm': match.get('gold_per_min', 0),
            'xpm': match.get('xp_per_min', 0),
            'duration_min': round(match.get('duration', 0) / 60),
            'won': won,
            'hero_damage': match.get('hero_damage', 0)
        }
    
    def analyze_performance(self, matches: List[Dict]) -> Dict:
        if not matches:
            return {'error': 'No data'}
        total_kills = sum(m.get('kills', 0) for m in matches)
        total_deaths = sum(m.get('deaths', 0) for m in matches)
        total_assists = sum(m.get('assists', 0) for m in matches)
        avg_gpm = sum(m.get('gpm', 0) for m in matches) / len(matches)
        avg_lh = sum(m.get('last_hits', 0) for m in matches) / len(matches)
        wins = sum(1 for m in matches if m.get('won'))
        winrate = (wins / len(matches)) * 100
        tips = []
        if avg_gpm < 400:
            tips.append("Низкий GPM. Фарми лес и линии между драками.")
        if total_deaths / len(matches) > 8:
            tips.append("Много смертей. Следи за позиционированием.")
        if total_kills / len(matches) < 2 and winrate < 50:
            tips.append("Участвуй в гангах и тимфайтах.")
        if avg_lh < 100:
            tips.append("Мало ластхитов. Тренируйся в лобби 20 мин/день.")
        return {
            'matches_analyzed': len(matches),
            'avg_kills': round(total_kills / len(matches), 1),
            'avg_deaths': round(total_deaths / len(matches), 1),
            'avg_assists': round(total_assists / len(matches), 1),
            'avg_gpm': round(avg_gpm),
            'winrate': round(winrate, 1),
            'tips': tips if tips else ["Отличная игра! Так держать."]
        }
