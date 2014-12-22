import sys
import random
import itertools
import collections

from game import State, Game
from player import Bot
from util import Variable

import beginners
import validators
import intermediates
import invalidator


def skip(iterator, n):
    next(itertools.islice(iterator, n, n), None)
    return iterator


class Runner(Game):

    def simulate(self, state):
        self.state = state.clone()

        for b in self.bots:
            b.game = self.state

        self.run()


class Opponent(object):

    def clone(self):
        c = object.__new__(type(self))
        c.name, c.index = self.name, self.index
        c.spy = self.spy

        try:
            c.spies = self.spies
            c.configurations = self.configurations[:]
        except:
            pass

        try:
            c.state = self.state.clone()
        except:
            pass

        try:
            c.invalidations = self.invalidations.copy()
            c.factors = self.factors.copy()
            c.oracle = self.oracle
            c.adviser = self.adviser
        except:
            pass

        return c

    def __call__(self, *args):
        return self

intermediates.Simpleton.clone = Opponent.__dict__['clone']
intermediates.Simpleton.__call__ = Opponent.__dict__['__call__']

beginners.RandomBot.clone = Opponent.__dict__['clone']
beginners.RandomBot.__call__ = Opponent.__dict__['__call__']

validators.StateChecker.clone = Opponent.__dict__['clone']
validators.StateChecker.__call__ = Opponent.__dict__['__call__']

invalidator.Invalidator.clone = Opponent.__dict__['clone']
invalidator.Invalidator.__call__ = Opponent.__dict__['__call__']



class Reasonable(invalidator.Invalidator):
    """A bot that does logical reasoning based on the known spies and the
    results from the mission sabotages.
    """

    def onGameRevealed(self, players, spies):
        self.spies = spies

        self.opponents = [invalidator.Invalidator(self.game, i, False) for i in range(5)]
        self.runner = Runner(self.opponents, [False] * 5)

        self._onCallback('onGameRevealed', players, spies)

    def _onCallback(self, attr, *args):
        for o in self.opponents:
            getattr(o, attr)(*args)
        getattr(super(Reasonable, self), attr)(*args)

    def onMissionAttempt(self, *args):
        self._onCallback('onMissionAttempt', *args)

    def onTeamSelected(self, *args):
        self._onCallback('onTeamSelected', *args)

    def onVoteComplete(self, *args):
        self._onCallback('onVoteComplete', *args)

    def onMissionComplete(self, *args):
        self._onCallback('onMissionComplete', *args)

    def onAnnouncement(self, *args):
        self._onCallback('onAnnouncement', *args)


    def _simulateAndPickBest(self, cmd, options, samples=100):
        assert len(options) > 0

        step = (self.game.turn, self.game.tries, self.game.phase)
        spies = None
        original = None
        me = None

        move = [None]        
        def decider(*args):
            if move[0] is None:
                assert step == (me.game.turn, me.game.tries, me.game.phase)
                m = random.choice(options)
                move[0] = m
                return m
            else:
                return original(*args)

        failures = 0
        scores = {o: Variable() for o in options}        
        for _ in range(samples):
            move[0] = None

            mn = min(self.invalidations.values())
            invalidations = [c for c, s in self.invalidations.items() if s <= mn]

            iv = random.choice(invalidations)
            spies = self.spies if self.spy else self.getSpies(iv)
            for o in self.opponents:
                assert o.spy is not None
            self.runner.bots = [o.clone() for o in self.opponents]

            me = self.runner.bots[self.index]
            original = getattr(me, cmd)
            setattr(me, cmd, decider)

            if self.spy:
                assert self in spies

            for b in self.runner.bots:
                b.spy = bool(b.index in [s.index for s in spies])
            assert self.runner.bots[self.index].spy == self.spy

            self.runner.simulate(self.game)
            # print(move[0], spies, self.runner.state)

            win = int(self.spy == (not self.runner.won))
            if move[0] is not None:
                scores[move[0]].sample(win)
            else:
                assert False
                failures += 1

        if failures:
            print("Failures:", failures, " out of ", samples, " for ", cmd)

        # Reverse the list so True is the default.
        return max(reversed(scores.keys()), key=scores.get), scores
 
    def select(self, players, count):
        options = itertools.chain(*[itertools.combinations(self.getResistance(c), count) for c in self.invalidations])
        if options:
            options = itertools.combinations(players, count)
        options = [o for o in options if self in o]
        s, data = self._simulateAndPickBest('select', list(set(options)), samples=2500)
        self.log.debug("TEAMS: %r" % data)

        d = collections.defaultdict(Variable)
        for team, score in data.items():
            for t in team:
                d[t].samples += score.samples
                d[t].total += score.total

        self.log.debug("PLAYERS: %r" % d)
        return s
        # return sorted(d, key=d.get, reverse=True)[:count]

    def vote(self, team):
        v, data = self._simulateAndPickBest('vote', [True, False], samples=1000)
        self.log.debug("VOTES: %r" % data)
        return v

    def sabotage(self):
        s, data = self._simulateAndPickBest('sabotage', [True, False], samples=1000)
        self.log.debug("SABOTAGES: %r" % data)
        return s


class Sensible(Reasonable):

    def onGameRevealed(self, players, spies):
        self.spies = spies

        self.opponents = [intermediate.Simpleton(self.game, i, False) for i in range(1,6)]
        self.runner = Runner(self.opponents, [False] * 5)

        self._onCallback('onGameRevealed', players, spies)
