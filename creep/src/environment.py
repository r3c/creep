#!/usr/bin/python3

import json


class EnvironmentLocation:
    def __init__(self, logger, location):
        subsidiaries = location.get('subsidiaries', None)

        if subsidiaries is not None:
            logger.warning('Deprecated property "subsidiaries" should be replaced by "cascades" in environment file.')

        cascades = location.get('cascades', subsidiaries or {})

        self.append_files = location.get('append_files', [])
        self.cascades = dict(((path, isinstance(name, list) and name or [name]) for path, name in cascades.items()))
        self.connection = location.get('connection', None)
        self.local = location.get('local', False)
        self.options = location.get('options', {})
        self.remove_files = location.get('remove_files', [])
        self.state = location.get('state', '.creep.rev')


class Environment:
    def __init__(self, logger, config):
        self.locations = dict(((name, EnvironmentLocation(logger, location)) for (name, location) in config.items()))

    def get_location(self, name):
        return self.locations.get(name, None)
