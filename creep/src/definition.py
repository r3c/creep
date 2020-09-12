#!/usr/bin/python3

import json
import os
import re

from .action import Action
from .process import Process


def _get_or_fallback(logger, source, key, obsolete):
    fallback = source.get(obsolete, None)

    if fallback is not None:
        logger.warning('Deprecated property "{0}" should be replaced by "{1}" in definition file.'.format(
            obsolete, key))

    return source.get(key, fallback)


class DefinitionModifier:
    def __init__(self, regex, rename, link, modify, chmod, filter):
        self.chmod = chmod
        self.filter = filter
        self.link = link
        self.modify = modify
        self.regex = regex
        self.rename = rename


class Definition:
    def __init__(self, logger, modifiers, options, trackers):
        self.logger = logger
        self.modifiers = modifiers
        self.options = options
        self.tracker = trackers

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
                path = os.path.normpath(os.path.join(os.path.dirname(path), name))

                if type == Action.ADD:
                    os.rename(os.path.join(base_directory, previous_path), os.path.join(base_directory, path))

                self.logger.debug('File \'{0}\' renamed to \'{1}\'.'.format(previous_path, path))

            # Apply link command if any
            if modifier.link is not None and type == Action.ADD:
                out = self.run(base_directory, path, modifier.link)

                if out is not None:
                    for link in out.decode('utf-8').splitlines():
                        self.logger.debug('File \'{0}\' is linked to file \'{1}\'.'.format(path, link))

                        actions.extend(self.apply(base_directory, link, type, used))
                else:
                    self.logger.warning('Command \'link\' on file \'{0}\' returned non-zero code.'.format(path))

                    type = Action.ERR

            # Build output file using processing command if any
            if modifier.modify is not None and type == Action.ADD:
                out = self.run(base_directory, path, modifier.modify)

                if out is not None:
                    with open(os.path.join(base_directory, path), 'wb') as file:
                        file.write(out)
                else:
                    self.logger.warning('Command \'modify\' on file \'{0}\' returned non-zero code.'.format(path))

                    type = Action.ERR

            # Set file mode
            os.chmod(os.path.join(base_directory, path), modifier.chmod)

            # Apply filtering command if any
            if modifier.filter is not None and (modifier.filter == '' or self.run(base_directory, path, modifier.filter) is None):
                self.logger.debug('File \'{0}\' filtered out.'.format(path))

                type = Action.NOP

            # Append action to list and return
            actions.append(Action(path, type))

            return actions

        # No modifier matched, return unmodified input
        return [Action(path, type)]

    def run(self, base_directory, path, command):
        result = Process(command.replace('{}', path)).set_directory(base_directory).set_shell(True).execute()

        if not result:
            return None

        return result.out


def load(logger, config, ignores):
    # Read modifiers from JSON configuration
    modifiers_config = config.get('modifiers', [])

    if not isinstance(modifiers_config, list):
        logger.error('Property "modifiers" must be an array in definition file.')

        return None

    modifiers = []

    for modifier_config in modifiers_config:
        pattern = modifier_config.get('pattern', None)

        if pattern is None:
            logger.error('Missing property "pattern" for modifier in definition file.')

            return None

        chmod = int(modifier_config.get('chmod', '0644'), 8)
        filter = modifier_config.get('filter', None)
        link = modifier_config.get('link', None)
        modify = _get_or_fallback(logger, modifier_config, 'modify', 'adapt')
        rename = _get_or_fallback(logger, modifier_config, 'rename', 'name')

        modifiers.append(DefinitionModifier(re.compile(pattern), rename, link, modify, chmod, filter))

    # Append ignores specified in arguments
    for ignore in ignores:
        modifiers.append(DefinitionModifier(re.compile('^' + re.escape(ignore) + '$'), None, None, None, None, ''))

    options = config.get('options', {})
    tracker = _get_or_fallback(logger, config, 'tracker', 'source')

    return Definition(logger, modifiers, options, tracker)
