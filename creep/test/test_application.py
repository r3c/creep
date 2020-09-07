#!/usr/bin/python3

import io
import logging
import os
import sys
import tarfile
import tempfile
import unittest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src import Application, Logger


class ApplicationTester(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.directory.cleanup()

    def assert_file(self, name, expected=None):
        path = os.path.join(self.directory.name, name)

        if expected is not None:
            self.assertTrue(os.path.exists(path))

            with open(path, 'rb') as file:
                data = file.read()

            self.assertEqual(data, expected)
        else:
            self.assertFalse(os.path.exists(path))

    def create_directory(self, name):
        path = os.path.join(self.directory.name, name)

        os.makedirs(path, exist_ok=True)

        return path

    def create_file(self, name, data):
        path = os.path.join(self.directory.name, name)

        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, 'wb') as file:
            file.write(data)

        return path

    def delete_file(self, name):
        path = os.path.join(self.directory.name, name)

        if os.path.exists(path):
            os.remove(path)

    def deploy(self, source_path, locations, definition=None, environment=None):
        source_path = os.path.join(self.directory.name, source_path)
        definition = os.path.join(source_path, '.creep.def') if definition is None else definition
        environment = os.path.join(source_path, '.creep.env') if environment is None else environment

        application = Application(Logger.build(logging.WARNING), definition, environment, True)

        self.assertTrue(application.run(source_path, locations, [], [], None, None))

    def test_config_definition_file(self):
        self.create_directory('target')
        self.create_file('source/.creep.def', b'{"modifiers": [{"pattern": "^bbb$", "filter": ""}]}')
        self.create_file('source/.creep.env', b'{"default": {"connection": "file:///../target"}}')
        self.create_file('source/aaa', b'a')
        self.create_file('source/bbb', b'b')

        self.deploy('source', ['default'])

        self.assert_file('target/aaa', b'a')
        self.assert_file('target/bbb')

    def test_config_definition_inline(self):
        self.create_directory('target')
        self.create_file('source/.creep.env', b'{"default": {"connection": "file:///../target"}}')
        self.create_file('source/aaa', b'a')
        self.create_file('source/bbb', b'b')

        self.deploy('source', ['default'], definition='{"modifiers": [{"pattern": "^bbb$", "filter": ""}]}')

        self.assert_file('target/aaa', b'a')
        self.assert_file('target/bbb')

    def test_config_environment_file(self):
        self.create_directory('target')
        self.create_file('source/.creep.env', b'{"default": {"connection": "file:///../target"}}')
        self.create_file('source/aaa', b'a')

        self.deploy('source', ['default'])

        self.assert_file('target/aaa', b'a')

    def test_config_environment_inline(self):
        self.create_directory('target')
        self.create_file('source/aaa', b'a')

        self.deploy('source', ['default'], environment='{"default": {"connection": "file:///../target"}}')

        self.assert_file('target/aaa', b'a')

    def test_target_deploy_then_append(self):
        self.create_directory('target')
        self.create_file('source/.creep.env', b'{"default": {"connection": "file:///../target"}}')

        # Create first file and deploy
        self.create_file('source/a/a', b'a')
        self.deploy('source', ['default'])
        self.assert_file('target/a/a', b'a')

        # Create second file and deploy
        self.create_file('source/b/b', b'b')
        self.deploy('source', ['default'])
        self.assert_file('target/a/a', b'a')
        self.assert_file('target/b/b', b'b')

    def test_target_deploy_then_delete(self):
        self.create_directory('target')
        self.create_file('source/.creep.env', b'{"default": {"connection": "file:///../target"}}')

        # Create files and deploy
        self.create_file('source/a/a', b'a')
        self.create_file('source/b/b', b'b')
        self.deploy('source', ['default'])
        self.assert_file('target/a/a', b'a')

        # Delete one file and deploy
        self.delete_file('source/b/b')
        self.deploy('source', ['default'])
        self.assert_file('target/a/a', b'a')
        self.assert_file('target/b/b')

    def test_target_deploy_then_replace(self):
        self.create_directory('target')
        self.create_file('source/.creep.env', b'{"default": {"connection": "file:///../target"}}')

        # Create file and deploy
        self.create_file('source/a/a', b'a')
        self.deploy('source', ['default'])
        self.assert_file('target/a/a', b'a')

        # Replace file and deploy again
        self.create_file('source/a/a', b'aaa')
        self.deploy('source', ['default'])
        self.assert_file('target/a/a', b'aaa')

    def test_target_deploy_archive(self):
        archive = self.create_file('archive.tar', b'')
        data = b'Some binary contents'

        with tarfile.open(archive, 'w') as tar:
            info = tarfile.TarInfo('item.bin')
            info.size = len(data)

            tar.addfile(info, io.BytesIO(initial_bytes=data))

        target = self.create_directory('target')
        env = self.create_file('.creep.env', b'{"default": {"connection": "file:///' + target.encode('utf-8') + b'"}}')

        self.deploy('archive.tar', ['default'], environment=env)

        self.assert_file('target/item.bin', data)

    def test_target_deploy_multiple(self):
        self.create_directory('target')
        self.create_file('source/aaa', b'a')
        self.create_file('source/b/bb', b'b')
        self.create_file('source/c/c/c', b'c')

        self.deploy('source', ['default'], environment='{"default": {"connection": "file:///../target"}}')

        self.assert_file('target/aaa', b'a')
        self.assert_file('target/b/bb', b'b')
        self.assert_file('target/c/c/c', b'c')

    def test_target_deploy_single(self):
        self.create_directory('target')
        self.create_file('source/.creep.env', b'{"default": {"connection": "file:///../target"}}')
        self.create_file('source/test', b'Hello, World!')

        self.deploy('source', ['default'])

        self.assert_file('target/test', b'Hello, World!')


if __name__ == '__main__':
    unittest.main()
