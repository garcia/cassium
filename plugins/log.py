import logging

from cassium.plugin import Plugin

class Log(Plugin):
    
    def _log(self, channel, string):
        if channel: channel += ': '
        self.log.info(channel.rjust(16) + '-*- ' + string)

    def _logmsg(self, channel, string):
        self.log.info((channel + ': ').rjust(16) + string)
    
    def signedon(self, query, response):
        self._log('', 'Signed on')

    def ijoin(self, query, response):
        self._log(query.channel, 'Joined %s' % (query.channel))

    def ileft(self, query, response):
        self._log(query.channel, 'Left %s' % (query.channel))

    def ikick(self, query, response):
        self._log(query.channel,
            'Kicked from %s by %s (%s)' %
            (query.channel, query.kicker, query.message))

    def inick(self, query, response):
        self.nick(query, response)

    def join(self, query, response):
        self._log(query.channel,
            '%s joined %s' % (query.user, query.channel))

    def leave(self, query, response):
        self._log(query.channel,
            '%s left %s' % (query.user, query.channel))

    def quit(self, query, response):
        self._log('',
            '%s quit (%s)' % (query.user, query.message))

    def kick(self, query, response):
        self._log(query.channel,
            '%s kicked %s from %s (%s)' %
            (query.kicker, query.kickee, query.channel, query.message))

    def action(self, query, response):
        self._log(query.channel,
            '%s %s' % (query.user, query.message))

    def topic(self, query, response):
        self._log(query.channel,
            '%s set %s\'s topic to: %s' %
            (query.user, query.channel, query.topic))

    def nick(self, query, response):
        self._log('',
            '%s is now known as %s' % (query.oldname, query.newname))

    def msg(self, query, response):
        self._logmsg(query.channel, '<%s> %s' % (query.nick, query.message))
