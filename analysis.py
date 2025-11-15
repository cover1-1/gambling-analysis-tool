import json
import requests
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import statistics
import math

@dataclass
class Bet:
    """Represents a betting opportunity"""
    bet_type: str
    odds: float
    book: str
    implied_prob: float
    
@dataclass
class Game:
    """Represents a sports game"""
    sport: str
    home_team: str
    away_team: str
    game_id: str
    commence_time: Optional[str] = None

class EloRatingSystem:
    """Elo rating system for team strength estimation"""
    
    def __init__(self, k_factor: float = 20, home_advantage: float = 65):
        """
        Initialize Elo system
        k_factor: How much ratings change per game (higher = more volatile)
        home_advantage: Elo points added to home team (typically 50-100)
        """
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.ratings = {}  # team_name -> rating
        self.default_rating = 1500
        
    def get_rating(self, team: str) -> float:
        """Get team's current Elo rating"""
        return self.ratings.get(team, self.default_rating)
    
    def calculate_win_probability(self, team_a_rating: float, team_b_rating: float) -> float:
        """
        Calculate probability of team A beating team B
        Formula: 1 / (1 + 10^((Rb - Ra) / 400))
        """
        return 1 / (1 + 10 ** ((team_b_rating - team_a_rating) / 400))
    
    def predict_game(self, home_team: str, away_team: str) -> Dict:
        """Predict game outcome using Elo ratings"""
        home_rating = self.get_rating(home_team)
        away_rating = self.get_rating(away_team)
        
        # Add home advantage to home team
        adjusted_home_rating = home_rating + self.home_advantage
        
        home_win_prob = self.calculate_win_probability(adjusted_home_rating, away_rating)
        away_win_prob = 1 - home_win_prob
        
        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_rating": home_rating,
            "away_rating": away_rating,
            "home_win_prob": home_win_prob,
            "away_win_prob": away_win_prob,
            "rating_diff": home_rating - away_rating,
            "adjusted_home_rating": adjusted_home_rating
        }
    
    def update_ratings(self, home_team: str, away_team: str, home_score: int, away_score: int):
        """
        Update Elo ratings after a game
        home_score/away_score: actual points scored (or 1/0 for win/loss)
        """
        home_rating = self.get_rating(home_team)
        away_rating = self.get_rating(away_team)
        
        # Determine actual outcome (1 = home win, 0 = away win, 0.5 = tie)
        if home_score > away_score:
            actual_outcome = 1.0
        elif home_score < away_score:
            actual_outcome = 0.0
        else:
            actual_outcome = 0.5
        
        # Calculate expected outcome
        adjusted_home_rating = home_rating + self.home_advantage
        expected_outcome = self.calculate_win_probability(adjusted_home_rating, away_rating)
        
        # Update ratings
        rating_change = self.k_factor * (actual_outcome - expected_outcome)
        
        self.ratings[home_team] = home_rating + rating_change
        self.ratings[away_team] = away_rating - rating_change
        
        return {
            "home_new_rating": self.ratings[home_team],
            "away_new_rating": self.ratings[away_team],
            "rating_change": rating_change
        }
    
    def initialize_team(self, team: str, rating: float = None):
        """Initialize or set a team's rating"""
        if rating is None:
            rating = self.default_rating
        self.ratings[team] = rating
    
    def get_top_teams(self, n: int = 10) -> List[tuple]:
        """Get top N teams by rating"""
        sorted_teams = sorted(self.ratings.items(), key=lambda x: x[1], reverse=True)
        return sorted_teams[:n]

