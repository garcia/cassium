class CassiumPlugin(object):
    
    triggers = []

    def run(self, *args, **kwargs):
        raise NotImplementedError()

    def __str__(self):
        return '<CassiumPlugin %s>' % self.__name__
