from __future__ import print_function

import glob
import os
import re
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

class Cassium(IRCClient):
    """Cassium's main class.
    
    Takes a single argument, an imported configuration file. This is
    unnecessary if config.py is present in the current working directory.

    """

    plugins = []

    def __init__(self, config_=None):
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
    
    def load_plugins_recursively(self, directory):
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
        # Find subclasses of CassiumPlugin and load them
        reload(this_plugin)
        loaded_nothing = True
        for attr in dir(this_plugin):
            this_attr = getattr(this_plugin, attr)
            if (isclass(this_attr) and
                    issubclass(this_attr, CassiumPlugin) and
                    this_attr is not CassiumPlugin):
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
        if hasattr(config, 'password'):
                self.msg('NickServ', 'IDENTIFY ' + config.password)
        for channel in config.channels:
            self.join(channel)

    def privmsg(self, user, channel, message):
        # See the comment in Query on ValueError
        try:
            query = Query(config, user, channel, message)
        except ValueError:
            return
        response = Response(user, channel, message)
        # Check each plugin's triggers
        for plugin in self.plugins:
            for trigger in plugin.triggers:
                if re.match(trigger, message):
                    plugin.run(query, response)
        # Process list- and set-based responses
        for response_type in ('msg', 'join', 'leave', 'mode', 'notice', 'me'):
            # i.e. for action in response._msg:
            for action in getattr(response, '_' + response_type):
                # i.e. self.msg(*action)
                getattr(self, response_type)(*action)
        # Process dict-based responses
        for channel_and_name, reason in response._kick.iteritems():
            self.kick(*channel_and_name + (reason,))
        for channel, topic in response._topic.iteritems():
            self.topic(channel, topic)
        # And the rest
        if response._nick:
            self.setNick(response._nick)
        for path in response._load:
            self.load_plugins_from_path(path)

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