class BettingAdvisor:
    """Main betting advisor class with AI analysis capabilities"""
    
    def __init__(self, bankroll: float = 1000.0, use_elo: bool = True):
        self.bankroll = bankroll
        self.bet_history = []
        self.use_elo = use_elo
        
        # Initialize Elo system
        if self.use_elo:
            self.elo = EloRatingSystem(k_factor=20, home_advantage=65)
            self._initialize_default_ratings()
    
    def _initialize_default_ratings(self):
        """Initialize ratings for common NFL teams (based on 2024 performance)"""
        # template, prolly use historical data for actual elo ratings later on in production
        nba_ratings = {
            "Minnesota TimberWolves": 1650,
            "Denver Nuggets": 1620,
            "Cleveland Cavaliers": 1640,
            "Toronto Raptors": 1580,
            "Memphis Grizzlies": 1630,
            "Indiana Pacers": 1610,
            "Oklahoma City Thunder": 1600,
            "Charlotte Hornets": 1590,
            "Los Angeles Lakers": 1560,
            "Milwaukee Bucks": 1570,
        }
        
        
        for team, rating in nba_ratings.items():
            self.elo.initialize_team(team, rating)
        
    def american_to_decimal(self, american_odds: int) -> float:
        """Convert American odds to decimal odds"""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
    
    def decimal_to_implied_prob(self, decimal_odds: float) -> float:
        """Convert decimal odds to implied probability"""
        return 1 / decimal_odds
    
    def calculate_kelly_criterion(self, win_prob: float, odds: float) -> float:
        """
        Calculate optimal bet size using Kelly Criterion
        Formula: (bp - q) / b
        where b = decimal odds - 1, p = win probability, q = 1 - p
        """
        b = odds - 1
        q = 1 - win_prob
        kelly = (b * win_prob - q) / b
        
        # Use fractional Kelly (0.25) for safety
        return max(0, kelly * 0.25)
    
    def calculate_expected_value(self, win_prob: float, odds: float, stake: float = 1) -> float:
        """Calculate expected value of a bet"""
        win_amount = stake * (odds - 1)
        loss_amount = stake
        ev = (win_prob * win_amount) - ((1 - win_prob) * loss_amount)
        return ev
    
    def fetch_odds_api(self, sport: str = "americanfootball_nfl", 
                       regions: str = "us", markets: str = "h2h,spreads", 
                       api_key: str = None) -> List[Game]:
        """
        Fetch odds from The Odds API (requires API key)
        Get your free API key at: https://the-odds-api.com/
        
        Args:
            sport: Sport key (e.g., 'americanfootball_nfl', 'basketball_nba')
            regions: Comma-separated regions (e.g., 'us', 'uk', 'eu')
            markets: Comma-separated markets (e.g., 'h2h', 'spreads', 'totals')
            api_key: Your Odds API key (or set ODDS_API_KEY environment variable)
        """
        
        # Try to get API key from parameter, environment variable, or use None
        import os
        if api_key is None:
            api_key = os.environ.get('ODDS_API_KEY')
        
        # If no API key, use mock data
        if not api_key:
            print("Note: Using mock data. To use real data:")
            print("  1. Get free API key from https://the-odds-api.com/")
            print("  2. Set environment variable: export ODDS_API_KEY='your_key_here'")
            print("  3. Or pass api_key parameter to this function\n")
            
            mock_games = [
                Game(
                    sport="NFL",
                    home_team="Kansas City Chiefs",
                    away_team="Buffalo Bills",
                    game_id="nfl_001",
                    commence_time="2025-11-10T18:00:00Z"
                ),
                Game(
                    sport="NFL",
                    home_team="San Francisco 49ers",
                    away_team="Dallas Cowboys",
                    game_id="nfl_002",
                    commence_time="2025-11-10T20:00:00Z"
                )
            ]
            return mock_games
        
        # Real API call
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
            params = {
                'apiKey': api_key,
                'regions': regions,
                'markets': markets,
                'oddsFormat': 'decimal'
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse response into Game objects
            games = []
            for event in data:
                games.append(Game(
                    sport=sport,
                    home_team=event['home_team'],
                    away_team=event['away_team'],
                    game_id=event['id'],
                    commence_time=event['commence_time']
                ))
            
            print(f"Fetched {len(games)} games from The Odds API")
            print(f"Requests remaining: {response.headers.get('x-requests-remaining', 'Unknown')}")
            
            return games
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching from API: {e}")
            print("Falling back to mock data...\n")
            return self.fetch_odds_api(sport=sport, api_key=None)  # Fallback to mock
    
    def get_mock_odds(self, game: Game, api_key: str = None) -> List[Bet]:
        """
        Get odds for a specific game
        If api_key provided, attempts to fetch real odds from The Odds API
        Otherwise generates mock odds for demonstration
        """
        import os
        if api_key is None:
            api_key = os.environ.get('ODDS_API_KEY')
        
        # If we have an API key, try to fetch real odds
        if api_key:
            try:
                url = f"https://api.the-odds-api.com/v4/sports/{game.sport.lower()}/odds"
                params = {
                    'apiKey': api_key,
                    'regions': 'us',
                    'markets': 'h2h,spreads',
                    'oddsFormat': 'decimal',
                    'eventIds': game.game_id
                }
                
                response = requests.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                if data:
                    event = data[0]
                    bets = []
                    
                    for bookmaker in event.get('bookmakers', []):
                        book_name = bookmaker['title']
                        
                        for market in bookmaker.get('markets', []):
                            if market['key'] == 'h2h':  # Moneyline
                                for outcome in market['outcomes']:
                                    odds = outcome['price']
                                    bets.append(Bet(
                                        bet_type=f"{outcome['name']} ML",
                                        odds=odds,
                                        book=book_name,
                                        implied_prob=self.decimal_to_implied_prob(odds)
                                    ))
                    
                    if bets:
                        print(f"Fetched real odds from {len(set(b.book for b in bets))} bookmakers")
                        return bets
                        
            except Exception as e:
                print(f"Could not fetch real odds: {e}")
                print("Using mock odds instead...\n")
        
        # Fallback to mock odds
        import random
        
        books = ["DraftKings", "FanDuel", "BetMGM"]
        bets = []
        
        for book in books:
            # Generate slightly different odds per book
            base_odds = random.uniform(1.8, 2.2)
            odds_variation = random.uniform(-0.1, 0.1)
            odds = base_odds + odds_variation
            
            bets.append(Bet(
                bet_type=f"{game.away_team} ML",
                odds=odds,
                book=book,
                implied_prob=self.decimal_to_implied_prob(odds)
            ))
            
            # Add home team odds
            home_odds = 2.4 - (odds - 1.8)
            bets.append(Bet(
                bet_type=f"{game.home_team} ML",
                odds=home_odds,
                book=book,
                implied_prob=self.decimal_to_implied_prob(home_odds)
            ))
        
        return bets
    
    def analyze_with_ai(self, game: Game, odds: List[Bet], elo_prediction: Optional[Dict] = None) -> Dict:
        """
        Use Claude API to analyze game and provide insights
        Note: Still needs a lot of work
        """
        
        odds_summary = "\n".join([
            f"{bet.book}: {bet.bet_type} @ {bet.odds:.2f} (implied: {bet.implied_prob*100:.1f}%)"
            for bet in odds[:6]  # Show first 6 for brevity
        ])
        
        elo_info = ""
        if elo_prediction:
            elo_info = f"""
Elo Rating Analysis:
- {game.home_team}: {elo_prediction['home_rating']:.0f} rating
- {game.away_team}: {elo_prediction['away_rating']:.0f} rating
- Rating difference: {elo_prediction['rating_diff']:.0f} (favoring {'home' if elo_prediction['rating_diff'] > 0 else 'away'})
- Elo win probabilities:
  * {game.home_team}: {elo_prediction['home_win_prob']*100:.1f}%
  * {game.away_team}: {elo_prediction['away_win_prob']*100:.1f}%
"""
        
        prompt = f"""You are a professional sports betting analyst. Analyze this matchup:

Game: {game.away_team} @ {game.home_team}
Sport: {game.sport}
Time: {game.commence_time}

Current Odds:
{odds_summary}

{elo_info}

Provide analysis in JSON format with these fields:
{{
  "matchup_analysis": "2-3 sentence analysis of the matchup",
  "value_bets": [
    {{
      "team": "team name",
      "bet_type": "moneyline/spread/total",
      "estimated_win_prob": 0.XX (as decimal, e.g., 0.55 for 55%),
      "reasoning": "why this has value"
    }}
  ],
  "risk_factors": ["factor 1", "factor 2"],
  "confidence_level": "high/medium/low",
  "elo_vs_market": "brief comparison of Elo prediction vs market odds (if Elo data provided)"
}}

Return ONLY valid JSON, no other text."""

        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"Content-Type": "application/json"},
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            
            data = response.json()
            text = "".join([c["text"] for c in data["content"] if c["type"] == "text"])
            return json.loads(text.strip())
            
        except Exception as e:
            return {"error": f"AI analysis failed: {str(e)}"}
    
    def find_best_odds(self, bets: List[Bet], bet_type: str) -> Optional[Bet]:
        """Find the best odds for a specific bet type"""
        matching_bets = [b for b in bets if bet_type.lower() in b.bet_type.lower()]
        if not matching_bets:
            return None
        return max(matching_bets, key=lambda x: x.odds)
    
    def analyze_game(self, game: Game, verbose: bool = True) -> Dict:
        """Complete analysis of a game"""
        if verbose:
            print(f"\n{'='*60}")
            print(f"Analyzing: {game.away_team} @ {game.home_team}")
            print(f"{'='*60}\n")
        
        # Get Elo prediction if enabled
        elo_prediction = None
        if self.use_elo:
            elo_prediction = self.elo.predict_game(game.home_team, game.away_team)
            if verbose:
                print("ELO RATING ANALYSIS:")
                print(f"  {game.home_team}: {elo_prediction['home_rating']:.0f}")
                print(f"  {game.away_team}: {elo_prediction['away_rating']:.0f}")
                print(f"  Rating Difference: {elo_prediction['rating_diff']:.0f}")
                print(f"  Elo Win Probabilities:")
                print(f"    {game.home_team}: {elo_prediction['home_win_prob']*100:.1f}%")
                print(f"    {game.away_team}: {elo_prediction['away_win_prob']*100:.1f}%")
                print()
        
        # Get odds
        odds = self.get_mock_odds(game)
        
        # AI analysis
        ai_analysis = self.analyze_with_ai(game, odds, elo_prediction)
        
        if "error" in ai_analysis:
            print(f"Error: {ai_analysis['error']}")
            return ai_analysis
        
        # Calculate recommendations
        recommendations = []
        
        for value_bet in ai_analysis.get("value_bets", []):
            best_odds = self.find_best_odds(odds, value_bet["team"])
            
            if best_odds:
                win_prob = value_bet["estimated_win_prob"]
                kelly_pct = self.calculate_kelly_criterion(win_prob, best_odds.odds)
                ev = self.calculate_expected_value(win_prob, best_odds.odds, 100)
                
                # Compare with Elo if available
                elo_edge = None
                if elo_prediction:
                    market_prob = best_odds.implied_prob
                    if value_bet["team"].lower() in game.home_team.lower():
                        elo_prob = elo_prediction['home_win_prob']
                    else:
                        elo_prob = elo_prediction['away_win_prob']
                    elo_edge = elo_prob - market_prob
                
                recommendations.append({
                    "bet": best_odds.bet_type,
                    "book": best_odds.book,
                    "odds": best_odds.odds,
                    "estimated_win_prob": win_prob,
                    "market_implied_prob": best_odds.implied_prob,
                    "elo_win_prob": elo_prob if elo_prediction else None,
                    "elo_edge": elo_edge,
                    "kelly_stake_pct": kelly_pct * 100,
                    "recommended_stake": self.bankroll * kelly_pct,
                    "expected_value": ev,
                    "reasoning": value_bet["reasoning"]
                })
        
        result = {
            "game": game,
            "elo_prediction": elo_prediction,
            "analysis": ai_analysis,
            "recommendations": recommendations,
            "all_odds": odds
        }
        
        if verbose:
            self.print_analysis(result)
        
        return result
    
    def print_analysis(self, result: Dict):
        """Pretty print analysis results"""
        analysis = result["analysis"]
        
        print("MATCHUP ANALYSIS:")
        print(f"  {analysis.get('matchup_analysis', 'N/A')}\n")
        
        print(f"CONFIDENCE: {analysis.get('confidence_level', 'N/A').upper()}\n")
        
        # Print Elo vs Market comparison if available
        if analysis.get('elo_vs_market'):
            print("ELO VS MARKET:")
            print(f"  {analysis['elo_vs_market']}\n")
        
        print("VALUE BETS IDENTIFIED:")
        for i, rec in enumerate(result["recommendations"], 1):
            print(f"\n  {i}. {rec['bet']}")
            print(f"     Book: {rec['book']}")
            print(f"     Odds: {rec['odds']:.2f}")
            print(f"     Market Implied Prob: {rec['market_implied_prob']*100:.1f}%")
            if rec.get('elo_win_prob'):
                print(f"     Elo Win Probability: {rec['elo_win_prob']*100:.1f}%")
                if rec.get('elo_edge'):
                    edge_pct = rec['elo_edge'] * 100
                    print(f"     Elo Edge: {edge_pct:+.1f}% {'✓ POSITIVE' if edge_pct > 0 else '✗ NEGATIVE'}")
            print(f"     Estimated Win Prob: {rec['estimated_win_prob']*100:.1f}%")
            print(f"     Kelly Stake: {rec['kelly_stake_pct']:.2f}% (${rec['recommended_stake']:.2f})")
            print(f"     Expected Value: ${rec['expected_value']:.2f} per $100 bet")
            print(f"     Reasoning: {rec['reasoning']}")
        
        print("\nRISK FACTORS:")
        for risk in analysis.get("risk_factors", []):
            print(f"  • {risk}")
        
        print(f"\n{'='*60}\n")
    
    def compare_books(self, odds: List[Bet]) -> Dict[str, List[Bet]]:
        """Compare odds across different books"""
        by_book = {}
        for bet in odds:
            if bet.book not in by_book:
                by_book[bet.book] = []
            by_book[bet.book].append(bet)
        return by_book
    
    def calculate_arbitrage(self, odds: List[Bet]) -> Optional[Dict]:
        """Check for arbitrage opportunities"""
        # Simplified arbitrage detection
        # In practice, you'd need to check all combinations
        bet_types = set(bet.bet_type for bet in odds)
        
        for bet_type in bet_types:
            matching = [b for b in odds if b.bet_type == bet_type]
            if len(matching) > 1:
                best = max(matching, key=lambda x: x.odds)
                worst = min(matching, key=lambda x: x.odds)
                
                # Check if there's significant line shopping value
                if (best.odds - worst.odds) > 0.1:
                    return {
                        "opportunity": "line_shopping",
                        "bet_type": bet_type,
                        "best_book": best.book,
                        "best_odds": best.odds,
                        "worst_book": worst.book,
                        "worst_odds": worst.odds,
                        "edge": best.odds - worst.odds
                    }
        return None


