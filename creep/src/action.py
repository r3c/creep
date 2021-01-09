#!/usr/bin/env python3


class Action:
    ADD = 1
    DEL = 2
    ERR = 3
    NOP = 4

    def __init__(self, path, type):
        self.path = path
        self.type = type

    def order(self):
        if self.type == Action.DEL:
            return 0
        elif self.type == Action.ADD:
            return 1
        elif self.type == Action.NOP:
            return 2
        else:
            return 3
