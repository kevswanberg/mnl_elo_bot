import unittest
import sys
from mnl_elo_bot import elo_bot

sys.path.append(".")


class IntegrationTest(unittest.TestCase):
    # Just see if it initializes and runs...
    def test_process(self):
        teams = elo_bot.main(False, None, '')

        for team in teams.values():
            self.assertIsNotNone(team.name)
            self.assertIsNotNone(team.color)
            self.assertIsNotNone(team.emoji)
            self.assertIsNotNone(team.history)


if __name__ == '__main__':
    unittest.main()
