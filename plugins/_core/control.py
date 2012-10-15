from cassium.plugin import Plugin

class Control(Plugin):

    triggers = [
        '^`(join|leave|nick|import)',
    ]

    def run(self, query, response):
        if query.nick not in query.config.admins:
            return response.msg('You are not permitted to use this command.')
        if query.words[0] == '`join':
            response.join(query.words[1])
        elif query.words[0] == '`leave':
            response.leave(query.words[1])
        elif query.words[0] == '`nick':
            response.nick(query.words[1])
        elif query.words[0] == '`import':
            response.load('plugins.' + query.words[1])
            response.msg('Loaded ' + query.words[1] + '.')
