
import os
import json
from datetime import datetime
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

def k_val(mov, diff):
    return ((20*(mov+3)**.8) / 7.5+0.006*diff)

def e_val(elo1, elo2):
    return 1/(1+10**((elo2-elo1)/400))

def new_season_elo(elo):
    return (0.75*elo) + (0.25*1505)
class EloRatingSystemExtensions:
    # additional methods to add to EloRatingSystem class in analysis.py
    def update_elo(self, sport: str = "basketball_nba", days_back: int = 3,
                   api_key: Optional[str] = None) -> int:
        """Update ratings from completed games using an explicit or env API key."""
        api_key = api_key or os.environ.get("ODDS_API_KEY")
        if not api_key:
            print("Skipping Elo update: set ODDS_API_KEY to fetch completed games.")
            return 0

        url = f"https://api.the-odds-api.com/v4/sports/{sport}/scores"
        days_back = min(max(days_back, 1), 3)
        params = {
            'apiKey': api_key,
            'daysFrom': days_back
        }
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
        except requests.exceptions.RequestException as error:
            print(f"Unable to update Elo ratings: {error}")
            return 0
        completed_games = response.json()
        updated_count = 0
        processed_game_ids = getattr(self, "processed_game_ids", set())
        print(f"\nUpdating...")
        for game in completed_games:
            game_id = game.get("id")
            if game.get('completed') and not game_id:
                print("Skipping completed game with no event ID.")
                continue
            if game.get('completed') and game_id not in processed_game_ids:
                home_team = game['home_team']
                away_team = game['away_team']
                scores = game.get('scores')
                if scores and len(scores) >= 2:
                    home_score = next((s['score'] for s in scores if s['name'] == home_team), None)
                    away_score = next((s['score'] for s in scores if s['name']==away_team), None)
                    if home_score is not None and away_score is not None:
                        self.update_ratings(home_team, away_team, int(home_score), int(away_score))
                        processed_game_ids.add(game_id)
                        updated_count +=1
                        print(f" {away_team} @ {home_team}: {away_score}-{home_score}")
        if updated_count > 0:
            self.processed_game_ids = processed_game_ids
            self.save_ratings()
        print(f"\nUpdated {updated_count} game(s).")
        return updated_count

    def save_ratings(self,filepath:str = "elo_ratings.json"):
        # save ratings to JSON file
        data = {
            "ratings":self.ratings,
            "last_updated":datetime.now().isoformat(),
            "k_factor" : self.k_factor,
            "home_advantage":self.home_advantage,
            "processed_game_ids": sorted(getattr(self, "processed_game_ids", set()))
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Elo ratings successfully saved to {filepath}")

    def load_ratings(self, filepath:str = "elo_ratings.json"):
        if not os.path.exists(filepath):
            print("No saved ratings found at this filepath")
            return False
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            self.ratings = data["ratings"]
            self.k_factor = data.get("k_factor", self.k_factor)
            self.home_advantage = data.get("home_advantage", self.home_advantage)
            self.processed_game_ids = set(data.get("processed_game_ids", []))
            last_updated = data.get("last_updated", "Unknown")
            print(f"Loaded Elo Ratings (last updated: {last_updated})")
            return True
        except Exception as e:
            print(f"error: {e}")
            return False
