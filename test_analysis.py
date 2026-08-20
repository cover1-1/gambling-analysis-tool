import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from analysis import EloRatingSystem


class EloRatingSystemTests(unittest.TestCase):
    def _response(self, payload):
        response = Mock()
        response.json.return_value = payload
        response.raise_for_status.return_value = None
        return response

    @patch("analysis.requests.get")
    def test_completed_game_is_only_applied_once(self, mock_get):
        game = {
            "id": "game-123",
            "completed": True,
            "home_team": "Home",
            "away_team": "Away",
            "scores": [{"name": "Home", "score": "100"}, {"name": "Away", "score": "90"}],
        }
        mock_get.return_value = self._response([game])
        ratings = EloRatingSystem()

        with patch.object(ratings, "save_ratings"):
            self.assertEqual(ratings.update_elo_from_recent(api_key="test-key"), 1)
        after_first_update = dict(ratings.ratings)
        self.assertEqual(ratings.update_elo_from_recent(api_key="test-key"), 0)
        self.assertEqual(ratings.ratings, after_first_update)

    def test_processed_game_ids_round_trip_with_ratings(self):
        ratings = EloRatingSystem()
        ratings.initialize_team("Home", 1600)
        ratings.processed_game_ids.add("game-123")
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "ratings.json")
            ratings.save_ratings(path)

            loaded = EloRatingSystem()
            self.assertTrue(loaded.load_ratings(path))

        self.assertEqual(loaded.ratings["Home"], 1600)
        self.assertEqual(loaded.processed_game_ids, {"game-123"})

    @patch.dict(os.environ, {}, clear=True)
    def test_update_requires_an_api_key(self):
        ratings = EloRatingSystem()
        self.assertEqual(ratings.update_elo_from_recent(), 0)


if __name__ == "__main__":
    unittest.main()
