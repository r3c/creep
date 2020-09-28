#!/usr/bin/python3

import io
import json
import logging
import os
import sys
import tarfile
import tempfile
import unittest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src import Application, Logger, load


def _get_json(obj):
    return json.dumps(obj).encode('utf-8')


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

    def deploy(self, config, location_names):
        logger = Logger.build(logging.WARNING)
        application = Application(logger, True)
        definition = load(logger, self.directory.name, config)

        self.assertFalse(definition is None)
        self.assertTrue(application.run(definition, location_names, [], [], None, None))

    def test_config_definition_file(self):
        self.create_directory('target')
        self.create_file('source/.creep.def', _get_json({"environment": ".test.env"}))
        self.create_file('source/.test.env', _get_json({"default": {"connection": "file:///../target"}}))
        self.create_file('source/aaa', b'a')

        self.deploy('source/.creep.def', ['default'])

        self.assert_file('target/.creep.def', None)
        self.assert_file('target/.test.env', None)
        self.assert_file('target/aaa', b'a')

    def test_config_definition_inline(self):
        self.create_directory('target')
        self.create_file('.creep.env', _get_json({"default": {"connection": "file:///../target"}}))
        self.create_file('source/aaa', b'a')

        self.deploy({"origin": "source"}, ['default'])

        self.assert_file('target/aaa', b'a')

    def test_config_definition_modifier(self):
        self.create_directory('target')
        self.create_file('source/.creep.def', _get_json({"modifiers": [{"pattern": "^bbb$", "filter": ""}]}))
        self.create_file('source/.creep.env', _get_json({"default": {"connection": "file:///../target"}}))
        self.create_file('source/aaa', b'a')
        self.create_file('source/bbb', b'b')

        self.deploy('source', ['default'])

        self.assert_file('target/.creep.def', None)
        self.assert_file('target/.creep.env', None)
        self.assert_file('target/aaa', b'a')
        self.assert_file('target/bbb')

    def test_config_environment_file(self):
        self.create_directory('target')
        self.create_file('source/.creep.env', _get_json({"default": {"connection": "file:///../target"}}))
        self.create_file('source/aaa', b'a')

        self.deploy('source', ['default'])

        self.assert_file('target/.creep.env', None)
        self.assert_file('target/aaa', b'a')

    def test_config_environment_inline(self):
        self.create_directory('target')
        self.create_file('source/.creep.def',
                         _get_json({"environment": {
                             "default": {
                                 "connection": "file:///../target"
                             }
                         }}))
        self.create_file('source/aaa', b'a')

        self.deploy('source', ['default'])

        self.assert_file('target/.creep.env', None)
        self.assert_file('target/aaa', b'a')

    def test_target_cascade_inline(self):
        self.create_directory('target1')
        self.create_directory('target2')
        self.create_file(
            'source1/.creep.def',
            _get_json({
                "cascades": [{
                    "environment": {
                        "default": {
                            "connection": "file:///../target2"
                        }
                    },
                    "modifiers": [{
                        "pattern": "^c$",
                        "filter": ""
                    }],
                    "origin": "../source2"
                }],
                "environment": {
                    "default": {
                        "connection": "file:///../target1"
                    }
                }
            }))
        self.create_file('source1/a', b'a')
        self.create_file('source2/b', b'b')
        self.create_file('source2/c', b'c')

        self.deploy('source1', ['default'])

        self.assert_file('target1/a', b'a')
        self.assert_file('target2/b', b'b')
        self.assert_file('target2/c', None)

    def test_target_cascade_of_cascade(self):
        self.create_directory('target')
        self.create_file('source/.creep.def', _get_json({"cascades": ["a"]}))
        self.create_file('source/a/.creep.def', _get_json({"cascades": ["b"]}))
        self.create_file('source/a/b/.creep.env', _get_json({"default": {"connection": "file:///../../../target"}}))
        self.create_file('source/a/b/c', b'c')

        self.deploy('source', ['default'])

        self.assert_file('target/.creep.def', None)
        self.assert_file('target/a/.creep.def', None)
        self.assert_file('target/a/b/.creep.env', None)
        self.assert_file('target/c', b'c')

    def test_target_cascade_reference(self):
        self.create_directory('target1')
        self.create_directory('target2')
        self.create_file(
            'source1/.creep.def',
            _get_json({
                "cascades": ["../source2_def"],
                "environment": {
                    "default": {
                        "connection": "file:///../target1"
                    }
                }
            }))
        self.create_file(
            'source2_def',
            _get_json({
                "environment": "source2_env",
                "modifiers": [{
                    "pattern": "^c$",
                    "filter": ""
                }],
                "origin": "source2"
            }))
        self.create_file('source2_env', _get_json({"default": {"connection": "file:///../target2"}}))
        self.create_file('source1/a', b'a')
        self.create_file('source2/b', b'b')
        self.create_file('source2/c', b'c')

        self.deploy('source1', ['default'])

        self.assert_file('target1/a', b'a')
        self.assert_file('target2/b', b'b')
        self.assert_file('target2/c', None)

    def test_target_deploy_then_append(self):
        self.create_directory('target')
        self.create_file('source/.creep.env', _get_json({"default": {"connection": "file:///../target"}}))

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
        self.create_file('source/.creep.env', _get_json({"default": {"connection": "file:///../target"}}))

        # Create files and deploy
        self.create_file('source/a/a', b'a')
        self.create_file('source/b/b', b'b')

        self.deploy('source', ['default'])

        self.assert_file('target/.creep.env', None)
        self.assert_file('target/a/a', b'a')
        self.assert_file('target/b/b', b'b')

        # Delete one file and deploy
        self.delete_file('source/b/b')

        self.deploy('source', ['default'])

        self.assert_file('target/.creep.env', None)
        self.assert_file('target/a/a', b'a')
        self.assert_file('target/b/b')

    def test_target_deploy_then_replace(self):
        self.create_directory('target')
        self.create_file('source/.creep.env', _get_json({"default": {"connection": "file:///../target"}}))

        # Create file and deploy
        self.create_file('source/a/a', b'a')

        self.deploy('source', ['default'])

        self.assert_file('target/.creep.env', None)
        self.assert_file('target/a/a', b'a')

        # Replace file and deploy again
        self.create_file('source/a/a', b'aaa')

        self.deploy('source', ['default'])

        self.assert_file('target/.creep.env', None)
        self.assert_file('target/a/a', b'aaa')

    def test_target_deploy_archive(self):
        archive = self.create_file('archive.tar', b'')
        data = b'Some binary contents'

        with tarfile.open(archive, 'w') as tar:
            info = tarfile.TarInfo('item.bin')
            info.size = len(data)

            tar.addfile(info, io.BytesIO(initial_bytes=data))

        target = self.create_directory('target')

        self.create_file('.creep.def', _get_json({"origin": "archive.tar"}))
        self.create_file('.creep.env', _get_json({"default": {"connection": "file:///" + target}}))

        self.deploy('.', ['default'])

        self.assert_file('target/item.bin', data)

    def test_target_deploy_archive_subdir(self):
        archive = self.create_file('archive.tar', b'')
        data = b'Some binary contents'

        with tarfile.open(archive, 'w') as tar:
            info = tarfile.TarInfo('remove/keep/item.bin')
            info.size = len(data)

            tar.addfile(info, io.BytesIO(initial_bytes=data))

        target = self.create_directory('target')

        self.create_file('.creep.def', _get_json({"origin": "archive.tar#remove"}))
        self.create_file('.creep.env', _get_json({"default": {"connection": "file:///" + target}}))

        self.deploy('.', ['default'])

        self.assert_file('target/keep/item.bin', data)

    def test_target_deploy_multiple(self):
        self.create_directory('target')
        self.create_file('source/.creep.env', _get_json({"default": {"connection": "file:///../target"}}))
        self.create_file('source/aaa', b'a')
        self.create_file('source/b/bb', b'b')
        self.create_file('source/c/c/c', b'c')

        self.deploy('source', ['default'])

        self.assert_file('target/.creep.env', None)
        self.assert_file('target/aaa', b'a')
        self.assert_file('target/b/bb', b'b')
        self.assert_file('target/c/c/c', b'c')

    def test_target_deploy_single(self):
        self.create_directory('target')
        self.create_file('source/.creep.env', _get_json({"default": {"connection": "file:///../target"}}))
        self.create_file('source/test', b'Hello, World!')

        self.deploy('source', ['default'])

        self.assert_file('target/.creep.env', None)
        self.assert_file('target/test', b'Hello, World!')

    def test_deploy_url(self):
        target = self.create_directory('target')

        self.create_file(
            '.creep.def',
            _get_json({
                "origin":
                "https://gist.github.com/r3c/2004ebb0763a02b5945287f3dfa2e3e2/archive/003650e2639b49edc8c4ff6eb20e0931edb547dc.zip#2004ebb0763a02b5945287f3dfa2e3e2-003650e2639b49edc8c4ff6eb20e0931edb547dc"
            }))
        self.create_file('.creep.env', _get_json({"default": {"connection": "file:///" + target}}))

        self.deploy('.', ['default'])

        self.assert_file('target/filename', b'test')


if __name__ == '__main__':
    unittest.main()
