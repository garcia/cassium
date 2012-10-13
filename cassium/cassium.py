from __future__ import print_function

import glob
import imp
import os
import re
import sys
import traceback
from threading import Timer
try:
    import cPickle as pickle
except ImportError:
    import pickle

from twisted.internet import protocol, reactor
from twisted.words.protocols.irc import IRCClient

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
        # config must be given if the import above failed
        if config_: config = config_
        elif not config: raise AttributeError('no configuration found')
        # set up for IRC
        self.nickname = config.nick
        self.realname = config.realname
        self.username = "A Cassium IRC Bot"
        self.versionName = "Cassium"
        # import plugins
        self.load_plugins_recursively('plugins/')
    
    def load_plugins_recursively(self, directory):
        plugins = []
        for node in glob.iglob(directory + '*'):
            if os.path.isdir(node):
                self.load_plugins_recursively(node + '/')
            elif node.endswith('.py') and '__init__' not in node:
                # Convert filesystem path to dot-delimited path
                path = os.path.splitext(node)[0].replace(os.path.sep, '.')
                self.load_plugin(path)

    def load_plugin(self, plugin):
        """Loads or reloads a plugin."""
        # Import the plugin
        this_plugin = __import__(plugin)
        for component in plugin.split('.')[1:]:
            this_plugin = getattr(this_plugin, component)

        # Search for an existing copy of the plugin
        for i, plugin in enumerate(self.plugins):
            if this_plugin.__name__ == plugin.__name__:
                self.plugins[i] = this_plugin
                print("Reloaded " + this_plugin.__name__)
                break
        # No existing copy found
        else:
            self.plugins.append(this_plugin)
            print("Imported " + this_plugin.__name__)

    def signedOn(self):
        if hasattr(config, 'password'):
                self.msg('NickServ', 'IDENTIFY ' + config.password)
        for channel in config.channels:
            self.join(channel)

    def privmsg(self, user, channel, message):
        for plugin in self.plugins:
            for trigger in plugin.triggers:
                if re.match(trigger, message):
                    self.msg(channel or user,
                        self.trigger.run(user, channel, message))

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
