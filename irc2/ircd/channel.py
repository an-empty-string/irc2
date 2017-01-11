# -*- coding: utf-8 -*-
import collections
import time

from . import utils
from .numerics import RPL_TOPIC, RPL_TOPICBY, RPL_NAMREPLY, RPL_ENDOFNAMES
from ..utils import join_max_length

class Channel(object):

    def __init__(self, name):
        self.name = name
        self.ts = time.time()
        self.topic = "haha yes look a topic"
        self.topic_set_at = time.time()
        self.topic_belongs_to = ""
        self.members = dict()
        self.modes = collections.defaultdict(lambda: None)

    def add(self, client):
        # update state
        client.data["channels"].add(self)
        self.members[client] = "" if self.members else "o"

        # send JOIN
        self.send(client.hostmask(), "JOIN", self.name)

        # send TOPIC
        if self.topic:
            client.send_numeric(RPL_TOPIC, self.name, self.topic)
            client.send_numeric(RPL_TOPICBY, self.name, self.topic_belongs_to, str(self.topic_set_at))

        # send NAMES
        names = [(utils.prefixes[value[0]] if value else "") + key.data["nickname"]
                 for key, value in
                 sorted(self.members.items(), key=lambda k: k[0].data["nickname"])]

        while names:
            cur, names = join_max_length(names, " ")
            client.send_numeric(RPL_NAMREPLY, "=", self.name, cur)
        client.send_numeric(RPL_ENDOFNAMES, self.name, "End of NAMES list.")

    def send(self, *data):
        for member in self.members:
            member.send(*data)

    def send_except(self, exc, *data):
        for member in self.members:
            if member != exc:
                member.send(*data)

class Channels(dict):

    def __missing__(self, key):
        self[key] = Channel(key)
        return self[key]

channels = Channels()
