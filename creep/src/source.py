import os
import shutil
import tempfile
import urllib.request

from logging import Logger
from urllib.parse import SplitResult


class Source:
    """
    Source is a wrapper over the path deployment is initiated from. This path can be:
    * A regular directory on file system
    * An archive file that will be extracted before deployment
    * An HTTP or HTTPS URL to an archive file
    Archive and URL formats also supports an optional sub-path within the archive e.g. "archive.zip#usr/bin/"
    """

    def __init__(self, logger: Logger, origin: SplitResult):
        self.cleaners = []
        self.logger = logger
        self.origin = origin

    def __enter__(self):
        # Locate path to file or directory on disk
        if self.origin.scheme == "" or self.origin.scheme == "file":
            head = self.origin.path
            tail = self.origin.fragment

        # Download archive from HTTP endpoint
        elif self.origin.scheme == "http" or self.origin.scheme == "https":
            # https://stackoverflow.com/questions/23212435/permission-denied-to-write-to-my-temporary-file
            head = os.path.join(
                tempfile.gettempdir(),
                os.urandom(24).hex() + "." + os.path.splitext(self.origin.path)[1],
            )
            tail = self.origin.fragment

            self.cleaners.append(lambda: os.remove(head))

            try:
                with urllib.request.urlopen(
                    self.origin._replace(fragment="").geturl()
                ) as input_file:
                    with open(head, "wb") as output_file:
                        output_file.write(input_file.read())
            except:
                self.__exit__(None, None, None)

                raise

        else:
            self.logger.error(
                'origin has unsupported scheme "{0}"'.format(self.origin.scheme)
            )

            self.__exit__(None, None, None)

            return None

        # Open origin directory
        if os.path.isdir(head):
            if tail != "":
                self.logger.error(
                    "no sub-path can be specified when origin is a directory"
                )
                self.__exit__(None, None, None)

                return None

            return head

        # ...or extract from archive
        elif os.path.isfile(head):
            directory = tempfile.TemporaryDirectory()

            self.cleaners.append(lambda: directory.cleanup())

            try:
                shutil.unpack_archive(head, directory.name)
            except:
                self.__exit__(None, None, None)

                raise

            return os.path.normpath(os.path.join(directory.name, tail))

        self.logger.error(
            'Origin path "{0}" is not a directory nor an archive file.'.format(head)
        )

        return None

    def __exit__(self, type, value, traceback):
        for cleaner in self.cleaners:
            cleaner()

        self.cleaners = []
