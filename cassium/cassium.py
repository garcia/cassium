import glob
import logging
import os
import pprint
import re
import sys
import traceback
from inspect import isclass
try:
    import cPickle as pickle
except ImportError:
    import pickle

from twisted.internet import protocol, reactor
from twisted.words.protocols.irc import IRCClient

from plugin import *

__all__ = ['Cassium', 'CassiumFactory']

class Cassium(IRCClient):
    """Cassium's main class."""

    def __init__(self, config):
        """Initialize Cassium with a configuration module."""
        self.config = config
        self.log = logging.getLogger(__name__)
        # Set up for IRC
        self.nickname = config.nick
        self.realname = config.realname
        self.username = 'A Cassium IRC Bot'
        self.versionName = 'Cassium'
        self.channels = set()
        # Import plugins
        self.plugins = []
        self.load_plugins_recursively('plugins')
        self.builtin_plugins = [Control()]
    
    def load_plugins_recursively(self, directory):
        """Recursively loads or reloads all plugins in the given directory.
        
        The plugins are always loaded in alphabetical order.
        
        """
        for node in sorted(glob.iglob(os.path.join(directory, '*'))):
            # Recurse into directories
            if os.path.isdir(node):
                self.load_plugins_recursively(node)
            # Load plugins found in files
            elif node.endswith('.py'):
                # Don't load __init__.py
                if os.path.split(node)[1] != '__init__.py':
                    # Convert filesystem path to dot-delimited path
                    path = os.path.splitext(node)[0].replace(os.path.sep, '.')
                    self.load_plugins_from_path(path)

    def load_plugins_from_path(self, path):
        """Loads or reloads the plugin(s) at the given path.
        
        If the path points to a module, all plugins in the given module are
        loaded. If the path points to a specific plugin within a module, that
        plugin is loaded on its own.
        
        """
        this_plugin = __import__(path)
        # Navigate to the given path
        for component in path.split('.')[1:]:
            this_plugin = getattr(this_plugin, component)
        # Find subclasses of Plugin and load them
        reload(this_plugin)
        loaded_nothing = True
        for attr in dir(this_plugin):
            this_attr = getattr(this_plugin, attr)
            if (isclass(this_attr) and issubclass(this_attr, Plugin) and
                    this_attr is not Plugin):
                loaded_nothing = False
                self.load_plugin(plugin=this_attr())
        if loaded_nothing:
            self.log.warn('no plugins were found in the module ' + path)

    def load_plugin(self, plugin):
        """Loads or reloads a plugin instance."""
        name = plugin.fqn()
        # Insert logger into plugin
        plugin.log = logging.getLogger(name)
        # Search for an existing copy of the plugin
        for i, existing_plugin in enumerate(self.plugins):
            if name == existing_plugin.fqn():
                self.plugins[i] = plugin
                self.log.info('reloaded ' + name)
                return
        # No existing copy found
        self.plugins.append(plugin)
        self.log.info('imported ' + name)

    def add_channel(self, channel):
        self.channels.add(channel)

    def remove_channel(self, channel):
        try:
            self.channels.remove(channel)
        except KeyError:
            self.log.warn('attempted to remove a channel I hadn\'t joined')

    def signedOn(self):
        """Called when Cassium successfully connects to the IRC server."""
        if hasattr(self.config, 'password'):
                self.msg('NickServ', 'IDENTIFY ' + self.config.password)
        for channel in self.config.channels:
            self.join(channel)
        self.signal(Query(self.channels, 'signedon'), Response(None))

    def joined(self, channel):
        """Called when Cassium joins a channel."""
        self.add_channel(channel)
        query = Query(self.channels, 'ijoin', channel=channel)
        self.signal(query, Response(channel))

    def left(self, channel):
        """Called when Cassium leaves a channel."""
        self.remove_channel(channel)
        query = Query(self.channels, 'ileft', channel=channel)
        self.signal(query, Response(None))

    def kickedFrom(self, channel, kicker, message):
        """Called when Cassium is kicked from a channel."""
        self.remove_channel(channel)
        query = Query(self.channels, 'ikick', channel=channel, user=kicker,
            message=message)
        self.signal(query, Response(kicker))

    def nickChanged(self, nick):
        """Called when Cassium's nickname is changed."""
        query = Query(self.channels, 'inick', oldname=self.nickname,
            newname=nick)
        self.nickname = nick
        self.signal(query, Response(None))

    def privmsg(self, user, channel, message):
        """Called when a user sends a message to Cassium or a channel."""
        # See the comment in Query on ValueError
        try:
            query = Query(self.channels, 'msg', user=user, channel=channel,
                message=message)
        except ValueError:
            return
        # Handles private messages
        target = query.nick
        if any(c in channel for c in '#&'):
            target = channel
        self.signal(query, Response(target))

    def userJoined(self, user, channel):
        """Called when a user joins a channel."""
        query = Query(self.channels, 'join', user=user, channel=channel)
        self.signal(query, Response(channel))

    def userLeft(self, user, channel):
        """Called when a user leaves a channel."""
        query = Query(self.channels, 'leave', user=user, channel=channel)
        self.signal(query, Response(channel))

    def userQuit(self, user, message):
        """Called when a user quits the server."""
        query = Query(self.channels, 'quit', user=user, message=message)
        self.signal(query, Response(None))

    def userKicked(self, kickee, channel, kicker, message):
        """Called when a user is kicked from a channel."""
        query = Query(self.channels, 'kick', kickee=kickee, channel=channel,
            kicker=kicker, message=message)
        self.signal(query, Response(channel))

    def action(self, user, channel, message):
        """Called when a user performs an action."""
        query = Query(self.channels, 'action', user=user, channel=channel,
            message=message)
        # TODO: determine whether IRCClient supports private message actions
        self.signal(query, Response(channel or user))

    def topicUpdated(self, user, channel, topic):
        """Called when a channel's topic is updated."""
        query = Query(self.channels, 'topic', user=user, channel=channel,
            topic=topic)
        self.signal(query, Response(channel))

    def userRenamed(self, oldname, newname):
        """Called when a user changes their nickname."""
        query = Query(self.channels, 'nick', oldname=oldname, newname=newname)
        self.signal(query, Response(newname))

    def signal(self, query, response):
        """Called by the above signals to relay the event to each plugin."""
        # Don't respond to *Serv
        if hasattr(query, 'nick') and query.nick.endswith('Serv'):
            return
        # Convenience
        signaltype = query.type
        try:
            # Check each plugin for an appropriate signal handler
            for plugin in self.plugins + self.builtin_plugins:
                if hasattr(plugin, signaltype):
                    # Ensure the attribute we're looking at is a method
                    if hasattr(getattr(plugin, signaltype), '__call__'):
                        method = getattr(plugin, signaltype)
                        # If this is a builtin plugin, pass it Cassium
                        if plugin in self.builtin_plugins:
                            method(query, self)
                        else:
                            method(query, response)
            # Print log messages
            for message in response._log:
                self.log.info(message)
            # Process dict-based responses
            for channel_and_name, reason in response._kick.iteritems():
                self.kick(*channel_and_name + (reason,))
            for channel, topic in response._topic.iteritems():
                self.topic(channel, topic)
            # Nick change
            if response._nick:
                self.setNick(response._nick)
            # Process list- and set-based responses
            for responsetype in ('join', 'leave', 'mode', 'notice', 'me', 'msg'):
                # e.g. for action in response._msg:
                for action in getattr(response, '_' + responsetype):
                    # Unicode fix
                    # XXX: might be necessary for other response types?
                    if responsetype == 'msg':
                        action = (action[0], action[1].encode('UTF-8'))
                    # e.g. self.msg(*action)
                    getattr(self, responsetype)(*action)
        except Exception:
            self.msg(response._defaulttarget,
                traceback.format_exc().splitlines()[-1])
            traceback.print_exc()
            pprint.pprint(vars(response), stream=sys.stderr)

    def save(self):
        """Calls each plugin's save() method."""
        for plugin in self.plugins:
            plugin.save()

