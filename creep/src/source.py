import os
import shutil
import tempfile
import urllib.parse
import urllib.request


class Source:
    """
    Source is a wrapper over the path deployment is initiated from. This path can be:
    * A regular directory on file system
    * An archive file that will be extracted before deployment
    * An HTTP or HTTPS URL to an archive file
    Archive and URL formats also supports an optional sub-path within the archive e.g. "archive.zip#usr/bin/"
    """
    def __init__(self, logger, path):
        self.cleaners = []
        self.logger = logger
        self.path = path

    def __enter__(self):
        result = urllib.parse.urlparse(self.path)

        # Locate path to file or directory on disk
        if result.scheme == 'file':
            # Hack: remove leading "/" to restore original path (see function `__load_origin`)
            origin = result.path[1:]
            scope = result.fragment

        # Download archive from HTTP endpoint
        elif result.scheme == 'http' or result.scheme == 'https':
            # https://stackoverflow.com/questions/23212435/permission-denied-to-write-to-my-temporary-file
            origin = os.path.join(tempfile.gettempdir(), os.urandom(24).hex() + '.' + os.path.splitext(result.path)[1])
            scope = result.fragment

            self.cleaners.append(lambda: os.remove(origin))

            try:
                with urllib.request.urlopen(result._replace(fragment='').geturl()) as input_file:
                    with open(origin, 'wb') as output_file:
                        output_file.write(input_file.read())
            except:
                self.__exit__(None, None, None)

                raise

        else:
            self.logger.error('origin has unsupported scheme "{0}"'.format(result.scheme))
            self.__exit__(None, None, None)

        # Open origin directory
        if os.path.isdir(origin):
            if scope != '':
                self.logger.error('no sub-path can be specified when origin is a directory')
                self.__exit__(None, None, None)

                return None

            return origin

        # ...or extract from archive
        elif os.path.isfile(origin):
            directory = tempfile.TemporaryDirectory()

            self.cleaners.append(lambda: directory.cleanup())

            try:
                shutil.unpack_archive(origin, directory.name)
            except:
                self.__exit__(None, None, None)

                raise

            return os.path.normpath(os.path.join(directory.name, scope))

        self.logger.error('Origin path "{0}" is not a directory nor an archive file.'.format(origin))

        return None

    def __exit__(self, type, value, traceback):
        for cleaner in self.cleaners:
            cleaner()

        self.cleaners = []
