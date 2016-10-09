#!/usr/bin/env python

import logging
import os
import shutil
import sys
import tempfile
import unittest

sys.path.append (os.path.dirname (os.path.dirname (__file__)))

from src import Deployer, Logger

class DeployerTester (unittest.TestCase):
	def execute (self, steps):
		directory = tempfile.mkdtemp ()

		try:
			source = os.path.join (directory, 'source')
			target = os.path.join (directory, 'target')

			os.makedirs (source)
			os.makedirs (target)

			for step in steps:
				step (source, target)
		finally:
			shutil.rmtree (directory)

	def step_create (self, source, files):
		for relative, data in files.items ():
			directory = os.path.join (source, os.path.dirname (relative))

			if not os.path.exists (directory):
				os.makedirs (directory)

			with open (os.path.join (source, relative), 'wb') as file:
				file.write (data)

	def step_deploy (self, source, locations, definition = '.creep.def', environment = '.creep.env'):
		deployer = Deployer (Logger.build (logging.CRITICAL), definition, environment, True)

		self.assertTrue (deployer.deploy (source, locations, [], [], None, None))

	def step_expect (self, target, files):
		for relative, expected in files.items ():
			path = os.path.join (target, relative)

			self.assertEqual (os.path.exists (path), expected is not None)

			if expected is not None:
				with open (path, 'rb') as file:
					data = file.read ()

				self.assertEqual (data, expected)

	def step_set_definition (self, source, definition, path = '.creep.def'):
		with open (os.path.join (source, path), 'wb') as file:
			file.write (definition)

	def step_set_environment (self, source, environment, path = '.creep.env'):
		with open (os.path.join (source, path), 'wb') as file:
			file.write (environment)

	def test_config_definition_file (self):
		self.execute ([
			lambda s, t: self.step_set_environment (s, b'{"default": {"connection": "file:///../target"}}'),
			lambda s, t: self.step_set_definition (s, b'{"modifiers": [{"pattern": "^bbb$", "filter": ""}]}'),
			lambda s, t: self.step_create (s, {'aaa': b'a', 'bbb': b'b'}),
			lambda s, t: self.step_deploy (s, ['default']),
			lambda s, t: self.step_expect (t, {'aaa': b'a', 'bbb': None})
		])

	def test_config_definition_inline (self):
		self.execute ([
			lambda s, t: self.step_set_environment (s, b'{"default": {"connection": "file:///../target"}}'),
			lambda s, t: self.step_create (s, {'aaa': b'a', 'bbb': b'b'}),
			lambda s, t: self.step_deploy (s, ['default'], '{"modifiers": [{"pattern": "^bbb$", "filter": ""}]}'),
			lambda s, t: self.step_expect (t, {'aaa': b'a', 'bbb': None})
		])

	def test_config_environment_file (self):
		files = {'aaa': b'a'}

		self.execute ([
			lambda s, t: self.step_set_environment (s, b'{"default": {"connection": "file:///../target"}}'),
			lambda s, t: self.step_create (s, files),
			lambda s, t: self.step_deploy (s, ['default']),
			lambda s, t: self.step_expect (t, files)
		])

	def test_config_environment_inline (self):
		files = {'aaa': b'a'}

		self.execute ([
			lambda s, t: self.step_create (s, files),
			lambda s, t: self.step_deploy (s, ['default'], '.creep.def', '{"default": {"connection": "file:///../target"}}'),
			lambda s, t: self.step_expect (t, files)
		])

	def test_file_basic_many (self):
		files = {'aaa': b'a', 'b/bb': b'b', 'c/c/c': b'c'}

		self.execute ([
			lambda s, t: self.step_set_environment (s, b'{"default": {"connection": "file:///../target"}}'),
			lambda s, t: self.step_create (s, files),
			lambda s, t: self.step_deploy (s, ['default']),
			lambda s, t: self.step_expect (t, files)
		])

	def test_file_basic_one (self):
		files = {'test': b'Hello, World!'}

		self.execute ([
			lambda s, t: self.step_set_environment (s, b'{"default": {"connection": "file:///../target"}}'),
			lambda s, t: self.step_create (s, files),
			lambda s, t: self.step_deploy (s, ['default']),
			lambda s, t: self.step_expect (t, files)
		])

	def test_file_multi_replace (self):
		a1 = {'a/a': b'a'}
		a2 = {'a/a': b'aaa'}

		self.execute ([
			lambda s, t: self.step_set_environment (s, b'{"default": {"connection": "file:///../target"}}'),
			lambda s, t: self.step_create (s, a1),
			lambda s, t: self.step_deploy (s, ['default']),
			lambda s, t: self.step_expect (t, a1),
			lambda s, t: self.step_create (s, a2),
			lambda s, t: self.step_deploy (s, ['default']),
			lambda s, t: self.step_expect (t, a2)
		])

	def test_file_multi_update (self):
		a = {'a/a': b'a'}
		b = {'b/b': b'b'}
		c = a.copy ()
		c.update (b)

		self.execute ([
			lambda s, t: self.step_set_environment (s, b'{"default": {"connection": "file:///../target"}}'),
			lambda s, t: self.step_create (s, a),
			lambda s, t: self.step_deploy (s, ['default']),
			lambda s, t: self.step_expect (t, a),
			lambda s, t: self.step_create (s, c),
			lambda s, t: self.step_deploy (s, ['default']),
			lambda s, t: self.step_expect (t, c),
			lambda s, t: self.step_create (s, b),
			lambda s, t: self.step_deploy (s, ['default']),
			lambda s, t: self.step_expect (t, b)
		])

if __name__ == '__main__':
    unittest.main ()