class Control(Plugin):
    """Internal plugin used to provide admins with basic control."""

    controls = ('join', 'leave', 'nick', 'import', 'reconnect', 'restart', 'save')

    def msg(self, query, cassium):
        if not any(query.message.startswith('`' + ctl) for ctl in self.controls):
            return
        # TODO: better authentication
        if query.nick not in cassium.config.admins:
            return cassium.msg(query.channel or query.user,
                'You are not permitted to use this command.')
        command = query.words[0][1:]
        if command == 'join':
            cassium.join(query.words[1])
        elif command == 'leave':
            cassium.leave(query.words[1])
        elif command == 'nick':
            cassium.setNick(query.words[1])
        elif command == 'import':
            cassium.load_plugins_from_path('plugins.' + query.words[1])
            cassium.msg(query.channel or query.user,
                'Loaded ' + query.words[1] + '.')
        elif command == 'save':
            cassium.save()
        elif command == 'reconnect':
            cassium.log.critical('reconnecting')
            cassium.save()
            cassium.quit()
        elif command == 'restart':
            cassium.log.critical('restarting')
            cassium.save()
            reactor.stop()
            os.execv(sys.argv[0], sys.argv)

class CassiumFactory(protocol.ClientFactory):
    """A Twisted factory that instantiates or reinstantiates Cassium."""

    def __init__(self, config):
        self.config = config
        # Set up logging
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, config.log_verbosity))
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(fmt=config.log_format))
        logger.addHandler(handler)


    def buildProtocol(self, addr):
        cassium = Cassium(self.config)
        cassium.factory = self
        return cassium

    def clientConnectionLost(self, connector, reason):
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        reactor.stop()
