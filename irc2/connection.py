# -*- coding: utf-8 -*-
"""irc2 connection management"""

from . import parser
import asyncio
import socket
import logging

class IRCConnection(object):
    """
    IRCConnection respresents the lowest level of abstraction in the library.
    It exposes an iterator interface over incoming messages, as well as helpers
    to wait for messages matching a certain pattern.

    >>> for message in conn:  # doctest: +SKIP
    ...     print(message)
    ...     break
    Message(tags={}, prefix="orwell.freenode.net", verb="NOTICE", args=["*", "Looking up your hostname..."])

    Instance variables:
        host        the IRC server to connect to
        port        the IRC server's port
        ssl         whether or not to attempt a secure connection
        connected   whether or not a connection has been established
        callback    a function to call when a message is received while waiting
                    for a pattern to be matched
    """

    def __init__(self, host="chat.freenode.net", port=6697, ssl=True):
        self.host = host
        self.port = port
        self.ssl = ssl
        self.connected = False
        self.callback = None
        self.reader = None
        self.writer = None

    def shutdown(self):
        # TODO: we're still leaking a fd.
        self.reader.feed_eof()
        if self.writer:
            self.writer.close()

    async def connect(self):
        """
        Idempotently establish a connection to the IRC server.
        """
        if not self.connected:
            # TODO: make ipv6 configurable, or figure out why it takes so long.
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port, ssl=self.ssl, family=socket.AF_INET)
            self.connected = True

        return self

    async def __aiter__(self):
        await self.connect()
        return self

    async def __anext__(self):
        line = await self.reader.readline()
        if line:
            return parser.parse_line(line)
        else:
            raise StopAsyncIteration

    async def match(self, *pats, **kwargs):
        """
        Wait for a message matching a pattern. Follows the Message.matches
        rules for matching. Multiple Messages can be passed, or keyword
        arguments to construct a single Message can be passed:

        >>> await conn.match(verb="PRIVMSG")  # doctest: +SKIP
        >>> await conn.match(Message(verb="PRIVMSG"), Message(args=["#channel"]))  # doctest: +SKIP
        """
        if len(pats):
            pats = pats
        else:
            pats = [parser.Message(**kwargs)]

        while True:
            line = parser.parse_line(await self.reader.readline())
            await self.callback(line)
            if any(pat.matches(line) for pat in pats):
                return line

    def send(self, *args):
        """
        Send an IRC message immediately.

        >>> conn.send("PRIVMSG", "#channel", "hello there")  # doctest: +SKIP
        """
        if len(args) == 0:
            return
        elif len(args) == 1:
            line = args[0].encode()
        else:
            line = (" ".join(args[:-1]) + " :" + args[-1]).encode()

        if not line.endswith(b"\n"):
            line = line + b"\n"

        logging.info("Send: {}".format(parser.parse_line(line)))
        self.writer.write(line)
