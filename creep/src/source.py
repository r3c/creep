import os
import shutil
import tempfile


class Source:
    """
    Source is a wrapper over the path deployment is initiated from. It could be a directory or an archive file whose
    contents is extracted automatically.
    """
    def __init__(self, path):
        self.directory = None
        self.path = path

    def __enter__(self):
        if os.path.isdir(self.path):
            self.directory = None

            return self.path

        elif os.path.isfile(self.path):
            self.directory = tempfile.TemporaryDirectory()

            try:
                name = self.directory.name

                shutil.unpack_archive(self.path, name)

                return name
            except:
                self.directory.cleanup()
                self.directory = None

                raise

        return None

    def __exit__(self, type, value, traceback):
        if self.directory is not None:
            self.directory.cleanup()
            self.directory = None
