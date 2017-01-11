# -*- coding: utf-8 -*-
from .handler import handler
from .numerics import RPL_WELCOME, RPL_YOURHOST, RPL_ISUPPORT, RPL_MOTDSTART, RPL_MOTD, RPL_ENDOFMOTD
import re

# list, with parameter, none req on removal, no parameter
usermodes = ("", "", "", "iw")
chanmodes = ("be", "o", "flj", "istmn")

prefixes = {"o": "@", "v": "+"}
nickres = "^[a-zA-Z][a-zA-Z0-9]{0,14}$"
nickre = re.compile(nickres)

def valid_nick(nick):
    return bool(nickre.match(nick))

def send_welcome(client):
    client.send_numeric(RPL_WELCOME, "Welcome to IRC")
    client.send_numeric(RPL_YOURHOST, "Your host is {}, running irc2.ircd".format(handler.config["name"]))
    client.send_numeric(RPL_ISUPPORT, "NOTHING", "is supported by this server")
    send_motd(client)

def send_motd(client):
    client.send_numeric(RPL_MOTDSTART, "MOTD is:")
    client.send_numeric(RPL_MOTD, handler.config["motd"])
    client.send_numeric(RPL_ENDOFMOTD, "End of MOTD")

def parse_mode(mode, kinds):
    at, bt, ct, dt = kinds
    # A-type: edit a list
    # B-type: setting w/ parameter
    # C-type: setting w/ parameter on addition, not removal
    # D-type: setting no parameter

    data = mode.split(maxsplit=1)
    args = ""
    if len(data) > 1:
        args = data[1]
    args = args.split()

    cstr = "+"
    result = ([], [])  # adding, removing
    for char in mode:
        if char == "+" or char == "-":
            cstr = char
        elif cstr == "+" and (char in at or char in bt or char in ct):
            if not args:
                return False, ("Not enough arguments to add mode {}".format(char))
            result[0].append((char, args.pop(0)))
        elif cstr == "+" and char in dt:
            result[0].append(char)
        elif cstr == "-" and (char in at or char in bt):
            if not args:
                return False, ("Not enough arguments to remove mode {}".format(char))
            result[1].append((char, args.pop(0)))
        elif cstr == "-" and (char in ct or char in dt):
            result[1].append(char)
        else:
            return False, ("{} is unknown mode".format(char))

    return True, result
