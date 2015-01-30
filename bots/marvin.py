import os
import threading

import speech_recognition as speech

import experts


class Marvin(experts.Suspicious):

    def __init__(self, *args, **kwargs):
        super(Marvin, self).__init__(*args, **kwargs)

        self.recognizer = speech.Recognizer()
        self.recognizer.energy_threshold = 4000
        self.stop = False

        self.thread = threading.Thread(target=self.listen)
        self.thread.daemon = True
        self.thread.start()

    def onGameComplete(self, win, spies):
        self.stop = True
        self.thread.join()

    def say(self, message):
        super(Marvin, self).say(message)
        os.system('/usr/bin/say -v Zarvox "%s"' % message)

    def listen(self):
        while not self.stop:
            try:
                with speech.Microphone() as source:
                    print "Listening...",
                    audio = self.recognizer.listen(source, timeout=5.0)
                    print "DONE! (%i)" % len(audio.data)
                try:
                    st = self.recognizer.recognize(audio).lower()
                    print ">", st
                    for prefix in ["i am", "this is"]:
                        if st.startswith(prefix):
                            name = st.replace(prefix, '')
                            self.say("Hello %s!" % name)
                            return
                    if "about" in st:
                        self.respondToQuery(st)
                        return
                    if 'cool' in st:
                        self.say("Robots are always cool!")
                        return
                except LookupError:
                    print "Sorry."
            except NameError:
                pass
            except:
                import traceback
                traceback.print_exc()

    def _extractPlayers(self, message):
        def matches(p):
            return p.name in message or ("#%i" % p.index) in message
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
            return

        # Determine how player fits into most likely configurations.
        p = players.pop()
        spy_score, res_score = 0, 0
        for c in configs:
            spy_score = int(p in self.getSpies(c))
            res_score = int(p in self.getResistance(c))

        # Express beliefs about the current estimates for the player.
        if spy_score == res_score:
            self.say("It's unclear at this stage what %r is playing." % (p.name))
        if spy_score > res_score:
            confidence = "arguably" if res_score > 0 else "likely"
            self.say("I think %r is %s a spy at this stage." % (p.name, confidence))
        if res_score > spy_score:
            confidence = "arguably" if spy_score > 0 else "likely"
            self.say("I think %r is %s resistance at this stage." % (p.name, confidence))
