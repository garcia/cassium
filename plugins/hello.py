from cassium.plugin import CassiumPlugin

class HelloWorld(CassiumPlugin):
    
    triggers = [r'^`hello$']

    def run(self, query, response):
        response.msg("Hello, " + ("admin " if query.nick in query.config.admins else "") + query.nick + "!")
