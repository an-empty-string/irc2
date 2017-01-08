# -*- coding: utf-8 -*-
import collections

class Dispatcher(object):
    """
    Dispatcher maintains a list of functions and classes which should receive
    events (which are essentially just a (name, args) pair) and provides
    facilities to call all the functions associated with an event.
    """

    def __init__(self):
        self.handler_classes = []
        self.handlers = collections.defaultdict(list)

    def subscribe(self, event, handler):
        """
        Add a handler function for the given event. You can also use a
        decorator interface.

        >>> d = Dispatcher()
        >>> async def handler1(n):
        ...     print("handler1 {}".format(n))
        >>> d.subscribe("number", handler1)
        >>> @d.number
        ... async def handler2(n):
        ...    print("handler2 {}".format(n))
        >>> import asyncio
        >>> asyncio.get_event_loop().run_until_complete(d.fire("number", 5))
        handler1 5
        handler2 5
        """
        self.handlers[event].append(handler)

    def add_handler(self, obj):
        """
        Add a handler object. Handler objects should have methods with names
        like "on_event" (which will be called when "event" is fired).

        >>> class MyHandler:
        ...     @staticmethod
        ...     async def on_number(n):
        ...         print("myhandler {}".format(n))
        >>> d = Dispatcher()
        >>> d.add_handler(MyHandler)
        >>> import asyncio
        >>> asyncio.get_event_loop().run_until_complete(d.fire("number", 5))
        myhandler 5
        """
        self.handler_classes.append(obj)

    async def fire(self, event, *args):
        for handler in self.handlers[event]:
            await handler(*args)

        for handler_class in self.handler_classes:
            f = getattr(handler_class, "on_{}".format(event), None)
            if f is not None:
                await f(*args)

    def __getattr__(self, attr):
        def decorator(f):
            self.subscribe(attr, f)
            return f
        return decorator

if __name__ == '__main__':
    import doctest
    doctest.testmod()
