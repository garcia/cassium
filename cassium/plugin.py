import re

# Do not expose imported modules
__all__ = ['Plugin', 'Query', 'Response']

class Plugin(object):
    """The base class for all Cassium plugins.

    Subclasses must override the run() method. __init__ may also be overridden
    if necessary, but it would be advisable to call the superclass's __init__
    as well.

    """

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


class Query(object):
    """An object that is passed among all triggered plugins for a message.
    
    Query objects have the following read-only properties:
        
        * nick: the nickname of the user that sent the privmsg
        * host: the host of the user
        * channel: the channel in which the privmsg was sent
        * message: the message string
        * words: the message as a list of space-separated words
        * config: Cassium's configuration module
    
    """

    def __init__(self, config, user, channel, message):
        # Raises ValueError on server messages (user string has no '!')
        self._nick, self._host = user.split('!', 1)
        self._channel = channel
        self._message = message
        self._words = message.split(' ')
        self._config = config

    @property
    def nick(self): return self._nick

    @property
    def host(self): return self._host

    @property
    def channel(self): return self._channel

    @property
    def message(self): return self._message

    @property
    def words(self): return self._words

    @property
    def config(self): return self._config


class Response(object):
    """An object that is passed among all triggered plugins for a message.

    More specifically, a Response object is initialized with the message
    information and passed as an argument to each triggered plugin. The
    plugin then responds using the given methods.

    """

    def __init__(self, user, channel):
        self._defaulttarget = channel or user

        # Initialize response values
        self._msg = []      # Duplicate messages permitted
        self._join = set()  # Only makes sense to join a channel once at a time
        self._leave = set() # Same idea as _join
        self._kick = {}     # Only one user kick per channel
        self._topic = {}    # Same idea as _kick
        self._mode = []     # Too complex to restrict meaningfully
        self._notice = []   # Same idea as _messages
        self._nick = None   # You're either changing it or you're not
        self._me = []       # Same idea as _messages

    def _target(self, target):
        return target or self._defaulttarget

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
