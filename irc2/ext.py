"""irc2 extensions (cap, sasl, etc)"""

import base64

class IRCCaps(object):
    """
    IRCCaps manages IRCv3 capabilities.
    """
    def __init__(self, client):
        self.client = client
        self.caps = set()

    async def req(self, cap):
        """
        Request a capability from the server. Returns True if we already have
        the capability, or if the server ACKed our request, or False if the
        server responded with NAK.
        """
        if cap in self.caps:
            return True
        await self.client.send("CAP", "REQ", cap)
        message = await self.client.irc.match(Message(verb="CAP", args=[None, ["ACK", "NAK"], cap]))
        _, sub, current_cap = message.args

        if sub == "ACK":
            self.caps.add(cap)
            return True
        elif sub == "NAK":
            return False

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
        if all([await self.client.cap.req("extended-join"),
                await self.client.cap.req("account-notify")]):
            return True
        return False

if __name__ == '__main__':
    import doctest
    doctest.testmod()
