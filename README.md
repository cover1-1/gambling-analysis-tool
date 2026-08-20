The user can analyze upcoming NBA games using statistical models and sportsbooks' odds to evaluate expected value and optimal bet sizing. The tool calculates win probabilities using an Elo rating system and applies the Kelly Criterion to determine risk-adjusted position sizes. Game odds are fetched automatically and compared across multiple sportsbooks.

Built using Python, with statistical modeling and API integration for real-time data retrieval and persistent storage.

The goal of the project is to explore quantitative sports analytics and automate data-driven decision-making for professional basketball analysis.

## Setup

Install dependencies with `pip install -r requirements.txt`. To use live Odds
API data, set `ODDS_API_KEY` in your environment (see `.env.example`); without
it, the app uses mock odds and skips Elo updates. API keys are intentionally
never stored in source code.

Run the automated checks with `python -m unittest test_analysis.py`.
