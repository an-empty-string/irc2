# -*- coding: utf-8 -*-
import asyncio
from .client import clients

async def handle_incoming(reader, writer):
    client = clients.new(reader, writer)
    while True:
        line = await reader.readline()
        line = line.decode("utf-8").strip()
        if reader.at_eof():
            return client.done()
        else:
            clients.write_all("{}: {}\n".format(client.id, line).encode())

loop = asyncio.get_event_loop()
coro = asyncio.start_server(handle_incoming, "127.0.0.1", 8888)
server = loop.run_until_complete(coro)
loop.run_forever()
