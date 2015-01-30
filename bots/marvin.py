import os
import random
import threading
import subprocess

import speech_recognition as speech

import experts


class Marvin(experts.Suspicious):

    def __init__(self, *args, **kwargs):
        super(Marvin, self).__init__(*args, **kwargs)

        self.recognizer = speech.Recognizer()
        self.recognizer.energy_threshold = 1000
        self.stop = False

        self.thread = threading.Thread(target=self.listen)
        self.thread.daemon = True
        self.thread.start()

    def onGameComplete(self, win, spies):
        self.stop = True
        self.thread.join()

    def _say(self, message):
        # os.system('/usr/bin/say -v Zarvox "%s"' % message)
        print "saying..."
        subprocess.call(['/usr/bin/say', '-v', 'Zarvox', "%s" % message])
        print ".said!"

    def listen(self):
        while not self.stop:
            try:
                with speech.Microphone() as source:
                    print "Listening...",
                    audio = self.recognizer.listen(source)
                    print "DONE! (%i)" % len(audio.data)
                try:
                    st = self.recognizer.recognize(audio).lower()
                    print "<<", st
                    for prefix in ["i am", "this is"]:
                        if st.startswith(prefix):
                            name = st.replace(prefix, '')
                            self._say("Hello %s!" % name)
                            continue
                    if "about" in st:
                        print "QUERY:"
                        self.respondToQuery(st)
                        continue
                    if 'cool' in st:
                        self._say("Robots are always cool!")
                        continue
                    if random.random() > 0.75:
                        self._say("What a rust bucket!")
                    print ">>"
                except LookupError:
                    print "Sorry."
            except:
                import traceback
                traceback.print_exc()

    def _extractPlayers(self, message):
        def matches(p):
            return p.name.lower() in message or ("#%i" % p.index) in message
        return set([p for p in self.game.players if matches(p)])

    def onMessage(self, source, message):
        # Only respond to queries directly addressed to this bot.
        if not message.startswith(self.name) or 'about' not in message:
            return

        self.respondToQuery(message)

    def respondToQuery(self, message):
        players = self._extractPlayers(message) - set([self])
        configs = self.likeliest()
        if len(players) != 1:
            print "no players"
            return

        print "configs", configs
        # Determine how player fits into most likely configurations.
        p = players.pop()
        spy_score, res_score = 0, 0
        for c in configs:
            spy_score = int(p in self.getSpies(c))
            res_score = int(p in self.getResistance(c))

        # Express beliefs about the current estimates for the player.
        if spy_score == res_score:
            self._say("%r has high entropy." % (p.name))
        if spy_score > res_score:
            if res_score > 0:
                # arguably
                self._say("%r has some suspicious bits." % (p.name))
            else:
                # likely
                self._say("%r should optimize its spy policy." % (p.name))
        if res_score > spy_score:
            if spy_score > 0:
                # arguably
                self._say("%r's bits are somewhat clean." % (p.name))
            else:
                # likely
                self._say("%r follows a resistance policy." % (p.name))                
