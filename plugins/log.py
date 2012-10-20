from cassium.plugin import Plugin

class Log(Plugin):
    
    # TODO: ijoin, ileft, etc.

    def log(self, channel, string):
        print (channel + ': ').ljust(16) + string

    def join(self, query, response):
        self.log(query.channel,
            '-*- %s joined %s' % (query.user, query.channel))

    def leave(self, query, response):
        self.log(query.channel,
            '-*- %s left %s' % (query.user, query.channel))

    def quit(self, query, response):
        for channel in query.channels:
            self.log(channel,
                '-*- %s quit (%s)' % (query.user, query.message))

    def kick(self, query, response):
        self.log(query.channel,
            '-*- %s kicked %s from %s (%s)' %
            (query.kicker, query.kickee, query.channel, query.message))

    def action(self, query, response):
        self.log(query.channel,
            '-*- %s %s' % (query.user, query.message))

    def topic(self, query, response):
        self.log(query.channel,
            '-*- %s set %s\'s topic to: %s' %
            (query.user, query.channel, query.topic))

    def nick(self, query, response):
        for channel in query.channels:
            self.log(channel,
                '-*- %s is now known as %s' % (query.oldname, query.newname))

    def msg(self, query, response):
        self.log(query.channel, '<%s> %s' % (query.nick, query.message))
