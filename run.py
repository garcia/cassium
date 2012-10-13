#!/usr/bin/env python
from twisted.internet import reactor

from cassium.cassium import Cassium, CassiumFactory
#import config

def main():
    factory = CassiumFactory()
    #reactor.connectTCP(config.server, config.port, factory)
    reactor.connectTCP('localhost', 6667, factory)
    reactor.run()


if __name__ == "__main__":
    main()
