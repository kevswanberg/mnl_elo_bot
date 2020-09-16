import unittest
import sys
sys.path.append(".")


from mnl_elo_bot import elo_bot  # noqa


class IntegrationTest(unittest.TestCase):
    # Just see if it initializes and runs...
    def test_process(self):
        elo_bot.process_results(elo_bot.get_raw_results_reader())
        for team in elo_bot.TEAMS.values():
            self.assertIsNotNone(team.name)
            self.assertIsNotNone(team.color)
            self.assertIsNotNone(team.emoji)
            self.assertIsNotNone(team.history)


if __name__ == '__main__':
    unittest.main()
