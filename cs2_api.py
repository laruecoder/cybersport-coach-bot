import requests
from typing import Dict, Optional
from datetime import datetime

PROXY = "socks5://127.0.0.1:10808"

class CS2API:
    def __init__(self, steam_api_key: str):
        self.api_key = steam_api_key
        self.base_url = "https://api.steampowered.com"
    
    def get_steam_id_from_url(self, profile_url: str) -> Optional[str]:
        """Извлекает Steam ID из URL профиля"""
        try:
            if 'steamcommunity.com/id/' in profile_url:
                custom_url = profile_url.split('/id/')[-1].strip('/')
                response = requests.get(
                    f"{self.base_url}/ISteamUser/ResolveVanityURL/v1/",
                    params={'key': self.api_key, 'vanityurl': custom_url},
                    proxies={'http': PROXY, 'https': PROXY}
                )
                data = response.json()
                if data.get('response', {}).get('success') == 1:
                    return data['response']['steamid']
            elif 'steamcommunity.com/profiles/' in profile_url:
                return profile_url.split('/profiles/')[-1].strip('/')
            return None
        except Exception as e:
            print(f"Error resolving Steam ID: {e}")
            return None
    
    def get_player_summary(self, steam_id: str) -> Optional[Dict]:
        """Получает базовую информацию о профиле (работает всегда для публичных)"""
        try:
            response = requests.get(
                f"{self.base_url}/ISteamUser/GetPlayerSummaries/v2/",
                params={'key': self.api_key, 'steamids': steam_id},
                proxies={'http': PROXY, 'https': PROXY}
            )
            data = response.json()
            players = data.get('response', {}).get('players', [])
            
            if not players:
                return None
            
            player = players[0]
            
            # Определяем статус
            status_map = {0: 'Offline', 1: 'Online', 2: 'Busy', 3: 'Away', 4: 'Snooze', 5: 'Looking to trade', 6: 'Looking to play'}
            
            # Преобразуем timestamp в дату
            creation_date = None
            if player.get('timecreated'):
                creation_date = datetime.fromtimestamp(player['timecreated']).strftime('%d.%m.%Y')
            
            # Определяем видимость профиля
            visibility_map = {1: 'Private', 2: 'Friends only', 3: 'Public'}
            
            return {
                'steam_id': steam_id,
                'nickname': player.get('personaname', 'Unknown'),
                'avatar': player.get('avatarfull', ''),
                'profile_url': player.get('profileurl', ''),
                'status': status_map.get(player.get('personastate', 0), 'Unknown'),
                'visibility': visibility_map.get(player.get('communityvisibilitystate', 1), 'Unknown'),
                'creation_date': creation_date,
                'country': player.get('loccountrycode', 'Unknown'),
                'last_online': datetime.fromtimestamp(player.get('lastlogoff', 0)).strftime('%d.%m.%Y %H:%M') if player.get('lastlogoff') else 'Unknown'
            }
        except Exception as e:
            print(f"Error fetching player summary: {e}")
            return None
    
    def get_owned_games(self, steam_id: str) -> Optional[Dict]:
        """Получает список игр и часы (только если профиль публичный)"""
        try:
            response = requests.get(
                f"{self.base_url}/IPlayerService/GetOwnedGames/v1/",
                params={
                    'key': self.api_key,
                    'steamid': steam_id,
                    'include_played_free_games': 1,
                    'include_appinfo': 1
                },
                proxies={'http': PROXY, 'https': PROXY}
            )
            data = response.json()
            games = data.get('response', {}).get('games', [])
            
            if not games:
                return None
            
            # Ищем CS2
            cs2_data = None
            total_hours = 0
            top_games = []
            
            for game in games:
                hours = round(game.get('playtime_forever', 0) / 60, 1)
                if game.get('appid') == 730:  # CS2/CS:GO appid
                    cs2_data = {
                        'hours_total': hours,
                        'hours_2weeks': round(game.get('playtime_2weeks', 0) / 60, 1) if game.get('playtime_2weeks') else 0
                    }
                top_games.append({'name': game.get('name', 'Unknown'), 'hours': hours})
            
            # Сортируем по часам и берём топ-5
            top_games.sort(key=lambda x: x['hours'], reverse=True)
            
            return {
                'total_games': len(games),
                'cs2': cs2_data,
                'top_games': top_games[:5]
            }
        except Exception as e:
            print(f"Error fetching owned games: {e}")
            return None
    
    def analyze_cs2_profile(self, summary: Dict, games: Dict) -> Dict:
        """Формирует итоговую информацию и советы по CS2"""
        tips = [
            "🎯 Practice aim: Aim Lab (free) or Aim Botz workshop map",
            "📺 Watch pro demos: hltv.org/demos",
            "🗺️ Learn smokes: search 'CS2 smoke guide' on YouTube",
            "💪 Warmup routine: 15 min DM + 15 min aim training before matches",
            "🧠 Game sense: play retake servers, watch your own demos",
            "🤝 Communication: use clear callouts, don't rage at teammates"
        ]
        
        cs2_info = ""
        if games and games.get('cs2'):
            cs2 = games['cs2']
            cs2_info = f"\n🕹️ *CS2 Hours:* {cs2['hours_total']} total"
            if cs2['hours_2weeks'] > 0:
                cs2_info += f" ({cs2['hours_2weeks']}h last 2 weeks)"
            
            # Советы в зависимости от часов
            if cs2['hours_total'] < 100:
                tips.insert(0, "🔰 You're new! Focus on basics: crosshair placement, economy, map knowledge")
            elif cs2['hours_total'] > 1000:
                tips.insert(0, "🔥 Veteran! Try joining Faceit or ESEA leagues to go pro")
        
        return {
            'cs2_info': cs2_info,
            'tips': tips
        }