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
    def __init__(self, definition, environment, locations, path):
        self.definition = definition
        self.environment = environment
        self.locations = locations
        self.path = path


class Environment:
    def __init__(self, locations):
        self.locations = locations

    def get_location(self, name):
        return self.locations.get(name, None)


def __load_location(logger, config, location_name):
    if not isinstance(config, dict):
        logger.error('Location must be an object in environment file, location "{0}".'.format(location_name))

        return None

    subsidiaries = config.get('subsidiaries', None)

    if subsidiaries is not None:
        logger.warning(
            'Deprecated property "subsidiaries" should be replaced by "cascades" in environment file, location "{0}".'.
            format(location_name))

    cascades_config = config.get('cascades', subsidiaries or [])

    if isinstance(cascades_config, dict):
        logger.warning(
            'Property "cascades" should be an array, not a object in environment file, location "{0}".'.format(
                location_name))

        cascades_config = [{
            'locations': isinstance(name, list) and name or [name],
            'path': path
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


def __load_target(logger, config, location_name):
    if isinstance(config, dict):
        path = config.get('path', None)

        if path is None:
            logger.error(
                'Missing property "path" in environment file, location "{0}", cascade definition'.format(location_name))

            return None

    elif isinstance(config, str):
        path = config
        config = {}

    else:
        logger.error(
            'Cascade definition must be either a string or an object in environment file, location "{0}"'.format(
                location_name))

        return None

    definition = config.get('definition', os.path.join(path, '.creep.def'))
    environment = config.get('environment', os.path.join(path, '.creep.env'))
    locations = config.get('locations', [location_name])

    return EnvironmentTarget(definition, environment, locations, path)


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
