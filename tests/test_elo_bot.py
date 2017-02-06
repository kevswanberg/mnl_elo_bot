import unittest
import sys
sys.path.append(".")
from mnl_elo_bot import elo_bot

class TestTeam(unittest.TestCase):
    def setUp(self):
        self.team = elo_bot.Team("ponies", "blue")

    def test_initialization(self):
        self.assertEqual(self.team.name, "ponies")

    def test_win(self):
        self.team.win(30)
        self.assertEqual(self.team.history, [1500])
        self.assertEqual(self.team.elo, 1530)


if __name__ == '__main__':
    unittest.main()
