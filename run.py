#!/usr/bin/env python
import os
import sys

from twisted.internet import reactor

from cassium.cassium import Cassium, CassiumFactory

def main():
    factory = CassiumFactory()
    reactor.connectTCP('localhost', 6667, factory)
    reactor.run()

if __name__ == "__main__":
    main()
