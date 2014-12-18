import unittest
import random

from player import Player
from game import State

from bots.searchers import Sensible
from bots.beginners import RandomBot


class TestResistance(unittest.TestCase):

    def setUp(self):
        self.players = [Player('Random', i+1) for i in range(5)]

        self.bot = Sensible('Bot', 1, spy=False)
        self.bot.onGameRevealed(self.players, set())

    def __test_VoteApproveLastTry(self):
        for _ in range(100):
            s = State()
            s.phase = State.PHASE_VOTING
            s.turn = random.choice([1,3])
            s.tries = 5
            s.losses = min(2, s.turn - 1)
            s.wins = min(2, s.turn - 1 - s.losses)

            s.players = self.players
            s.leader = random.choice(self.players)
            s.team = random.sample(self.players, 2)

            self.bot.game = s
            v = self.bot.vote(s.team)
            if not v:
                print(s)
            self.assertTrue(v)

    def test_VoteAgainstBadTeam(self):
        """A team of three that doesn't include this bot was picked,
        so it should be voted down."""
        for _ in range(100):
            s = State()
            s.phase = State.PHASE_VOTING
            s.turn = 5 # random.choice([4])
            s.tries = 1 # random.choice([1,2,3,4])
            s.wins = 2 # min(2, s.turn - 1)
            s.losses = 2 # min(2, s.turn - 1 - s.wins)
            # print(s)

            s.players = self.players
            s.leader = random.choice(self.players[1:])
            s.team = random.sample(self.players[1:], 3)

            self.bot.game = s
            v = self.bot.vote(s.team)
            if v:
                print(s)
            self.assertFalse(v)


class TestSpy(unittest.TestCase):

    def setUp(self):
        self.players = [Player('Random', i+1) for i in range(5)]

        self.bot = Sensible('Bot', 1, spy=True)
        self.bot.onGameRevealed(self.players, self.players[0:2])

    def __test_SabotageToWin(self):
        for _ in range(100):
            s = State()
            s.phase = State.PHASE_MISSION
            s.turn = 5
            s.tries = 5
            s.losses = 2
            s.wins = 2
            s.votes = [True, False, True, True, False]

            s.players = self.players
            s.leader = self.bot
            s.team = [self.bot] + random.sample(self.players[2:], 2)

            self.bot.game = s
            v = self.bot.sabotage()
            self.assertTrue(v)


if __name__ == "__main__":
    unittest.main()
