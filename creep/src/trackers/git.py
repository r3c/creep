#!/usr/bin/env python3

from ..action import Action
from ..process import Process

import os
import tempfile


class GitTracker:
    def __init__(self, logger):
        self.logger = logger

    def current(self, base_path):
        revision = Process (['git', 'rev-parse', '--quiet', '--verify', 'HEAD']) \
         .set_directory (base_path) \
         .execute ()

        if revision:
            return revision.out.decode('utf-8').strip()

        return None

    def diff(self, base_path, work_path, rev_from, rev_to):
        # Parse and validate source and target revisions
        if rev_from is None or rev_from == '':
            process = Process(['git', 'hash-object', '-t', 'tree', '/dev/null'])
        elif isinstance(rev_from, str):
            process = Process(['git', 'rev-parse', '--quiet', '--verify', rev_from])
        else:
            self.logger.error('Corrupted source revision "{0}" (must be a valid Git hash).'.format(rev_from))

            return None

        res_from = process.set_directory(base_path).execute()

        if not res_from:
            self.logger.error(res_from.err.decode('utf-8'))
            self.logger.error('Unknown source revision "{0}" (must be a valid Git tree-ish).'.format(rev_from))

            return None

        res_to = Process(['git', 'rev-parse', '--quiet', '--verify', rev_to]).set_directory(base_path).execute()

        if not res_to:
            self.logger.error(res_to.err.decode('utf-8'))
            self.logger.error('Unknown target revision "{0}" (must be a valid Git tree-ish).'.format(rev_to))

            return None

        hash_from = res_from.out.decode('utf-8').strip()
        hash_to = res_to.out.decode('utf-8').strip()

        # Display update information
        if hash_from != hash_to:
            f = hash_from[0:8]
            t = hash_to[0:8]

            self.logger.info('Update from revision ((fuchsia)){0}((default)) to ((fuchsia)){1}((default)).'.format(
                f, t))
        else:
            self.logger.info('Already at revision ((fuchsia)){0}((default)).'.format(hash_from[0:8]))

            return []

        # Populate work directory from Git archive
        (temp_file, temp_path) = tempfile.mkstemp()

        try:
            os.close(temp_file)

            archive_args = ['git', 'archive', '--output', temp_path, hash_to, '.']
            archive = Process(archive_args).set_directory(base_path).execute()

            if not archive:
                self.logger.error(archive.err.decode('utf-8'))
                self.logger.error('Couldn\'t export archive from Git.')

                return None

            extract = Process(['tar', 'xf', temp_path]).set_directory(work_path).execute()

            if not extract:
                self.logger.error(extract.err.decode('utf-8'))
                self.logger.error('Couldn\'t extract Git archive to temporary directory.')

                return None
        finally:
            os.remove(temp_path)

        # Build actions from Git diff output
        diff_args = ['git', 'diff', '--name-status', '--relative', hash_from, hash_to]
        diff = Process(diff_args).set_directory(base_path).execute()

        if not diff:
            self.logger.error(diff.err.decode('utf-8'))
            self.logger.error('Couldn\'t get diff from Git.')

            return None

        actions = []

        for line in diff.out.decode('utf-8').splitlines():
            (mode, path) = line.split('\t', 1)

            if mode == 'A' or mode == 'M':
                actions.append(Action(path, Action.ADD))
            elif mode == 'D':
                actions.append(Action(path, Action.DEL))
            elif mode.startswith('R'):
                (path_del, path_add) = path.split('\t', 1)

                actions.append(Action(path_add, Action.ADD))
                actions.append(Action(path_del, Action.DEL))

        return actions
