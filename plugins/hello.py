from cassium.plugin import CassiumPlugin

class HelloWorld(CassiumPlugin):
    
    triggers = [r'^`hello$']

    def run(self, user, channel, message):
        return "Hello, world!"
