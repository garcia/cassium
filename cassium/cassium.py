from __future__ import print_function

import glob
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

# Why isn't this particular import relative to run.py's cwd?
from plugin import *

# Attempt to get configuration from the current directory
try:
    import config
except ImportError:
    config = None

# Do not expose imported modules
__all__ = ['Cassium', 'CassiumFactory']

class Cassium(IRCClient):
    """Cassium's main class."""

    plugins = []

    def __init__(self, config_=None):
        """Initialize Cassium.
        
        If there is no configuration module in the current working directory,
        one must be passed as the sole argument to the constructor.

        """
        global config
        # Config must be given if the import above failed
        if config_: config = config_
        elif not config: raise AttributeError('no configuration found')
        # Set up for IRC
        self.nickname = config.nick
        self.realname = config.realname
        self.username = 'A Cassium IRC Bot'
        self.versionName = 'Cassium'
        # Import plugins
        self.load_plugins_recursively('plugins/')
        self.builtin_plugins = [Cassium.Control()]
    
    def load_plugins_recursively(self, directory):
        """Recursively loads or reloads all plugins in the given directory."""
        plugins = []
        for node in sorted(glob.iglob(directory + '*')):
            if os.path.isdir(node):
                self.load_plugins_recursively(node + '/')
            elif node.endswith('.py') and '__init__' not in node:
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
            print('Warning: no plugins were found in the module ' + path)

    def load_plugin(self, plugin):
        """Loads or reloads a plugin instance."""
        name = plugin.__class__.__name__
        # Search for an existing copy of the plugin
        for i, existing_plugin in enumerate(self.plugins):
            if name == existing_plugin.__class__.__name__:
                self.plugins[i] = plugin
                print('Reloaded ' + name)
                return
        # No existing copy found
        self.plugins.append(plugin)
        print('Imported ' + name)

    def signedOn(self):
        """Called upon successfully connecting to the IRC server."""
        if hasattr(config, 'password'):
                self.msg('NickServ', 'IDENTIFY ' + config.password)
        for channel in config.channels:
            self.join(channel)

    def privmsg(self, user, channel, message):
        """Called when a user sends a message to the bot or a channel."""
        # See the comment in Query on ValueError
        try:
            query = Query(config, 'msg', user=user, channel=channel,
                message=message)
        except ValueError:
            return
        # "channel or user" is needed to handle private messages to the bot
        self.signal(query, Response(channel or user))

    def userJoined(self, user, channel):
        """Called when a user joins a channel."""
        query = Query(config, 'join', user=user, channel=channel)
        self.signal(query, Response(channel))

    def userLeft(self, user, channel):
        """Called when a user leaves a channel."""
        query = Query(config, 'leave', user=user, channel=channel)
        self.signal(query, Response(channel))

    def userQuit(self, user, message):
        """Called when a user quits the server."""
        query = Query(config, 'quit', user=user, message=message)
        self.signal(query, Response(None))

    def userKicked(self, user, channel):
        """Called when a user is kicked from a channel."""
        query = Query(config, 'kick', user=user, channel=channel)
        self.signal(query, Response(channel))

    def action(self, user, channel, message):
        """Called when a user performs an action."""
        query = Query(config, 'action', user=user, channel=channel,
            message=message)
        # TODO: determine whether IRCClient supports private message actions
        self.signal(query, Response(channel or user))

    def topicUpdated(self, user, channel, topic):
        """Called when a channel's topic is updated."""
        query = Query(config, 'topic', user=user, channel=channel, topic=topic)
        self.signal(query, Response(channel))

    def userRenamed(self, oldname, newname):
        """Called when a user changes their nickname."""
        query = Query(config, 'nick', oldname=oldname, newname=newname)
        self.signal(query, Response(newname))

    def signal(self, query, response):
        # Convenience
        signaltype = query._type
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
            pprint.pprint(vars(response))

    class Control(Plugin):
        """Internal plugin used to provide admins with basic control."""

        def msg(self, query, cassium):
            if not re.match(r'^`(join|leave|nick|import|reconnect|restart)',
                    query.message):
                return
            if query.nick not in query.config.admins:
                return cassium.msg(query.channel or query.user,
                    'You are not permitted to use this command.')
            if query.words[0] == '`join':
                cassium.join(query.words[1])
            elif query.words[0] == '`leave':
                cassium.leave(query.words[1])
            elif query.words[0] == '`nick':
                cassium.setNick(query.words[1])
            elif query.words[0] == '`import':
                cassium.load_plugins_from_path('plugins.' + query.words[1])
                cassium.msg(query.channel or query.user,
                    'Loaded ' + query.words[1] + '.')
            elif query.words[0] == '`reconnect':
                cassium.quit()
            elif query.words[0] == '`restart':
                reactor.stop()
                print("===== RESTARTING =====")
                os.execvp('./run.py', sys.argv)

class CassiumFactory(protocol.ClientFactory):
    """A Twisted factory that instantiates or reinstantiates Cassium."""

    def buildProtocol(self, addr):
        cassium = Cassium()
        cassium.factory = self
        return cassium

    def clientConnectionLost(self, connector, reason):
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        reactor.stop()
