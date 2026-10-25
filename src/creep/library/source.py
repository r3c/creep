import os
import shutil
import tempfile
import urllib.request

from urllib.parse import SplitResult


class Source:
    """
    Source is a wrapper over the path deployment is initiated from. This path can be:
    * A regular directory on file system
    * An archive file that will be extracted before deployment
    * An HTTP or HTTPS URL to an archive file
    Archive and URL formats also supports an optional sub-path within the archive e.g. "archive.zip#usr/bin/"
    """

    def __init__(self, logger, origin: SplitResult):
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
                # Format must be specified to `shutil.unpack_archive` for `filter` to be taken into account
                # https://github.com/python/cpython/issues/112760
                if head.endswith((".tar.gz", ".tgz")):
                    filter = "data"
                    format = "gztar"
                elif head.endswith((".tar.bz2", ".tbz2")):
                    filter = "data"
                    format = "bztar"
                elif head.endswith((".tar.xz", ".txz")):
                    filter = "data"
                    format = "xztar"
                elif head.endswith((".tar")):
                    filter = "data"
                    format = "tar"
                elif head.endswith((".zip")):
                    filter = None
                    format = "zip"
                else:
                    filter = None
                    format = None

                if format is not None:
                    shutil.unpack_archive(
                        head, directory.name, format=format, filter=filter
                    )

                    return os.path.normpath(os.path.join(directory.name, tail))
            except:
                self.__exit__(None, None, None)

                raise

        self.logger.error(
            'Origin path "{0}" is not a directory nor a supported archive file.'.format(
                head
            )
        )

        return None

    def __exit__(self, type, value, traceback):
        for cleaner in self.cleaners:
            cleaner()

        self.cleaners = []
