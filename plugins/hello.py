import re

from cassium.plugin import Plugin

class HelloWorld(Plugin):
    
    def msg(self, query, response):
        if query.message == '`hello':
            response.msg("Hello, " + query.nick + "!")
