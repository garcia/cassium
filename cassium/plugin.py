import os
try:
    import cPickle as pickle
except ImportError:
    import pickle
import re

# Do not expose imported modules
__all__ = ['Plugin', 'Query', 'Response']

# TODO: documentation

class Plugin(object):
    """The base class for all Cassium plugins."""

    def __init__(self):
        self.load()

    def fqn(self):
        return self.__class__.__module__ + '.' + self.__class__.__name__

    def savefile(self):
        return os.path.join('save', self.fqn() + '.pck')

    def load(self):
        savefile = self.savefile()
        if os.path.isfile(savefile):
            with open(savefile, 'r') as sf:
                self.__dict__.update(pickle.load(sf))

    def save(self):
        savefile = self.savefile()
        with open(savefile, 'w') as sf:
            pickle.dump(self.__dict__, sf)

    def __str__(self):
        return '<Plugin %s>' % self.__class__.__name__


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

    def __init__(self, channels, signaltype, **kwargs):
        self.channels = frozenset(channels)
        self.type = signaltype
        for k, v in kwargs.items():
            # Translates to e.g. self.message = kwargs['message']
            setattr(self, k, v)
            if k == 'message':
                self.words = v.split(' ')
            elif k == 'user':
                try:
                    self.nick, self.host = v.split('!', 1)
                except:
                    self.nick = v


class Response(object):
    """An object that is passed among all triggered plugins for a message.

    More specifically, a Response object is initialized with the message
    information and passed as an argument to each triggered plugin. The
    plugin then responds using the given methods.

    """

    def __init__(self, defaulttarget):
        self._defaulttarget = defaulttarget

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
