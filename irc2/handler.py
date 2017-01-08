# -*- coding: utf-8 -*-
"""irc2 low-level event handler"""

from . import utils
from .parser import Message
import logging


class IRCHandler(object):
    """
    IRCHandler handles incoming messages from an IRCClient. This is usually not
    something applications have to worry about.
    """

    def __init__(self, client):
        client.subscribe(Message(), self.handle_all)
        client.subscribe(Message(verb="PING"), self.handle_ping)
        client.subscribe(Message(verb="005"), self.handle_005)
        client.subscribe(Message(verb="PRIVMSG"), self.handle_privmsg)

        client.features = utils.IDict()
        self.client = client

    async def handle_all(self, message):
        logging.info("Recv: {}".format(message))

    async def handle_005(self, message):
        server_features = message.args[1:]
        for feature in server_features:
            if "=" in feature:
                key, value = feature.split("=", maxsplit=1)
                self.client.features[key] = value
            else:
                self.client.features[feature] = True
        logging.info("Received new features: {}".format(self.client.features))

    async def handle_privmsg(self, message):
        target, text = message.args
        await self.client.event.fire("message", message, message.prefix, target, text)

    async def handle_ping(self, message):
        resp = message.args[0] if message.args else "PONG"
        await self.client.send("PONG", resp)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
