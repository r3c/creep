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
    def __init__(self, base_directory, relative_path):
        self.base_directory = base_directory
        self.cleaners = []
        self.relative_path = relative_path

    def __enter__(self):
        result = urllib.parse.urlparse(self.relative_path)

        # Locate path on disk or download source
        if result.scheme == '' or result.scheme == 'file':
            origin = os.path.join(self.base_directory, result.path)
            scope = result.fragment

        elif result.scheme == 'http' or result.scheme == 'https':
            download = tempfile.NamedTemporaryFile(suffix=os.path.splitext(result.path)[1])

            self.cleaners.append(lambda: download.close())

            origin = download.name
            scope = result.fragment

            try:
                with urllib.request.urlopen(result._replace(fragment='').geturl()) as file:
                    download.write(file.read())
            except:
                self.__exit__(None, None, None)

                raise

            download.seek(0)

        else:
            self.__exit__(None, None, None)

            raise ValueError('origin has unsupported scheme "{0}"'.format(result.scheme))

        # Extract archive or open directory
        if os.path.isdir(origin):
            if scope != '':
                self.__exit__(None, None, None)

                raise ValueError('no sub-path can be specified when origin is a directory')

            return origin

        elif os.path.isfile(origin):
            directory = tempfile.TemporaryDirectory()

            self.cleaners.append(lambda: directory.cleanup())

            try:
                shutil.unpack_archive(origin, directory.name)
            except:
                self.__exit__(None, None, None)

                raise

            return os.path.normpath(os.path.join(directory.name, scope))

        return None

    def __exit__(self, type, value, traceback):
        for cleaner in self.cleaners:
            cleaner()

        self.cleaners = []
