"""irc2 general utilities"""

import asyncio
import collections
import time

class IStr(str):
    """
    IStr is a string which follows RFC1459 casing rules, and allows for
    case-insensitive equality testing.

    >>> IStr("Hello World") == "HELLO world"
    True
    >>> IStr("Hello[] World~") == "hello{] WORLD^"
    True
    >>> IStr("Hello World") == "this is a completely different string"
    False
    """

    case_map = list(zip("[]\\~", "{}|^"))

    def lower(self):
        s = str.lower(self)
        for lo, up in IStr.case_map:
            s = s.replace(up, lo)
        return IStr(s)

    def upper(self):
        s = str.upper(self)
        for lo, up in IStr.case_map:
            s = s.replace(lo, up)
        return IStr(s)

    def __hash__(self):
        return hash(str(self.lower()))

    def __eq__(self, other):
        if not isinstance(other, IStr):
            other = IStr(other)

        return str(self.lower()) == str(other.lower())

class IDict(collections.MutableMapping):
    """
    IDict is a dict-like object with case-insensitive keys.

    >>> d = IDict(A=1, b=2, c=3)
    >>> "B" in d and d["B"] == d["b"]
    True
    >>> "a" in d and d["A"] == d["a"]
    True
    """
    def __init__(self, data={}, **more_data):
        self._data = dict()
        self.update(data)
        self.update(more_data)

    def __getitem__(self, key):
        key, value = self._data[IStr(key).lower()]
        return value

    def __setitem__(self, key, value):
        self._data[IStr(key).lower()] = key, value

    def __delitem__(self, key):
        del self._data[IStr(key).lower()]

    def __iter__(self):
        return (key for key, value in self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return "IDict({" + ", ".join(repr(key) + ": " + repr(value) for key, value in self._data.values()) + "})"

class IDefaultDict(IDict):
    """
    IDefaultDict is IDict but with collections.defaultdict functionality:

    >>> d = IDefaultDict(int)
    >>> d["A"] += 1
    >>> d["A"]
    1
    >>> d["a"]
    1
    """

    def __init__(self, default, data={}, **more_data):
        self.default = default
        super().__init__(data, **more_data)

    def __getitem__(self, key):
        if IStr(key).lower() not in self._data:
            self._data[IStr(key).lower()] = key, self.default()
        return super().__getitem__(key)

def join_max_length(l, sep, maxlen=400):
    """
    Join the items in l with sep such that the result is not longer than
    maxlen. Returns a tuple (result, remaining items).

    >>> join_max_length(["lorem", "ipsum", "dolor", "sit", "amet"], ":", 15)
    ('lorem:ipsum', ['dolor', 'sit', 'amet'])
    >>> join_max_length(["dolor", "sit", "amet"], ":", 15)
    ('dolor:sit:amet', [])
    """

    result = ""
    l = list(l)

    while l and len(result) + len(l[0]) < maxlen:
        result += (l.pop(0) + sep)
    return result[:-len(sep)], l

class TokenBucket(object):
    """
    Implements token-bucket rate limiting with the given bucket size ("fill")
    and replenishing time (t).
    """

    def __init__(self, fill, t):
        self._amount = fill
        self.last = time.time()

        self.fill = fill
        self.time = t

    def amount(self):
        """
        Get the current number of tokens in the bucket. Does not decrement the
        number of tokens (don't use this for rate-limiting).
        """
        old = self._amount
        self._amount = min(self._amount + ((time.time() - self.last) // self.time), self.fill)
        if old != self._amount:
            self.last = time.time()

        return self._amount

    def take(self):
        """
        Take a token from the bucket, if available. Returns True if successful,
        and False if not.
        """
        if self.amount():
            self._amount -= 1
            return True
        return False

    async def wait(self):
        """
        Asynchronously wait for a token to be available in the bucket, then
        take it. Will complete immediately if a token is already available.
        """
        if self.take():
            return True

        await asyncio.sleep(self.time - (time.time() - self.last))
        return self.take()

class AttrGetFollower(object):
    """
    AttrGetFollower takes getattr requests, keeps track of the path they
    create, and calls a callback when called. Best explained with an example:

    >>> def callback(path):
    ...     print("callback: {}".format(", ".join(path)))
    >>> follower = AttrGetFollower([], callback)
    >>> abcdef = follower.a.b.c.d.e.f
    >>> print(abcdef)
    AttrGetFollower(['a', 'b', 'c', 'd', 'e', 'f'])
    >>> abcdef()
    callback: a, b, c, d, e, f
    """

    def __init__(self, path, callback):
        self.path = path
        self.callback = callback

    def __repr__(self):
        return "AttrGetFollower({})".format(self.path)

    def __getattr__(self, attr):
        return AttrGetFollower(self.path + [attr], self.callback)

    def __call__(self, *args, **kwargs):
        self.callback(self.path, *args, **kwargs)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
