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

from ircbot import SingleServerIRCBot
from irclib import nm_to_n

# Attempt to get configuration from the current directory
try:
    import config as cfg
except:
    cfg = None
global cfg

class Cassium(SingleServerIRCBot):
    """Cassium's main class.
    
    Takes a single argument, an imported configuration file. This is
    unnecessary if config.py is present in the current working directory.

    """

    plugins = []

    def __init__(self, config=None):
        global cfg
        # config must be given if the import above failed
        if config: cfg = config
        elif not cfg: raise AttributeError('no configuration found')
        # initialize the IRC bot
        SingleServerIRCBot.__init__(self, [(cfg.server, cfg.port)], cfg.nick,
            cfg.realname)
        # import plugins
        self.plugins = self.load_plugins_recursively('plugins/')
    
    def load_plugins_recursively(self, directory):
        plugins = []
        for node in glob.iglob(directory + '*'):
            if os.path.isdir(node):
                plugins.extend(self.load_plugins_recursively(node + '/'))
            elif node.endswith('.py') and '__init__' not in node:
                # Convert filesystem path to dot-delimited path
                path = os.path.splitext(node)[0].replace(os.path.sep, '.')
                plugins.append(self.load_plugin(path))
        return plugins

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

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        if hasattr(cfg, 'password'):
                self.connection.privmsg('NickServ', 'IDENTIFY ' + cfg.password)
        for channel in cfg.channels:
            c.join(channel)
