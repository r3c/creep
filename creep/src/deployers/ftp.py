#!/usr/bin/env python3

import ftplib
import io
import itertools
import os

from ..action import Action
from .. import path


class FTPDeployer:
    def __init__(self, logger, secure, host, port, user, password, directory, options):
        self.directory = directory
        self.host = host or 'localhost'
        self.logger = logger
        self.options = options
        self.port = port or 21
        self.password = password
        self.secure = secure
        self.user = user

    def connect(self):
        if self.secure:
            ftp = ftplib.FTP_TLS()
        else:
            ftp = ftplib.FTP()

        ftp.connect(self.host, self.port)

        try:
            if self.user is not None:
                ftp.login(self.user, self.password)

            if self.directory:
                ftp.cwd(self.directory)

            ftp.set_pasv(self.options.get('passive', True))
        except ftplib.all_errors as e:
            if e.args[0].startswith('530 '):
                self.logger.error('Can\'t authenticate as \'{0}\' on remote FTP: \'{1}\''.format(self.user, e))
            elif e.args[0].startswith('550 '):
                self.logger.error('Can\'t access folder \'{0}\' on remote FTP: \'{1}\''.format(self.directory, e))
            else:
                self.logger.error('Unknown FTP error: \'{0}\''.format(e))

            ftp.quit()

            return None

        return ftp

    def escape(self, path):
        return path  # FIXME: wrong escape [ftp-escape]

    def read(self, relative):
        ftp = self.connect()

        if ftp is None:
            return None

        with io.BytesIO() as buffer:
            try:
                ftp.retrbinary('RETR ' + self.escape(relative), buffer.write)

                return buffer.getvalue()

            except ftplib.all_errors as e:
                if e.args[0].startswith('550 '):  # no such file or directory
                    return ''

                self.logger.warning('Can\'t read file \'{0}\' from FTP remote: {1}'.format(relative, e))

                return None

            finally:
                ftp.quit()

    def send(self, work, actions):
        ftp = self.connect()

        if ftp is None:
            return None

        try:
            # Group actions by parent path
            commands = [(head, tail, type)
                        for ((head, tail), type) in ((os.path.split(action.path), action.type) for action in actions)]

            for (directory, files) in itertools.groupby(commands, lambda command: command[0]):
                # Must create directory before uploading files to it
                create = True
                names = path.explode(directory)

                # Append or delete files
                for (head, tail, type) in files:
                    target = self.escape(head and head + '/' + tail or tail)

                    if type == Action.ADD:
                        # Create missing parent directories
                        if create:
                            for parent in ('/'.join(names[0:n + 1]) for n in range(0, len(names))):
                                try:
                                    ftp.mkd(parent)
                                except ftplib.all_errors as e:
                                    if not e.args[0].startswith('550 '):
                                        raise e

                            create = False

                        # Upload current file
                        with open(os.path.join(work, head, tail), 'rb') as file:
                            ftp.storbinary('STOR ' + target, file)

                    elif type == Action.DEL:
                        # Delete file if exists
                        try:
                            ftp.delete(target)
                        except ftplib.all_errors as e:
                            if not e.args[0].startswith('550 '):
                                raise e

        except ftplib.all_errors as e:
            self.logger.error('Can\'t deploy to FTP remote: {0}'.format(e))

            return False

        finally:
            ftp.quit()

        return True
