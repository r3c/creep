#!/usr/bin/env python3

from . import factory, path
from .action import Action
from .revision import Revision
from .source import Source

import json
import os
import shutil
import tempfile


def _join_path(a, b):
    return os.path.normpath(os.path.join(a, b))


class Application:
    def __init__(self, logger, yes):
        self.logger = logger
        self.yes = yes

    def run(self, definition, location_names, append_files, remove_files, rev_from, rev_to):
        # Compute origin path relative to definition file
        with Source(self.logger, definition.origin) as path:
            if path is None:
                return False

            # Expand location names
            if len(location_names) < 1:
                location_names = ['default']
            elif len(location_names) == 1 and location_names[0] == '*':
                location_names = definition.environment.locations.keys()

            # Search for undefined locations
            locations = [(name, definition.environment.locations.get(name, None)) for name in location_names]
            names = list(map(lambda i: i[0], filter(lambda item: item[1] is None, locations)))

            if len(names) > 0:
                self.logger.error('Location(s) missing from {environment}: {names}.'.format(
                    environment=definition.environment.path, names=', '.join(names)))

                return False

            # Deploy to selected locations
            for name, location in locations:
                if location.connection is None:
                    continue

                self.logger.info('Deploying to location "{0}"...'.format(name))

                success = self.__sync(path, definition, location, name, append_files, remove_files, rev_from, rev_to)

                if not success:
                    return False

            # Trigger cascaded definitions
            for cascade in definition.cascades:
                self.logger.info('Cascading to "{0}"...'.format(cascade.path))
                self.logger.enter()

                success = self.run(cascade, location_names, [], [], None, None)

                self.logger.leave()

                if not success:
                    return False

        return True

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

        self.logger.debug('Compare changes with "{tracker}" and deploy with "{deployer}"'.format(
            deployer=type(deployer).__name__, tracker=type(tracker).__name__))

        # Read revision file
        location_state_path = os.path.join(source, location.state)

        if not location.local:
            data = deployer.read(location.state)
        elif os.path.exists(location_state_path):
            data = open(location_state_path, 'rb').read()
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
            tracker_actions = tracker.diff(source, work_path, rev_from, rev_to)

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

            console = ConsoleDeployer(self.logger)
            console.send(work_path, actions)

            if not self.__prompt('Deploy? [Y/N]'):
                return True

            # Execute processed actions after ordering them by precedence
            actions.sort(key=lambda action: (action.order(), action.path))

            if not deployer.send(work_path, actions):
                return False

            # Update current revision (local mode)
            if location.local:
                with open(_join_path(source, location.state), 'wb') as file:
                    file.write(revision.serialize().encode('utf-8'))

        finally:
            shutil.rmtree(work_path)

        self.logger.info('Deployment done.')

        return True
