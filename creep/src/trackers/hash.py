#!/usr/bin/env python3

import hashlib
import os

from ..action import Action
from .. import path


class HashTracker:
    def __init__(self, logger, options):
        self.algorithm = options.get('algorithm', 'md5')
        self.follow = options.get('follow', True)
        self.logger = logger

    def current(self, base_path):
        entries = {}

        for name in os.listdir(base_path):
            source = os.path.join(base_path, name)

            if not self.follow and os.path.islink(source):
                continue
            elif os.path.isdir(source):
                entry = self.current(source)
            elif os.path.isfile(source):
                entry = self.digest(source)
            else:
                continue

            entries[name] = entry

        return entries

    def diff(self, base_path, work_path, rev_from, rev_to):
        rev_from_or_empty = rev_from or {}
        rev_to_or_empty = rev_to or {}

        if not isinstance(rev_from_or_empty, dict):
            self.logger.error('Corrupted source revision "{0}".'.format(rev_from))

            return None

        actions = self.recurse(base_path, work_path, '.', rev_from_or_empty, rev_to_or_empty)

        self.logger.info('((fuchsia)){0}((default)) file(s) changed.'.format(len(actions)))

        return actions

    def digest(self, path):
        hash = hashlib.new(self.algorithm)

        with open(path, 'rb') as file:
            for chunk in iter(lambda: file.read(4096), b''):
                hash.update(chunk)

        return hash.hexdigest()

    def recurse(self, base_path, work_path, parent, entries_from, entries_to):
        actions = []

        for name in set(entries_from.keys()).union(entries_to.keys()):
            entry_from = entries_from.get(name, None)
            entry_to = entries_to.get(name, None)
            source = os.path.join(parent, name)

            # Path was a directory on previous version
            if isinstance(entry_from, dict):
                # Path is still a directory => compare recursively
                if isinstance(entry_to, dict):
                    actions.extend(self.recurse(base_path, work_path, source, entry_from, entry_to))

                # Path is no longer a directory
                else:
                    # Path is now a file => add
                    if entry_to is not None and path.duplicate(os.path.join(base_path, source), work_path, source):
                        actions.append(Action(source, Action.ADD))

                    # Recurse with no right hand side to delete contents
                    actions.extend(self.recurse(base_path, work_path, source, entry_from, {}))

            # Path wasn't a directory on previous version but now is
            elif isinstance(entry_to, dict):
                # Path was a file => delete
                if entry_from is not None and path.duplicate(os.path.join(base_path, source), work_path, source):
                    actions.append(Action(source, Action.DEL))

                # Recurse with no left hand side to add contents
                actions.extend(self.recurse(base_path, work_path, source, {}, entry_to))

            # Path wasn't and isn't a directory but changed
            elif entry_from != entry_to:
                # Path is now a file => add
                if entry_to is not None and path.duplicate(os.path.join(base_path, source), work_path, source):
                    actions.append(Action(source, Action.ADD))

                # Path no longer exists => delete
                else:
                    actions.append(Action(source, Action.DEL))

        return actions
