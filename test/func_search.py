import unittest
import random

from bots import Neighbor
from game import Game


class TestSearch(unittest.TestCase):

    def test_DeterministicGame(self):
        players = [Neighbor] * 5
        roles = [True, True, False, False, False]
        random.shuffle(roles)

        game = Game(players, roles)
        games = [game]

        while not game.done:
            for g in games:
                g.step()

            clone = Game(players, roles, state=game.state.clone())
            games.append(clone)
        
        for g in games:
            if not(game.state == g.state):
                print("*" * 80)
                print("%r" % game.state)
                print("%r" % g.state)
            self.assertEquals(game.state, g.state)


if __name__ == "__main__":
    unittest.main()
