#!/usr/bin/python3

from . import factory, path
from .action import Action
from .definition import Definition
from .environment import Environment
from .revision import Revision

import codecs
import json
import os
import shutil
import tempfile


def _read_json(base_path, json_or_path, default):
    # Input looks like a JSON object
    if json_or_path[0:1] == '{':
        contents = json_or_path
        file_name = None

    # Otherwise consider it as a file path
    else:
        file_name = json_or_path[0:1] == '@' and json_or_path[1:] or json_or_path
        file_path = os.path.join(base_path, file_name)

        if not os.path.isfile(file_path):
            return (default, None)

        reader = codecs.getreader('utf-8')

        with open(file_path, 'rb') as file:
            contents = reader(file).read()

    return (json.loads(contents), file_name)


class Deployer:
    def __init__(self, logger, definition, environment, yes):
        self.definition = definition
        self.environment = environment
        self.logger = logger
        self.yes = yes

    def deploy(self, base_path, names, append_files, remove_files, rev_from, rev_to):
        # Ensure base directory is valid
        if not os.path.isdir(base_path):
            self.logger.error('Base directory "{0}" doesn\'t exist.'.format(base_path))

            return False

        ignores = []

        # Load environment configuration from command line argument or file
        (environment_config, environment_name) = _read_json(base_path, self.environment, None)

        if environment_config is None:
            self.logger.error('Environment file "{0}" doesn\'t exist.'.format(file_path))

            return False

        if environment_name is not None:
            ignores.append(environment_name)

        environment = Environment(self.logger, environment_config)

        # Read definition configuration from command line argument or file
        (definition_config, definition_name) = _read_json(base_path, self.definition, {})

        if definition_name is not None:
            ignores.append(definition_name)

        definition = Definition(self.logger, definition_config, ignores)

        # Expand location names
        if len(names) < 1:
            names.append('default')
        elif len(names) == 1 and names[0] == '*':
            names = environment.locations.keys()

        # Deploy to target locations
        ok = True

        for name in names:
            location = environment.get_location(name)

            if location is None:
                self.logger.warning('There is no location "{0}" in your environment file.'.format(name))

                continue

            if location.connection is not None:
                self.logger.info('Deploying to location "{0}"...'.format(name))

                if not self.sync(base_path, definition, location, name, append_files, remove_files, rev_from, rev_to):
                    ok = False

                    continue

            for cascade_path, cascade_names in location.cascades.items():
                full_path = os.path.join(base_path, cascade_path)

                self.logger.info('Cascading to path "{0}"...'.format(full_path))
                self.logger.enter()

                ok = self.deploy(full_path, cascade_names, [], [], None, None) and ok

                self.logger.leave()

        return ok

    def prompt(self, question):
        if self.yes:
            return True

        self.logger.info(question)

        while True:
            answer = input()

            if answer == 'N' or answer == 'n':
                return False
            elif answer == 'Y' or answer == 'y':
                return True

            self.logger.warning('Invalid answer')

    def sync(self, base_path, definition, location, name, append_files, remove_files, rev_from, rev_to):
        # Build source repository reader from current directory and target from location connection string
        source = factory.create_source(self.logger, definition.source, definition.options, base_path)
        target = factory.create_target(self.logger, location.connection, location.options, base_path)

        if source is None or target is None:
            return False

        # Read revision file
        if not location.local:
            data = target.read(self.logger, location.state)
        elif os.path.exists(os.path.join(base_path, location.state)):
            data = open(os.path.join(base_path, location.state), 'rb').read()
        else:
            data = ''

        if data is None:
            self.logger.error(
                'Can\'t read revision file "{0}", check connection string and ensure parent directory exists.'.format(
                    location.state))

            return False

        try:
            revision = Revision(data)
        except Exception as e:
            self.logger.error('Can\'t parse revision from file "{0}": {1}.'.format(location.state, e))

            return False

        # Retrieve source and target revision
        if rev_from is None:
            rev_from = revision.get(name)

            if rev_from is None and not self.prompt(
                    'No current revision found, are you deploying for the first time? [Y/N]'):
                return True

        if rev_to is None:
            rev_to = source.current(base_path)

            if rev_to is None:
                self.logger.error(
                    'Can\'t find source version, please ensure your environment file is correctly defined.')

                return False

        revision.set(name, rev_to)

        # Prepare actions
        work_path = tempfile.mkdtemp()

        try:
            # Append actions from revision diff
            source_actions = source.diff(self.logger, base_path, work_path, rev_from, rev_to)

            if source_actions is None:
                return False

            # Append actions for manually specified files
            manual_actions = []

            for append in location.append_files + append_files:
                full_path = os.path.join(base_path, append)

                if os.path.isdir(full_path):
                    for (dirpath, dirnames, filenames) in os.walk(full_path):
                        parent_path = os.path.relpath(dirpath, base_path)

                        manual_actions.extend(
                            (Action(os.path.join(parent_path, filename), Action.ADD) for filename in filenames))
                elif os.path.isfile(full_path):
                    manual_actions.append(Action(append, Action.ADD))
                else:
                    self.logger.warning('Can\'t append missing file "{0}".'.format(append))

            for action in manual_actions:
                if not path.duplicate(os.path.join(base_path, action.path), work_path, action.path):
                    self.logger.warning('Can\'t copy file "{0}".'.format(action.path))

            for remove in location.remove_files + remove_files:
                full_path = os.path.join(base_path, remove)

                if os.path.isdir(full_path):
                    for (dirpath, dirnames, filenames) in os.walk(full_path):
                        parent_path = os.path.relpath(dirpath, base_path)

                        manual_actions.extend(
                            (Action(os.path.join(parent_path, filename), Action.DEL) for filename in filenames))
                else:
                    manual_actions.append(Action(remove, Action.DEL))

            # Apply pre-processing modifiers on actions
            actions = []
            used = set()

            for command in source_actions + manual_actions:
                actions.extend(definition.apply(work_path, command.path, command.type, used))

            # Update current revision (remote mode)
            if rev_from != rev_to and not location.local:
                with open(os.path.join(work_path, location.state), 'wb') as file:
                    file.write(revision.serialize().encode('utf-8'))

                actions.append(Action(location.state, Action.ADD))

            # Display processed actions using console target
            if len(actions) < 1:
                self.logger.info('No deployment required.')

                return True

            from .targets.console import ConsoleTarget

            console = ConsoleTarget()
            console.send(self.logger, work_path, actions)

            if not self.prompt('Deploy? [Y/N]'):
                return True

            # Execute processed actions after ordering them by precedence
            actions.sort(key=lambda action: (action.order(), action.path))

            if not target.send(self.logger, work_path, actions):
                return False

            # Update current revision (local mode)
            if location.local:
                with open(os.path.join(base_path, location.state), 'wb') as file:
                    file.write(revision.serialize().encode('utf-8'))

        finally:
            shutil.rmtree(work_path)

        self.logger.info('Deployment done.')

        return True


# Hack for Python 2 + 3 compatibility
try:
    input = raw_input
except NameError:
    pass
