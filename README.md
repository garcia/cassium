cassium
=======

A lightweight IRC bot framework.

# Plugins

Plugins are simple and intuitive to write. They extend the Plugin class and define methods for handling signals. [**HelloWorld**](plugins/hello.py) is a good starting point:

    from cassium.plugin import Plugin

    class HelloWorld(Plugin):
        
        def msg(self, query, response):
            if query.message == '!hello': 
                response.msg("Hello, %s!" % query.nick)

For a more detailed look at the signals and responses available, look into the [Log](plugins/log.py) plugin and the documentation for the [Response](cassium/plugin.py) object.

# Dependencies

* 2.6 <= Python < 3
* [Twisted](http://twistedmatrix.com/) >= 8.2
