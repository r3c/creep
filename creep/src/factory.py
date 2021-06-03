#!/usr/bin/env python3

from urllib.parse import unquote_plus
from . import path

import os
import re
import urllib


def _detect_tracker(directory):
    drive, tail = os.path.splitdrive(os.path.abspath(directory))
    names = path.explode(tail)

    # Detect '.git' file or directory in parent folders
    if any((os.path.exists(drive + os.path.join(*(names[0:n] + ['.git']))) for n in range(len(names), 0, -1))):
        return 'git'

    # Fallback to hash tracker by default
    return 'hash'


def _wrap_or_none(value, callback):
    if value is not None:
        return callback(value)

    return None


def create_deployer(logger, connection, options, base_path):
    # FIXME: should use urllib.parse [url-parse]
    match = re.match('([+0-9A-Za-z]+)://(?:([^#/:@]+)(?::([^#/@]+))?@)?(?:([^#/:]+)(?::([0-9]+))?)?(?:/([^#]*))?',
                     connection)

    if match is None:
        logger.error('Could not parse connection strings "{0}" as a URL.'.format(connection))

        return None

    directory = match.group(6) or '.'
    host = match.group(4)
    password = _wrap_or_none(match.group(3), unquote_plus)
    port = _wrap_or_none(match.group(5), int)
    scheme = match.group(1)
    user = _wrap_or_none(match.group(2), unquote_plus)

    if scheme == 'file':
        if password is not None or port is not None or user is not None:
            logger.warning('Connection string for "file" scheme shouldn\'t contain any port, user or password.')

        from .deployers.file import FileDeployer

        return FileDeployer(logger, os.path.join(base_path, directory))

    if scheme == 'ftp' or scheme == 'ftps':
        from .deployers.ftp import FTPDeployer

        return FTPDeployer(logger, scheme == 'ftps', host, port, user, password, directory, options)

    if scheme == 'ssh':
        if password is not None:
            logger.warning('Connection string for "ssh" scheme shouldn\'t contain any password.')

        from .deployers.ssh import SSHDeployer

        return SSHDeployer(logger, host, port, user, directory, options)

    # No known scheme recognized
    logger.error('Unsupported scheme in connection string "{0}".'.format(connection))

    return None


def create_tracker(logger, tracker, options, base_path):
    tracker = tracker or _detect_tracker(base_path)

    if tracker == 'delta' or tracker == 'hash':
        from .trackers.hash import HashTracker

        return HashTracker(logger, options)

    if tracker == 'git':
        from .trackers.git import GitTracker

        return GitTracker(logger)

    # No known tracker type recognized
    logger.error('Unsupported tracker type "{0}" in definition file.'.format(tracker))

    return None
