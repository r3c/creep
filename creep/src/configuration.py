#!/usr/bin/env python3

import json
import os
import re
import shutil
import urllib.parse

from .action import Action
from .process import Process


class DefinitionModifier:
    def __init__(self, regex, rename, link, modify, chmod, filter):
        self.chmod = chmod
        self.filter = filter
        self.link = link
        self.modify = modify
        self.regex = regex
        self.rename = rename


class Definition:
    def __init__(self, logger, origin, environment, tracker, options, cascades, modifiers, where):
        self.cascades = cascades
        self.environment = environment
        self.logger = logger
        self.modifiers = modifiers
        self.options = options
        self.origin = origin
        self.tracker = tracker
        self.where = where

    def apply(self, base_directory, path, type, used):
        # Ensure we don't process a file already scanned
        path = os.path.normpath(path)

        if path in used:
            return []

        used.add(path)

        # Find modifier matching current file name if any
        name = os.path.basename(path)

        for modifier in self.modifiers:
            match = modifier.regex.search(name)

            if match is None:
                continue

            self.logger.debug('File \'{0}\' matches \'{1}\'.'.format(path, modifier.regex.pattern))

            actions = []

            # Apply renaming pattern if any
            if modifier.rename is not None:
                previous_path = path

                name = os.path.basename(re.sub('\\\\([0-9]+)', lambda m: match.group(int(m.group(1))), modifier.rename))
                path = _join_path(os.path.dirname(path), name)

                if type == Action.ADD:
                    # FIXME: must duplicate instead of rename so that references (e.g. links) won't break ; should be renamed at upload only instead
                    shutil.copyfile(_join_path(base_directory, previous_path), _join_path(base_directory, path))

                self.logger.debug('File \'{0}\' was renamed to \'{1}\'.'.format(previous_path, path))

            # Apply link command if any
            if modifier.link is not None and type == Action.ADD:
                self.logger.debug('Applying \'link\' command \'{1}\' on file \'{0}\'.'.format(path, modifier.modify))

                out = self.run(base_directory, path, modifier.link)

                if out is not None:
                    for link in out.decode('utf-8').splitlines():
                        self.logger.debug('File \'{0}\' was linked to file \'{1}\'.'.format(path, link))

                        actions.extend(self.apply(base_directory, link, type, used))
                else:
                    self.logger.warning('Command \'link\' on file \'{0}\' returned non-zero code.'.format(path))

                    type = Action.ERR

            # Build output file using processing command if any
            if modifier.modify is not None and type == Action.ADD:
                self.logger.debug('Applying \'modify\' command \'{1}\' on file \'{0}\'.'.format(path, modifier.modify))

                out = self.run(base_directory, path, modifier.modify)

                if out is not None:
                    with open(_join_path(base_directory, path), 'wb') as file:
                        file.write(out)
                else:
                    self.logger.warning('Command \'modify\' on file \'{0}\' returned non-zero code.'.format(path))

                    type = Action.ERR

            # Set file mode
            if modifier.chmod is not None and type == Action.ADD:
                os.chmod(_join_path(base_directory, path), modifier.chmod)

            # Apply filtering command if any
            if modifier.filter is not None:
                self.logger.debug('Applying \'filter\' command \'{1}\' on file \'{0}\'.'.format(path, modifier.filter))

                if modifier.filter == '' or self.run(base_directory, path, modifier.filter) is None:
                    self.logger.debug('File \'{0}\' was filtered out.'.format(path))

                    type = Action.NOP

            # Append action to list and return
            actions.append(Action(path, type))

            return actions

        # No modifier matched, return unmodified input
        return [Action(path, type)]

    def ignore(self, filename):
        regex = re.compile('^' + re.escape(filename) + '$')

        self.modifiers.append(DefinitionModifier(regex, None, None, None, 0o644, ''))

    def run(self, base_directory, path, command):
        result = Process(command.replace('{}', path)).set_directory(base_directory).set_shell(True).execute()

        if not result:
            self.logger.debug(result.err.decode('utf-8'))

            return None

        return result.out


class EnvironmentLocation:
    def __init__(self, append_files, connection, local, options, remove_files, state):
        self.append_files = append_files
        self.connection = connection
        self.local = local
        self.options = options
        self.remove_files = remove_files
        self.state = state


class Environment:
    def __init__(self, locations, where):
        self.locations = locations
        self.where = where

    def get_location(self, name):
        return self.locations.get(name, None)


def __get_or_fallback(logger, base_where, config, key, obsolete, default_value):
    if obsolete in config:
        logger.warning('Deprecated property "{0}" should be replaced by "{1}" in {2}'.format(obsolete, key, base_where))

        return config[obsolete]

    return config.get(key, default_value)


