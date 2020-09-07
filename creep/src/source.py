import os
import shutil
import tempfile


class Source:
    """
    Source is a wrapper over the path deployment is initiated from. This path can be either:
    * A regular directory on file system
    * An archive file that will be extracted before deployment
    Archive mode also supports an optional sub-path within the archive, e.g. "archive.zip:usr/bin/"
    """
    def __init__(self, path):
        self.directory = None
        self.path = path

    def __enter__(self):
        parts = self.path.split(':', 1)

        if os.path.isdir(parts[0]):
            self.directory = None

            return parts[0]

        elif os.path.isfile(parts[0]):
            self.directory = tempfile.TemporaryDirectory()

            try:
                name = self.directory.name

                shutil.unpack_archive(parts[0], name)

                return os.path.join(name, parts[1]) if len(parts) > 1 else name
            except:
                self.directory.cleanup()
                self.directory = None

                raise

        return None

    def __exit__(self, type, value, traceback):
        if self.directory is not None:
            self.directory.cleanup()
            self.directory = None
