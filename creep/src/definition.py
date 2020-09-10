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
    def __init__(self, regex, filter, rename, modify, link):
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

    def apply(self, work, path, type, used):
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
                    os.rename(os.path.join(work, previous_path), os.path.join(work, path))

                self.logger.debug('File \'{0}\' renamed to \'{1}\'.'.format(path, name))

            if type == Action.ADD:
                # Apply link command if any
                if modifier.link is not None:
                    out = self.run(work, path, modifier.link)

                    if out is not None:
                        for link in out.decode('utf-8').splitlines():
                            self.logger.debug('File \'{0}\' is linked to file \'{1}\'.'.format(path, link))

                            actions.extend(self.apply(work, link, type, used))
                    else:
                        self.logger.warning('Command \'link\' on file \'{0}\' returned non-zero code.'.format(path))

                        type = Action.ERR

                # Build output file using processing command if any
                if modifier.modify is not None:
                    out = self.run(work, path, modifier.modify)

                    if out is not None:
                        with open(os.path.join(work, path), 'wb') as file:
                            file.write(out)
                    else:
                        self.logger.warning('Command \'modify\' on file \'{0}\' returned non-zero code.'.format(path))

                        type = Action.ERR

            # Apply filtering command if any
            if modifier.filter is not None and (modifier.filter == '' or self.run(work, path, modifier.filter) is None):
                self.logger.debug('File \'{0}\' filtered out.'.format(path))

                type = Action.NOP

            # Append action to list and return
            actions.append(Action(path, type))

            return actions

        # No modifier matched, return unmodified input
        return [Action(path, type)]

    def run(self, work, path, command):
        result = Process (command.replace ('{}', path)) \
         .set_directory (work) \
         .set_shell (True) \
         .execute ()

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

        modify = _get_or_fallback(logger, modifier_config, 'modify', 'adapt')
        filter = modifier_config.get('filter', None)
        link = modifier_config.get('link', None)
        rename = _get_or_fallback(logger, modifier_config, 'rename', 'name')
        regex = re.compile(pattern)

        modifiers.append(DefinitionModifier(regex, filter, rename, modify, link))

    # Append ignores specified in arguments
    for ignore in ignores:
        modifiers.append(DefinitionModifier(re.compile('^' + re.escape(ignore) + '$'), '', None, None, None))

    options = config.get('options', {})
    tracker = _get_or_fallback(logger, config, 'tracker', 'source')

    return Definition(logger, modifiers, options, tracker)
