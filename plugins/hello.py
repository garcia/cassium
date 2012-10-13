from cassium.plugin import CassiumPlugin

class HelloWorld(CassiumPlugin):
    
    triggers = [r'^`hello$']

    def run(self, response, user, channel, message):
        response.msg("Hello, world!")
