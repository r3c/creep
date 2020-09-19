#!/usr/bin/python3

from . import factory, path
from .action import Action
from .definition import load as load_definition
from .environment import load as load_environment
from .revision import Revision
from .source import Source

import json
import os
import shutil
import tempfile


def _join_path(a, b):
    return os.path.normpath(os.path.join(a, b))


def _read_json(base_directory, json_or_path, default_file_name, default_value):
    # Input looks like a JSON object
    if isinstance(json_or_path, dict):
        return (json_or_path, _join_path(base_directory, default_file_name), False)

    # Input looks like a JSON object serialized as a string
    if json_or_path[0:1] == '{' and json_or_path[-1:] == '}':
        return (json.loads(json_or_path), _join_path(base_directory, default_file_name), False)

    # Otherwise consider it as a file path
    file_path = _join_path(base_directory, json_or_path[0:1] == '@' and json_or_path[1:] or json_or_path)

    if os.path.isdir(file_path):
        file_path = _join_path(file_path, default_file_name)

    if not os.path.isfile(file_path):
        return (default_value, file_path, False)

    with open(file_path, 'rb') as file:
        contents = file.read().decode('utf-8')

        return (json.loads(contents), file_path, True)


class Application:
    def __init__(self, logger, yes):
        self.logger = logger
        self.yes = yes

    def run(self, base_directory, target, append_files, remove_files, rev_from, rev_to):
        # Read definition configuration from JSON or file
        (def_config, def_path, def_ignore) = _read_json(base_directory, target.definition, '.creep.def', {})

        definition = load_definition(self.logger, def_config)

        if definition is None:
            return False

        if def_ignore:
            definition.ignore(os.path.basename(def_path))

        def_directory = os.path.dirname(def_path)

        # Load environment configuration from JSON or file
        (env_config, env_path, env_ignore) = _read_json(def_directory, definition.environment, '.creep.env', None)

        if env_config is None:
            self.logger.error('Environment file "{0}" not found.'.format(env_path))

            return False

        environment = load_environment(self.logger, env_config)

        if environment is None:
            return False

        if env_ignore:
            definition.ignore(os.path.basename(env_path))

        # Compute origin path relative to definition file
        origin_path = _join_path(def_directory, definition.origin)

        with Source(origin_path) as source_path:
            # Ensure source directory is valid
            if source_path is None:
                self.logger.error('Origin path "{0}" doesn\'t exist.'.format(origin_path))

                return False

            # Expand location names
            if len(target.locations) < 1:
                location_names = ['default']
            elif len(target.locations) == 1 and target.locations[0] == '*':
                location_names = environment.locations.keys()
            else:
                location_names = target.locations

            # Deploy to selected locations
            ok = True

            for location_name in location_names:
                location = environment.get_location(location_name)

                if location is None:
                    self.logger.warning('Environment file "{0}" has no location "{0}".'.format(env_path, location_name))

                    continue

                if location.connection is not None:
                    self.logger.info('Deploying to location "{0}"...'.format(location_name))
                    if not self.__sync(source_path, definition, location, location_name, append_files, remove_files,
                                       rev_from, rev_to):
                        ok = False

                        continue

                for cascade in location.cascades:
                    self.logger.info('Cascading to definition "{0}"...'.format(cascade.definition))
                    self.logger.enter()

                    ok = self.run(source_path, cascade, [], [], None, None) and ok

                    self.logger.leave()

            return ok

    def __prompt(self, question):
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

    def __sync(self, source, definition, location, location_name, append_files, remove_files, rev_from, rev_to):
        # Build repository tracker from current directory and file deployer from location connection string
        deployer = factory.create_deployer(self.logger, location.connection, location.options, source)
        tracker = factory.create_tracker(self.logger, definition.tracker, definition.options, source)

        if deployer is None or tracker is None:
            return False

        # Read revision file
        if not location.local:
            data = deployer.read(self.logger, location.state)
        elif os.path.exists(_join_path(source, location.state)):
            data = open(_join_path(source, location.state), 'rb').read()
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
            rev_from = revision.get(location_name)

            if rev_from is None and not self.__prompt(
                    'No current revision found, are you deploying for the first time? [Y/N]'):
                return True

        if rev_to is None:
            rev_to = tracker.current(source)

            if rev_to is None:
                self.logger.error(
                    'Can\'t find source version, please ensure your environment file is correctly defined.')

                return False

        revision.set(location_name, rev_to)

        # Prepare actions
        work_path = tempfile.mkdtemp()

        try:
            # Append actions from revision diff
            tracker_actions = tracker.diff(self.logger, source, work_path, rev_from, rev_to)

            if tracker_actions is None:
                return False

            # Append actions for manually specified files
            manual_actions = []

            for append in location.append_files + append_files:
                full_path = _join_path(source, append)

                if os.path.isdir(full_path):
                    for (dirpath, dirnames, filenames) in os.walk(full_path):
                        parent_path = os.path.relpath(dirpath, source)

                        manual_actions.extend(
                            (Action(_join_path(parent_path, filename), Action.ADD) for filename in filenames))
                elif os.path.isfile(full_path):
                    manual_actions.append(Action(append, Action.ADD))
                else:
                    self.logger.warning('Can\'t append missing file "{0}".'.format(append))

            for action in manual_actions:
                if not path.duplicate(_join_path(source, action.path), work_path, action.path):
                    self.logger.warning('Can\'t copy file "{0}".'.format(action.path))

            for remove in location.remove_files + remove_files:
                full_path = _join_path(source, remove)

                if os.path.isdir(full_path):
                    for (dirpath, dirnames, filenames) in os.walk(full_path):
                        parent_path = os.path.relpath(dirpath, source)

                        manual_actions.extend(
                            (Action(_join_path(parent_path, filename), Action.DEL) for filename in filenames))
                else:
                    manual_actions.append(Action(remove, Action.DEL))

            # Apply pre-processing modifiers on actions
            actions = []
            used = set()

            for command in tracker_actions + manual_actions:
                actions.extend(definition.apply(work_path, command.path, command.type, used))

            # Update current revision (remote mode)
            if rev_from != rev_to and not location.local:
                with open(_join_path(work_path, location.state), 'wb') as file:
                    file.write(revision.serialize().encode('utf-8'))

                actions.append(Action(location.state, Action.ADD))

            # Display processed actions using console deployer
            if len(actions) < 1:
                self.logger.info('No deployment required.')

                return True

            from .deployers.console import ConsoleDeployer

            console = ConsoleDeployer()
            console.send(self.logger, work_path, actions)

            if not self.__prompt('Deploy? [Y/N]'):
                return True

            # Execute processed actions after ordering them by precedence
            actions.sort(key=lambda action: (action.order(), action.path))

            if not deployer.send(self.logger, work_path, actions):
                return False

            # Update current revision (local mode)
            if location.local:
                with open(_join_path(source, location.state), 'wb') as file:
                    file.write(revision.serialize().encode('utf-8'))

        finally:
            shutil.rmtree(work_path)

        self.logger.info('Deployment done.')

        return True
