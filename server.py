import sys
import random

import gevent
from gevent.event import AsyncResult
from geventirc import Client
from geventirc import message
from geventirc import handlers


from competition import CompetitionRunner
from player import Player, Bot
from game import Game


def YesOrNo(b):
    result = {True: 'Yes', False: 'No'}
    return result[b]


class ProxyBot(Bot):

    def __init__(self, name, client):
        self.name = name
        self.client = client

        self._vote = None
        self._select = None
        self._sabotage = None
        self.game = '#game-0001'

    def __call__(self, game, index, spy):
        """This function pretends to be a Builder, but in fact just
        configures this object in place as it's easier."""
        Player.__init__(self, self.name, index)
        self.state = game
        self.spy = spy
        return self

    def bakeTeam(self, team):
        return ', '.join([str(p) for p in team])

    def makePlayer(self, identifier):
        index, name = identifier.split('-')
        return Player(name, int(index))

    @property
    def uuid(self):
        return "%s %s" % (Player.__repr__(self), self.game)

    def onGameRevealed(self, players, spies):
        roles = {True: "Spy", False: "Resistance"}
        s = ""
        if self.spy:
            s = "; SPIES " + self.bakeTeam(spies)
        self.client.msg(self.name, 'REVEAL %s; ID %s; ROLE %s; PLAYERS %s%s.' % (self.game, Player.__repr__(self), roles[self.spy], self.bakeTeam(players), s))

    def onMissionAttempt(self, mission, tries, leader):
        self.client.msg(self.name, 'MISSION %s %i.%i; LEADER %s.' % (self.uuid, mission, tries, Player.__repr__(leader)))

    def select(self, players, count):
        self.client.msg(self.name, 'SELECT %s %i.' % (self.uuid, count))
        self._select = AsyncResult()
        return self._select.get()

    def process_SELECTED(self, msg):
        team = [self.makePlayer(p.strip(' ,.')) for p in msg[4:]]
        self._select.set(team)

    def vote(self, team):
        self.client.msg(self.name, 'VOTE %s; TEAM %s.' % (self.uuid, self.bakeTeam(team)))
        self._vote = AsyncResult()
        return self._vote.get()

    def process_VOTED(self, msg):
        self._vote.set(msg[4] == 'Yes.')

    def onVoteComplete(self, team, votes):
        self.client.msg(self.name, "VOTED %s; TEAM %s; VOTES %s." % (self.uuid, self.bakeTeam(team), ', '.join([YesOrNo(v) for v in votes])))

    def sabotage(self, team):
        self.client.msg(self.name, 'SABOTAGE %s; TEAM %s.' % (self.uuid, self.bakeTeam(team)))
        self._sabotage = AsyncResult()
        return self._sabotage.get()

    def process_SABOTAGED(self, msg):
        self._sabotage.set(msg[4] == 'Yes.')

    def onMissionComplete(self, team, sabotaged):
        self.client.msg(self.name, "RESULT %s; TEAM %s; SABOTAGES %i." % (self.uuid, self.bakeTeam(team), sabotaged))

    def onGameComplete(self, win, spies):
        self.client.msg(self.name, "COMPLETE %s; WIN %s; SPIES %s." % (self.uuid, YesOrNo(win), self.bakeTeam(spies)))


class ResistanceCompetitionHandler(CompetitionRunner):
    """Host that moderates games of THE RESISTANCE given an IRC server."""

    commands = ['PRIVMSG', '001', 'PING']

    def pickPlayersForRound(self):
        participants = [random.choice(self.competitors) for x in range(0,5)]
        return [ProxyBot(bot, self.client) for bot in participants]

    def start(self):
        self.client.send_message(message.Join('#resistance'))
       
        self.main()
        self.show()
   
        self.client.stop()

    def __call__(self, client, msg):
        if msg.command == '001':
            self.client = client
            self.start()
        elif msg.command == 'PING':
            client.send_message(message.Pong())
        else:
            for bot in self.game.bots:
                if bot != bot.makePlayer(msg.params[2]):
                    continue
                name = 'process_'+msg.params[1]
                if hasattr(bot, name):
                    process = getattr(bot, name)
                    # print ' '.join(msg.params[1:])
                    process(msg.params)
            
if __name__ == '__main__':
    
    if len(sys.argv) == 1:
        print 'USAGE: server.py 25 BotName [...]'
        sys.exit(-1)

    irc = Client('localhost', 'aigamedev',  port=6667)
    h = ResistanceCompetitionHandler([s.split('.')[-1] for s in sys.argv[2:]], int(sys.argv[1]))
    irc.add_handler(h)
    irc.start()
    irc.join()
