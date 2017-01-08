# -*- coding: utf-8 -*-
"""irc2 extensions (cap, sasl, etc)"""

from . import parser, utils
import asyncio
import base64


class IRCCaps(object):
    """
    IRCCaps manages IRCv3 capabilities.
    """

    def __init__(self, client):
        self.client = client
        self.caps = set()
        self.waiting_caps = utils.IDefaultDict(asyncio.Future)

        client.subscribe(parser.Message(verb="CAP"), self._handle_cap)

    async def _handle_cap(self, message):
        _, sub = message.args[:2]
        if sub == "ACK" or sub == "NAK":
            caps = message.args[2]
            for cap in caps.split():
                if sub == "ACK":
                    self.caps.add(cap)
                    self.waiting_caps[cap].set_result(True)
                elif sub == "NAK":
                    self.waiting_caps[cap].set_result(False)

    async def req(self, cap):
        """
        Request a capability from the server. Returns True if we already have
        the capability, or if the server ACKed our request, or False if the
        server responded with NAK.
        """
        await self.client.send("CAP", "REQ", cap)
        while not self.waiting_caps[cap].done():
            await self.client.irc.match(verb="CAP")

        return self.waiting_caps[cap].result()

    async def end(self):
        await self.client.send("CAP", "END")


class IRCSasl(object):
    """
    IRCSasl manages SASL authentication.
    """

    def __init__(self, client):
        self.client = client

    async def auth(self, user, password):
        """
        Perform SASL PLAIN authentication with the given username and password.
        """
        if not await self.client.cap.req("sasl"):
            raise Exception("SASL not available")

        await self.client.send("AUTHENTICATE", "PLAIN")
        await self.client.irc.match(verb="AUTHENTICATE", args=["+"])

        data = base64.b64encode("{0}\x00{0}\x00{1}".format(user, password).encode()).decode()
        await self.client.send("AUTHENTICATE", data)
        result = await self.client.irc.match(verb=["902", "903", "904"])
        if result.verb != "903":
            raise Exception("SASL authentication failed")
        return True


class IRCState(object):
    """
    Track user and channel state.
    """

    def __init__(self, client):
        self.client = client

    async def enable(self):
        await self.client.cap.req("multi-prefix")
        if all([await self.client.cap.req("extended-join"), await self.client.cap.req("account-notify")]):
            return True
        return False


if __name__ == '__main__':
    import doctest
    doctest.testmod()
