#!/usr/bin/env python3

from ..action import Action


class ConsoleDeployer:
    def __init__(self, logger):
        self.logger = logger

    def read(self, relative):
        raise Exception('can\'t read from console deployer')

    def send(self, work, actions):
        for action in actions:
            if action.type == action.ADD:
                prefix = '((lime))+'
            elif action.type == action.DEL:
                prefix = '((blue))-'
            elif action.type != action.NOP:
                prefix = '((red))!'
            else:
                continue

            self.logger.info(prefix + '((reset)) ' + action.path)

        return True
