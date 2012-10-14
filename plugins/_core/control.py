from cassium.plugin import Plugin

class Control(Plugin):

    triggers = [
        '^`sudo (join|leave|nick|import)',
    ]

    def run(self, query, response):
        if query.nick not in query.config.admins:
            return response.msg('You are not permitted to use this command.')
        if query.words[1] == 'import':
            response.load('plugins.' + query.words[2])
            response.msg('Loaded ' + query.words[2] + '.')
        elif query.words[1] == 'join':
            response.join(query.words[2])
        elif query.words[1] == 'leave':
            response.leave(query.words[2])
        elif query.words[1] == 'nick':
            response.nick(query.words[2])
