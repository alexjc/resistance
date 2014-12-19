"""
@name: Invalidator Bot
@author: Alex J. Champandard <alexjc@aigamedev.com>
@license: GNU Public License (GPL) version 3.0
@about: THE RESISTANCE Competition, Vienna Game/AI Conference 2012.
@since: 01.06.2012
"""

import random
import itertools

from player import Bot
from game import State
from util import Variable


def permutations(config):
    """Returns unique elements from a list of permutations."""
    return list(set(itertools.permutations(config)))



class Invalidator(Bot):

    def oracle_selection(self, config):
        """Rate teams chosen by the leader, assuming a particular configuration.
        Zero means the selection is not suspicious, and positive values indicate
        higher suspicion levels."""

        all_spies = self.getSpies(config)
        team_spies = [s for s in self.game.team if s in all_spies]
        if self.game.leader in all_spies and len(team_spies) != 1:
            return 1.0, [(1.0, "%s, assuming a spy, did not pick a mission with spies.")] 
        return 0.0, []

    def oracle_voting(self, config, votes):
        """Assess the votes of a player, assuming a particular configuration.
        Zero means no suspicious activity and positive values indicate high
        suspicion levels."""
        score = 0.0
        factors = []

        all_spies = self.getSpies(config)
        team_spies = [s for s in self.game.team if s in all_spies]
        for p, v in zip(self.game.players, votes):
            # This is a spy, who voted for a mission, that had no spies.
            if p in all_spies and v and not team_spies:
                score += 1.0
                factors.append((1.0, "%s, assuming a spy, voted for a mission that had no assumed spies." % (p.name)))
            # This is a spy, who did not vote a mission, that had spies.
            if p in all_spies and not v and team_spies:
                score += 1.0
                factors.append((1.0, "%s, assuming a spy, did not vote a mission that had assumed spies." % (p.name)))
            # This is a Resistance guy who did not vote up the fifth try.
            if self.game.tries == 5 and p not in all_spies and not v:
                score += 2.0
            # This is a Resistance guy who voted up a mission without him!
            if p not in all_spies and len(self.game.team) == 3 and \
               p not in self.game.team and v:
                score += 2.0
        return score, factors

    def oracle_sabotages(self, config, sabotaged):
        spies = [s for s in self.game.team if s in self.getSpies(config)]
        score = max(0, sabotaged - len(spies)) * 100.0
        if score > 0.0:
            return score, [(score, "%s participated in a mission that had %i sabotages." % (self.game.team, sabotaged))]
        else:
            return 0.0, []

    def adviser_vote(self, team):
        if self.spy:
            spies = [s for s in team if s in self.spies]
            if len(spies) > 0 and (self.game.losses == 2 or self.game.wins == 2):
                # self.log.info("Taking a risk since the game could finish.")
                return True
            
            if self.game.tries == 5:
                # self.log.info("Voting up the last mission because Resistance would.")
                return False

            if len(team) == 3:
                # self.log.info("Voting strongly about this team because it's size 3!")
                return self in team

        else: # not self.spy

            # Always approve our own missions.
            if self.game.leader == self:
                # self.log.info("Approving my own mission selection.")
                return True

            # As resistance, always pass the fifth try.
            if self.game.tries == 5:
                # self.log.info("Voting up the last mission to avoid failure.")
                return True
        
        return None

    def onGameRevealed(self, players, spies):
        self.spies = spies

        # Count the number of times each configuration was apparently invalidated.
        self.invalidations = {k: 0.0 for k in permutations([True, True, False, False])}
        # This is used to help justify decisions in hybrid human/bot matches.
        self.factors = {k: [] for k in permutations([True, True, False, False])}

    def likeliest(self, configurations):
        ranked = sorted(configurations, key = lambda c: self.invalidations[c])
        invalidations = self.invalidations[ranked[0]]
        return [r for r in ranked if self.invalidations[r] == invalidations]

    def select(self, players, count):
        likely = self.likeliest(self.invalidations.keys())
        # self.log.info("Selecting randomly from these Resistance teams:")
        # for c in likely:
        #    self.log.info("  %s = %0.2f (%i)" % (self.getResistance(c), self.invalidations[c], len(self.factors[c])))
        config = random.choice(likely)

        # if self.factors[config]:
        #    self.log.info("Chosen configuration had these factors:")
        #    for s, f in self.factors[config]:
        #        self.log.info("%0.2f - %s" % (s, f))
        return [self] + random.sample(self.getResistance(config), count-1)

    def onTeamSelected(self, leader, team):
        for config in self.invalidations:
            score, factors = self.oracle_selection(config)
            self.invalidations[config] += score
            self.factors[config].extend(factors)

    def vote(self, team): 
        advice = self.adviser_vote(team)
        if advice:
            return advice

        # Count the scores of configurations where no spies are selected. 
        scores = []
        matches = []
        for config in self.invalidations:
            if len([s for s in team if s in self.getSpies(config)]) == 0:
                scores.append(self.invalidations[config])
                matches.append(config)
        if not scores:
            # self.log.info("No configuration matches this selection!")
            return random.choice([False, True])

        # Establish whether this meets the criteria for selection...
        score = min(scores)
        threshold = min(self.invalidations.values())
        if score <= threshold:
            # self.log.info("This selection scores %s under threshold %f." % (scores, threshold))
            return random.choice([True, True, True, False])
        else:
            # self.log.info("This selection scores %s above threshold %0.2f." % (scores, threshold))
            # for config in matches:
                # self.log.info("Possible configuration for %s:" % (str(self.getResistance(config))))
                # for s, f in self.factors[config]:
                #   self.log.info("  %0.2f - %s" % (s, f))
            # self.log.info("Options for Resistance were:\n%s" % ("\n".join(["  %s = %0.2f (%i)" % (str(self.getResistance(c)), t, len(self.factors[c])) for c, t in self.invalidations.items() if t == threshold])))
            return random.choice([False, False, False, True])

    def onVoteComplete(self, votes):
        for config in self.invalidations:
            score, factors = self.oracle_voting(config, votes)
            self.invalidations[config] += score
            self.factors[config].extend(factors)

    def getSpies(self, config):
        assert len(config) == 4
        assert all([type(c) is bool for c in config])
        return set([player for player, spy in zip(self.others(), config) if spy])

    def getResistance(self, config):
        assert len(config) == 4
        assert all([type(c) is bool for c in config])
        return set([player for player, spy in zip(self.others(), config) if not spy])

    def onMissionComplete(self, sabotaged):
        for config in self.invalidations:
            score, factors = self.oracle_sabotages(config, sabotaged)
            self.invalidations[config] += score
            self.factors[config].extend(factors)

    def sabotage(self):
        # If there's a chance of losing or winning, don't slow-play!
        if self.game.wins == 2 or self.game.losses == 2:
            # self.log.info("There's a chance of winning or losing.")
            return True
        if len(self.game.team) == 2 and self.game.turn == 1:
            # self.log.info("Missions of size two are too risky...")
            return random.choice([True, False]) 
        spies = [s for s in self.game.team if s in self.spies]
        if len(spies) > 1:
            # self.log.info("Too many spies, can't coordinate!")
            return random.choice([True, False])
        # self.log.info("All other checks failed, why not since I'm a spy?")
        return True

