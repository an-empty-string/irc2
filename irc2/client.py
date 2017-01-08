"""irc2 client core"""

from . import connection, event, ext, handler, utils
import asyncio
import logging

class IRCClientConfig(object):
    """
    IRCClientConfig is a helper to execute coroutines on an IRCConnection
    object. Its basic usage is something like:

        conf = IRCClientConfig("chat.freenode.net", 6697)
        conf.register("nick", "ident", "realname")
        conf.join("#channel", "#otherchannel")
        client = conf.configure()
        ... some event handler setup ...
        import asyncio
        asyncio.get_event_loop().run_forever()
    """

    def __init__(self, host, port, ssl=True):
        self.conn = connection.IRCConnection(host, port, ssl)
        self.client = IRCClient(self.conn)
        self.coros = []

    async def _run(self):
        await self.conn.connect()
        for coro in self.coros:
            await coro
        await self.client.handle()

    def configure(self):
        asyncio.get_event_loop().create_task(self._run())
        return self.client

    def _add_coro(self, path, *args, **kwargs):
        item = self.client
        for point in path:
            item = getattr(item, point)
        self.coros.append(item(*args, **kwargs))

    def __getattr__(self, attr):
        return utils.AttrGetFollower([attr], self._add_coro)

class IRCClient(object):
    """
    IRCClient wraps an IRCConnection to provide helpers, manages extensions
    (for things like SASL, IRCv3 capabilities, and state tracking), and
    dispatches IRC messages to interested handlers.

    Additionally, IRCClients have Dispatchers in order to keep track of higher-
    level events. Subscriptions to lower-level Messages are not required in
    most applications. Use decorators like "client.event.message" to subscribe
    functions to Dispatcher events.
    """
    def __init__(self, irc):
        self.subscriptions = []
        self.bucket = utils.TokenBucket(4, 2)
        self.event = event.Dispatcher()

        self.irc = irc
        self.irc.callback = self._run_handlers

        self.handler = handler.IRCHandler(self)
        self.cap = ext.IRCCaps(self)
        self.sasl = ext.IRCSasl(self)
        self.state = ext.IRCState(self)

    async def send(self, *args):
        """
        Same as IRCConnection.send, but ratelimiting is enforced.
        """
        await self.bucket.wait()
        self.irc.send(*args)

    async def register(self, nick, user, realname, password=None):
        """
        Send the server password (if set), nickname, user, and realname. Waits
        for registration to complete before finishing.
        """
        await self.cap.end()

        if password:
            await self.send("PASS", password)
        await self.send("NICK", nick)
        await self.send("USER", user, user, user, realname)
        await self.irc.match(verb=["001"])

    def subscribe(self, pat, handler):
        """
        Subscribe the given handler to receive IRC messages that match the
        given pattern. Message.matches rules apply.
        """
        self.subscriptions.append((pat, handler))

    async def _run_handlers(self, line):
        for pat, line_handler in self.subscriptions:
            if pat.matches(line):
                await line_handler(line)

    async def handle(self):
        """
        Handle incoming IRC messages, dispatching them to subscribed handlers.
        """
        logging.info("Received event loop control, now dispatching events")
        async for line in self.irc:
            await self._run_handlers(line)

    ## Commands
    async def join(self, *channels):
        """
        Join the specified channel or channels.
        """
        left = channels[:]
        while left:
            current, left = utils.join_max_length(left, ",", 400)
            await self.send("JOIN", current)

        not_joined = set(channels)
        while not_joined:
            message = await self.irc.match(verb="JOIN")
            channel = message.args[0]
            not_joined.discard(channel)

        return True

    async def say(self, dest, text):
        """
        Send a message to the given destination with the given text.
        """
        words = text.split(" ")
        if all(len(word) < 350 for word in words):
            # try to split at spaces when possible
            left = words[:]
            while left:
                current, left = utils.join_max_length(left, " ", 350)
                await self.send("PRIVMSG", dest, current)

        else:
            left = text[:]
            while left:
                current, left = utils.join_max_length(left, "", 350)
                await self.send("PRIVMSG", dest, current)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
