import unittest
import sys
sys.path.append(".")


from mnl_elo_bot import elo_bot  # noqa


class TestTeam(unittest.TestCase):
    def setUp(self):
        self.team = elo_bot.Team("ponies", "blue")

    def test_initialization(self):
        self.assertEqual(self.team.name, "ponies")
        self.assertEqual(self.team.color, "blue")
        self.assertEqual(self.team.last_game_explanation(),
                         "ponies rating is at 1500.0 (0.0)")

    def test_win(self):
        self.team.win(30)
        self.assertEqual(self.team.history, [1500, 1530])
        self.assertEqual(self.team.elo, 1530)
        self.assertEqual(self.team.last_game_explanation(),
                         "ponies rating goes up to 1530.0 (30.0)")

    def test_lose(self):
        self.team.lose(30)
        self.assertEqual(self.team.history, [1500, 1470])
        self.assertEqual(self.team.elo, 1470)
        self.assertEqual(self.team.last_game_explanation(),
                         "ponies rating goes down to 1470.0 (-30.0)")


if __name__ == '__main__':
    unittest.main()
