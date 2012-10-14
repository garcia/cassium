from cassium.plugin import Plugin

class HelloWorld(Plugin):
    
    triggers = [r'^`hello$']

    def run(self, query, response):
        response.msg("Hello, " + ("admin " if query.nick in query.config.admins else "") + query.nick + "!")
