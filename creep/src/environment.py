#!/usr/bin/python3

import json
import os


class EnvironmentLocation:
    def __init__(self, append_files, cascades, connection, local, options, remove_files, state):
        self.append_files = append_files
        self.cascades = cascades
        self.connection = connection
        self.local = local
        self.options = options
        self.remove_files = remove_files
        self.state = state


class EnvironmentTarget:
    def __init__(self, definition, locations):
        self.definition = definition
        self.locations = locations


class Environment:
    def __init__(self, locations):
        self.locations = locations

    def get_location(self, name):
        return self.locations.get(name, None)


def __get_or_fallback(logger, source, key, obsolete, default_value):
    if obsolete in source:
        logger.warning('Deprecated property "{0}" should be replaced by "{1}" in environment file.'.format(
            obsolete, key))

        return source[obsolete]

    return source.get(key, default_value)


def __load_location(logger, config, location_name):
    if not isinstance(config, dict):
        logger.error('Location must be an object in environment file, location "{0}".'.format(location_name))

        return None

    cascades_config = __get_or_fallback(logger, config, 'cascades', 'subsidiaries', [])

    if isinstance(cascades_config, dict):
        logger.warning(
            'Property "cascades" should be an array, not a object in environment file, location "{0}".'.format(
                location_name))

        cascades_config = [{
            'definition': path,
            'locations': isinstance(name, list) and name or [name]
        } for path, name in cascades_config.items()]

    elif not isinstance(cascades_config, list):
        logger.error('Property "cascades" must be an array in environment file, location "{0}".'.format(location_name))

        return None

    cascades = [__load_target(logger, cascade_config, location_name) for cascade_config in cascades_config]

    if None in cascades:
        return None

    append_files = config.get('append_files', [])
    connection = config.get('connection', None)
    local = config.get('local', False)
    options = config.get('options', {})
    remove_files = config.get('remove_files', [])
    state = config.get('state', '.creep.rev')

    return EnvironmentLocation(append_files, cascades, connection, local, options, remove_files, state)


def __load_target(logger, config, default_location_name):
    if isinstance(config, dict):
        definition = __get_or_fallback(logger, config, 'definition', 'origin', None)

        if definition is None:
            logger.error(
                'Missing property "definition" in environment file, location "{0}", cascade declaration'.format(
                    default_location_name))

            return None

    elif isinstance(config, str):
        definition = config
        config = {}

    else:
        logger.error(
            'Cascade declaration must be either a string or an object in environment file, location "{0}"'.format(
                default_location_name))

        return None

    locations = config.get('locations', [default_location_name])

    return EnvironmentTarget(definition, locations)


def load(logger, config):
    if not isinstance(config, dict):
        logger.error('Environment file root must be an object.')

        return None

    locations = dict()

    for name, location_config in config.items():
        location = __load_location(logger, location_config, name)

        if location is None:
            return None

        locations[name] = location

    return Environment(locations)
