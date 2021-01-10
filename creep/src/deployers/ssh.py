#!/usr/bin/env python3

import io
import os
import shlex
import tarfile
import tempfile

from ..action import Action
from ..process import Process


class SSHDeployer:
    def __init__(self, logger, host, port, user, directory, options):
        extra = shlex.split(options.get('extra', ''))
        remote = str((user or os.getusername()) + '@' + (host or 'localhost'))

        self.directory = directory
        self.logger = logger
        self.tunnel = ['ssh', '-T', '-p', str(port or 22)] + extra + [remote]

    def read(self, relative):
        base = shlex.quote(self.directory)
        path = shlex.quote(self.directory + '/' + relative)

        arguments = ['test', '-d', base, '&&', '(', 'test', '!', '-f', path, '||', 'cat', path, ')']
        result = self._remote_command(arguments).execute()

        if not result:
            self.logger.error(result.err.decode('utf-8'))
            self.logger.error('Couldn\'t read file \'{0}\' from SSH deployer.'.format(relative))

            return None

        return result.out

    def send(self, work, actions):
        with tempfile.TemporaryFile() as archive:
            to_add = False
            to_del = []

            # Append files to temporary TAR archive or deletion list
            with tarfile.open(fileobj=archive, mode='w') as tar:
                for action in actions:
                    if action.type == Action.ADD:
                        tar.add(os.path.join(work, action.path), action.path)

                        to_add = True
                    elif action.type == Action.DEL:
                        to_del.append(self.directory + '/' + action.path)

            archive.seek(0)

            # Send and delete files on remote host
            if to_add:
                arguments = ['tar', 'xC', shlex.quote(self.directory)]
                result = self._remote_command(arguments).set_input(archive.read()).execute()

                if not result:
                    self.logger.error(result.err.decode('utf-8'))
                    self.logger.error('Couldn\'t push files to SSH deployer.')

                    return False

            if len(to_del) > 0:
                commands = ';'.join(['rm -f \'' + shlex.quote(path) + '\'' for path in to_del])
                result = self._remote_command(['sh']).set_input(commands.encode('utf-8')).execute()

                if not result:
                    self.logger.error(result.err.decode('utf-8'))
                    self.logger.error('Couldn\'t delete files from SSH deployer.')

                    return False

        return True

    def _remote_command(self, arguments):
        command = ' '.join(arguments)

        return Process(self.tunnel + [command])
