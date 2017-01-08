# -*- coding: utf-8 -*-
from .client import clients
from .handler import handler
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)


async def handle_incoming(reader, writer):
    client = clients.new(reader, writer, handler)
    while True:
        line = await reader.readline()
        if reader.at_eof() or client not in client.manager:
            logging.info("Client disconnected: {}".format(client.id))
            return client.done()

        else:
            handler.handle(client, line)


def main():
    loop = asyncio.get_event_loop()
    clients.loop = loop

    coro = asyncio.start_server(handle_incoming, "127.0.0.1", 6667)
    server = loop.run_until_complete(coro)
    loop.run_forever()

if __name__ == '__main__':
    main()