def _join_path(a, b):
    return os.path.normpath(os.path.join(a, b))


def __load_definition(logger, base_where, base_directory, object_or_path):
    ignores = []
    result = __read_object_or_path(logger, base_where, base_directory, object_or_path, '.creep.def', ignores)

    if result is None:
        return None

    directory, where, config = result

    # Read cascades from JSON configuration
    cascades_config = config.get('cascades', [])

    if not isinstance(cascades_config, list):
        logger.error('Property "cascades" must be an array in {0}'.format(where))

        return None

    cascades = [
        __load_definition(logger, where + '.cascades[' + str(index) + ']', directory, cascade_config)
        for index, cascade_config in enumerate(cascades_config)
    ]

    if None in cascades:
        return None

    # Read modifiers from JSON configuration
    modifiers_config = config.get('modifiers', [])

    if not isinstance(modifiers_config, list):
        logger.error('Property "modifiers" must be an array in {0}'.format(where))

        return None

    modifiers = [
        __load_modifier(logger, where + '.modifier[' + str(index) + ']', modifier_config)
        for index, modifier_config in enumerate(modifiers_config)
    ]

    if None in modifiers:
        return None

    # Read scalar properties from JSON configuration
    environment_config = config.get('environment', '.')
    environment = __load_environment(logger, where + '.environment', directory, environment_config, ignores)
    options = config.get('options', {})
    origin = __load_origin(logger, directory, config.get('origin', '.'))
    tracker = __get_or_fallback(logger, where, config, 'tracker', 'source', None)

    if environment is None:
        return None

    definition = Definition(logger, origin, environment, tracker, options, cascades, modifiers, where)

    for ignore in set((os.path.basename(ignore) for ignore in ignores)):
        definition.ignore(ignore)

    return definition


def __load_environment(logger, base_where, base_directory, object_or_path, ignores):
    result = __read_object_or_path(logger, base_where, base_directory, object_or_path, '.creep.env', ignores)

    if result is None:
        return None

    _, where, config = result

    locations = {
        name: __load_location(logger, where + '.' + name, location_config)
        for name, location_config in config.items()
    }

    if None in locations.values():
        return None

    return Environment(locations, where)


def __load_location(logger, where, config):
    if not isinstance(config, dict):
        logger.error('Value must be an object in {0}'.format(where))

        return None

    append_files = config.get('append_files', [])
    connection = config.get('connection', None)
    local = config.get('local', False)
    options = config.get('options', {})
    remove_files = config.get('remove_files', [])
    state = config.get('state', '.creep.rev')

    return EnvironmentLocation(append_files, connection, local, options, remove_files, state)


def __load_modifier(logger, where, config):
    pattern = config.get('pattern', None)

    if pattern is None:
        logger.error('Property "pattern" must be a string in {0}'.format(where))

        return None

    chmod_string = config.get('chmod', None)
    chmod = chmod_string is not None and int(chmod_string, 8) or None
    filter = config.get('filter', None)
    link = config.get('link', None)
    modify = __get_or_fallback(logger, where, config, 'modify', 'adapt', None)
    rename = __get_or_fallback(logger, where, config, 'rename', 'name', None)

    return DefinitionModifier(re.compile(pattern), rename, link, modify, chmod, filter)


def __load_origin(logger, base_directory, config):
    url = urllib.parse.urlparse(config)

    if url.scheme == '' or url.scheme == 'file':
        # Hack: force triple slash before path so urllib preserves them. This will produce a URL with pattern
        # "file:///something" where "something" can be an absolute (starting with /) or relative path. After parsing
        # the URL, removing leading slash from path will give us back the original value of "something".
        return url._replace(scheme='file', path='///' + _join_path(base_directory, url.path)).geturl()

    return config


def __read_object_or_path(logger, where, base_directory, object_or_path, default_filename, ignores):
    if isinstance(object_or_path, dict):
        return (base_directory, where, object_or_path)

    elif isinstance(object_or_path, str):
        config_path = _join_path(base_directory, object_or_path)

        if os.path.isdir(config_path):
            config_path = _join_path(config_path, default_filename)

        if os.path.isfile(config_path):
            ignores.append(config_path)

            with open(config_path, 'rb') as file:
                contents = file.read().decode('utf-8')

            root = json.loads(contents)
        else:
            root = {}

        return (os.path.dirname(config_path), config_path, root)

    else:
        logger.error('Value must be an object or string in {0}'.format(where))

        return None


def load(logger, base_directory, object_or_path):
    return __load_definition(logger, 'definition', base_directory, object_or_path)
