#!/usr/bin/python3

import json
import os
import re

from .action import Action
from .process import Process


class DefinitionModifier:
    def __init__(self, regex, filter, rename, modify, link):
        self.filter = filter
        self.link = link
        self.modify = modify
        self.regex = regex
        self.rename = rename


class Definition:
    def __init__(self, data, ignores):
        config = json.loads(data)
        modifiers = []

        # Read modifiers from JSON configuration
        for modifier in config.get('modifiers', []):
            modify = modifier.get('modify', modifier.get('adapt', None))
            filter = modifier.get('filter', None)
            link = modifier.get('link', None)
            pattern = modifier['pattern']
            rename = modifier.get('rename', modifier.get('name', None))

            regex = re.compile(pattern)

            modifiers.append(DefinitionModifier(regex, filter, rename, modify, link))

        # Append ignores specified in arguments
        for ignore in ignores:
            modifiers.append(DefinitionModifier(re.compile('^' + re.escape(ignore) + '$'), '', None, None, None))

        self.modifiers = modifiers
        self.options = config.get('options', {})
        self.source = config.get('source', None)

    def apply(self, logger, work, path, type, used):
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

            logger.debug('File \'{0}\' matches \'{1}\'.'.format(path, modifier.regex.pattern))

            actions = []

            # Apply renaming pattern if any
            if modifier.rename is not None:
                previous_path = path

                name = os.path.basename(re.sub('\\\\([0-9]+)', lambda m: match.group(int(m.group(1))), modifier.rename))
                path = os.path.normpath(os.path.join(os.path.dirname(path), name))

                if type == Action.ADD:
                    os.rename(os.path.join(work, previous_path), os.path.join(work, path))

                logger.debug('File \'{0}\' renamed to \'{1}\'.'.format(path, name))

            if type == Action.ADD:
                # Apply link command if any
                if modifier.link is not None:
                    out = self.run(work, path, modifier.link)

                    if out is not None:
                        for link in out.decode('utf-8').splitlines():
                            logger.debug('File \'{0}\' is linked to file \'{1}\'.'.format(path, link))

                            actions.extend(self.apply(logger, work, link, type, used))
                    else:
                        logger.warning('Command \'link\' on file \'{0}\' returned non-zero code.'.format(path))

                        type = Action.ERR

                # Build output file using processing command if any
                if modifier.modify is not None:
                    out = self.run(work, path, modifier.modify)

                    if out is not None:
                        with open(os.path.join(work, path), 'wb') as file:
                            file.write(out)
                    else:
                        logger.warning('Command \'modify\' on file \'{0}\' returned non-zero code.'.format(path))

                        type = Action.ERR

            # Apply filtering command if any
            if modifier.filter is not None and (modifier.filter == '' or self.run(work, path, modifier.filter) is None):
                logger.debug('File \'{0}\' filtered out.'.format(path))

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