def main():
    """Main CLI interface"""
    print("=" * 60)
    print("AI-POWERED SPORTS BETTING ADVISOR")
    print("=" * 60)
    
    # Initialize advisor
    bankroll = float(input("\nEnter your bankroll ($): ") or "1000")
    use_elo = input("Use Elo rating system? (y/n): ").lower() != 'n'
    
    advisor = BettingAdvisor(bankroll=bankroll, use_elo=use_elo)
    
    print(f"\nBankroll set to: ${bankroll:.2f}")
    print(f"Elo ratings: {'Enabled' if use_elo else 'Disabled'}")
    
    if use_elo:
        print("\nTop teams by Elo rating:")
        for i, (team, rating) in enumerate(advisor.elo.get_top_teams(5), 1):
            print(f"  {i}. {team}: {rating:.0f}")
    
    print("\nFetching games...")
    
    # Fetch games
    games = advisor.fetch_odds_api(sport="basketball_nba",
                                   api_key="ef3bb5fc3d4f3207ee38ae1987ab43cf")
    
    print(f"\nFound {len(games)} games:\n")
    for i, game in enumerate(games, 1):
        print(f"{i}. {game.away_team} @ {game.home_team}")
    
    # Select game
    choice = int(input("\nSelect game to analyze (number): ")) - 1
    
    if 0 <= choice < len(games):
        selected_game = games[choice]
        analysis = advisor.analyze_game(selected_game)
        
        # Ask if user wants to see all odds
        show_all = input("\nShow all odds from all books? (y/n): ").lower() == 'y'
        if show_all:
            print("\nALL AVAILABLE ODDS:")
            by_book = advisor.compare_books(analysis["all_odds"])
            for book, bets in by_book.items():
                print(f"\n{book}:")
                for bet in bets:
                    print(f"  {bet.bet_type}: {bet.odds:.2f} ({bet.implied_prob*100:.1f}%)")
        
        # Check for arbitrage
        arb = advisor.calculate_arbitrage(analysis["all_odds"])
        if arb:
            print("\nLINE SHOPPING OPPORTUNITY DETECTED!")
            print(f"  {arb['bet_type']}")
            print(f"  Best: {arb['best_book']} @ {arb['best_odds']:.2f}")
            print(f"  Worst: {arb['worst_book']} @ {arb['worst_odds']:.2f}")
            print(f"  Edge: {arb['edge']:.2f} decimal points")
        
        # Option to update Elo ratings after game
        if use_elo:
            update = input("\nUpdate Elo ratings with game result? (y/n): ").lower() == 'y'
            if update:
                print(f"\nEnter final score:")
                home_score = int(input(f"  {selected_game.home_team}: "))
                away_score = int(input(f"  {selected_game.away_team}: "))
                
                result = advisor.elo.update_ratings(
                    selected_game.home_team,
                    selected_game.away_team,
                    home_score,
                    away_score
                )
                
                print(f"\nElo ratings updated!")
                print(f"  {selected_game.home_team}: {result['home_new_rating']:.0f} ({result['rating_change']:+.1f})")
                print(f"  {selected_game.away_team}: {result['away_new_rating']:.0f} ({-result['rating_change']:+.1f})")
    else:
        print("Invalid selection")


if __name__ == "__main__":
    main()


