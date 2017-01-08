"""irc2.ircd client abstractions"""

from . import utils
from .handler import handler
from .numerics import *
import asyncio
import collections
import uuid

class Client(object):
    def __init__(self, reader, writer, manager, handler):
        self.id = str(uuid.uuid4())
        self.reader = reader
        self.writer = writer
        self.manager = manager
        self.handler = handler
        self.registered = False

        self.futures = collections.defaultdict(asyncio.Future)
        self.data = collections.defaultdict(lambda: None)
        self.data["host"] = self.writer.get_extra_info("peername")[0]
        self.data["modes"] = set()
        self.data["channels"] = set()

        manager.loop.create_task(self.send_welcome())

    def hostmask(self):
        return self.data["nickname"] + "!" + self.data["ident"] + "@" + self.data["host"]

    async def send_welcome(self):
        await asyncio.wait([self.futures["nick"], self.futures["user"]])
        self.registered = True
        self.manager.map[self.data["nickname"]] = self
        utils.send_welcome(self)

    def write(self, line):
        self.writer.write(line)

    def send(self, *data):
        self.handler.send(self, *data)

    def send_numeric(self, *data):
        self.handler.send_numeric(self, *data)

    def all_channel_clients(self):
        result = set()
        for chan in self.data["channels"]:
            result |= set(chan.members.keys())
        return result

    async def drain(self):
        result = await self.writer.drain()
        print(result)

    def check_registered(self):
        if not self.registered:
            self.send_numeric(ERR_NOTREGISTERED, "You have not registered")
            return False
        return True

    def set_nick(self, nick):
        self.manager.map[nick] = self
        self.manager.map.pop(self.data["nickname"], None)
        self.data["nickname"] = nick

    def done(self):
        if self in self.manager:
            self.manager.remove(self)

        while self.data["channels"]:
            del self.data["channels"].pop().members[self]

class ClientManager(set):
    def __init__(self):
        self.map = {}
        super().__init__()

    def write_all(self, line):
        for client in self:
            client.write(line)

    async def drain_all(self):
        asyncio.wait(client.drain() for client in self)

    def new(self, reader, writer, handler):
        client = Client(reader, writer, self, handler)
        self.add(client)
        return client

clients = ClientManager()
