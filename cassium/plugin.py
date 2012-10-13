import re

__all__ = ['CassiumPlugin', 'Response']

class CassiumPlugin(object):
    
    triggers = []

    def __init__(self):
        """Initialize the plugin.

        This automatically compiles all trigger regular expressions. If you
        modify the trigger list at runtime, you'll want to compile any new
        triggers yourself.

        """
        for i, trigger in enumerate(self.triggers):
            self.triggers[i] = re.compile(trigger)

    def run(self, *args, **kwargs):
        raise NotImplementedError()

    def __str__(self):
        return '<CassiumPlugin %s>' % self.__class____name__

class Response(object):
    """An object that is passed among all triggered plugins for a message.

    More specifically, a Response object is initialized with the message
    information and passed as an argument to each triggered plugin. The
    plugin then modifies that object by calling it 

    """

    def __init__(self, user, channel, message):
        self._user = user
        self._channel = channel
        self._message = message

        # Initialize response values
        self._msg = []       # Duplicate messages permitted
        self._join = set()   # Only makes sense to join a channel once
        self._leave = set()  #   same goes for leaving
        self._kick = {}      # Only one user kick per channel
        self._topic = {}     # Only one topic set per channel
        self._mode = []      # Too complex to restrict meaningfully
        self._notice = []    # Same idea as _messages
        self._nick = None    # You're either changing it or you're not
        self._me = []        # Same idea as _messages

    def _target(self, target):
        return target or self._channel or self._user

    def msg(self, message, target=None):
        self._msg.append((self._target(target), message))

    def msgs(self, messages, target=None):
        self._msg.extend([(self._target(target), m) for m in messages])
 
    def join(self, channel, key=None):
        self._join.add((channel, key))

    def leave(self, channel, reason=None):
        self._leave.add((channel, reason))

    def kick(self, channel, user, reason=None):
        self._kick[(channel, user)] = reason

    def topic(self, channel, topic):
        self._topic[channel] = topic

    def mode(self, channel, set_, modes, limit=None, user=None, mask=None):
        self._mode.append((channel, set_, modes, limit, user, mask))

    def notice(self, user, message):
        self._notice.append((user, message))

    def nick(self, nick):
        self._nick = nick

    def me(self, channel, action):
        self._me.append((channel, action))
