# -*- coding: utf-8 -*-
"""irc2 parser"""

from .utils import IStr


class Prefix(object):
    """
    Prefix represents a source of an IRC message, usually a hostmask.

    Instance variables:
        prefix      The complete prefix.
        nick        A nickname, or None.
        ident       An ident/username, or None.
        host        A hostname, or None.
    """

    def __init__(self, prefix):
        self.prefix = prefix
        self._parse()

    def _parse(self):
        if "!" not in self.prefix or "@" not in self.prefix:
            return
        self.nick, rest = self.prefix.split("!", maxsplit=1)
        self.user, self.host = rest.split("@", maxsplit=1)

        self.nick = IStr(self.nick)
        self.user = IStr(self.user)
        self.host = IStr(self.host)

    def __repr__(self):
        return "Prefix({})".format(repr(self.prefix))


class Message(object):
    """
    Message represents a complete or partial IRC message.

    Instance variables:
        tags        A dict of IRCv3 message tags. Can be empty if there are no tags.
        prefix      The source of this message. Is either None or a Prefix object.
        verb        The command used, like PING, PRIVMSG, or JOIN.
        args        Any additional arguments to the command.
    """

    def __init__(self, tags={}, prefix=None, verb=None, args=[]):
        self.tags = tags
        self.prefix = prefix
        self.verb = verb
        self.args = args

        if self.prefix is not None and not isinstance(self.prefix, Prefix):
            self.prefix = Prefix(self.prefix)

    def __repr__(self):
        return "Message(tags={}, prefix={}, verb={}, args={})".format(self.tags, self.prefix, self.verb, self.args)

    @staticmethod
    def _matches(pat, test):
        if pat is None:
            return True
        elif isinstance(pat, list) or isinstance(pat, set):
            for i in pat:
                if test == i:
                    return True
        else:
            if test == pat:
                return True
        return False

    def matches(self, test):
        """
        Test another IRC message to see if it matches the pattern represented by
        this one. The rules for a successful match are:

        - Each tag in the pattern must exist and have the same value as the
          corresponding tag in the message.
        - Each argument in the pattern must be equal to the argument with the
          same index in the message.
        - The prefix and verb must be equal.

        "None" in the pattern is always successfully matched against. A list of
        items in the pattern will be successfully matched against by any item
        in the list. So:

        >>> Message(verb=["PRIVMSG", "NOTICE"]).matches(Message(verb="PRIVMSG"))
        True
        >>> Message(verb=None, args=[None]).matches(Message(verb="PRIVMSG", args=["##fwilson", "hi"]))
        True

        However:

        >>> Message(args=[None, None, None]).matches(Message(verb="PRIVMSG", args=["##fwilson", "hi"]))
        False

        ...since there are not enough arguments in the message to match against.
        """
        for tag in self.tags:
            if tag not in test.tags:
                return False
            if not self._matches(self.tags[tag], test.tags[tag]):
                return False

        if len(self.args) > len(test.args):
            return False

        for idx, arg in enumerate(self.args):
            if not self._matches(arg, test.args[idx]):
                return False

        return self._matches(self.prefix, test.prefix) and self._matches(self.verb, test.verb)


def parse_tags(tagstr):
    """
    Parse a series of IRCv3 tags in the format:

        @key1=value1;key2;key3=value3

    Returns a dict of keys to values. If there is no value for a key, but the
    key is specified, its value will be True.

    >>> parse_tags("@key1=value1;key2;key3=value3") == \
            {'key1': 'value1', 'key2': True, 'key3': 'value3'}
    True
    """

    tags = {}
    tagstrs = tagstr[1:].split(";")
    for tagstr in tagstrs:
        if "=" in tagstr:
            key, value = tagstr.split("=", maxsplit=1)
            tags[IStr(key)] = IStr(value)
        else:
            tags[IStr(tagstr)] = True

    return tags


def parse_line(line):
    """
    Parse an IRC message from a bytestring into a Message object.

    >>> parse_line(b":irc.fwilson.me NOTICE #hello :hello from the server")
    Message(tags={}, prefix=Prefix('irc.fwilson.me'), verb=NOTICE, args=['#hello', 'hello from the server'])
    >>> parse_line(b"HELP")
    Message(tags={}, prefix=None, verb=HELP, args=[])
    """

    try:
        if isinstance(line, bytes):
            line = line.decode('utf-8')
        line = line.strip()

        tags = {}
        prefix = None

        if line.startswith("@"):
            tags, line = line.split(" ", maxsplit=1)
            tags = parse_tags(tags)

        if line.startswith(":"):
            prefix, line = line.split(" ", maxsplit=1)
            prefix = Prefix(prefix[1:])

        verb_and_rest = line.split(" ", maxsplit=1)
        verb, line = verb_and_rest[0], ""
        if len(verb_and_rest) > 1:
            verb, line = verb_and_rest

        verb = IStr(verb)

        if line.startswith(":"):
            args = [line[1:]]
        elif " :" not in line:
            args = line.split()
        else:
            args, lastarg = line.split(" :", maxsplit=1)
            args = args.split(" ") if args else []
            args.append(lastarg)

        args = [IStr(arg) for arg in args]

        return Message(tags, prefix, verb, args)
    except:
        return None


if __name__ == '__main__':
    import doctest
    doctest.testmod()
