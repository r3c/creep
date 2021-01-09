#!/usr/bin/env python3

import os
import shutil


def duplicate(source, base, target):
    """
    Copy file and create parent directories if needed.
    source: path to source file
    base: base directory of target file (won't be created)
    target: path to target file relative to base directory (will be created)
    """

    if not os.path.isdir(base):
        return False

    destination = os.path.join(base, target)
    directory = os.path.dirname(destination)

    if not os.path.isdir(directory):
        os.makedirs(directory)

    shutil.copy(source, destination)

    return True


def explode(path):
    """
    Explode path into separate components.
    path: input path
    return: path components
    """

    names = []
    tail = '.'

    while tail != '':
        (path, tail) = os.path.split(path)

        if tail != '':
            names.insert(0, tail)
        elif path != '':
            names.insert(0, path)

    return names


def remove(base, target):
    """
    Remove file from given directory if exists.
    base: base directory of target file
    target: path to target file relative to base directory
    """

    remove = os.path.join(base, target)

    if not os.path.isfile(remove):
        return False

    os.remove(remove)

    return True
