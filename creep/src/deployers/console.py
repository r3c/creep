#!/usr/bin/python3

from ..action import Action


class ConsoleDeployer:
    def read(self, logger, relative):
        raise Exception('can\'t read from console deployer')

    def send(self, logger, work, actions):
        for action in actions:
            if action.type == action.ADD:
                prefix = '((lime))+'
            elif action.type == action.DEL:
                prefix = '((blue))-'
            elif action.type != action.NOP:
                prefix = '((red))!'
            else:
                continue

            logger.info(prefix + '((reset)) ' + action.path)

        return True
