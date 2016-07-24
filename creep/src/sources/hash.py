#!/usr/bin/env python

import hashlib
import os

from ..action import Action
from .. import path

class HashSource:
	def __init__ (self, directory, options):
		self.algorithm = options.get ('algorithm', 'md5')
		self.directory = directory
		self.follow = options.get ('follow', False)

	def current (self, base_path):
		return self.scan (os.path.join (base_path, self.directory))

	def diff (self, logger, base_path, work_path, rev_from, rev_to):
		return self.recurse (base_path, work_path, rev_from or {}, rev_to or {})

	def digest (self, path):
		hash = hashlib.new (self.algorithm)

		with open (path, 'rb') as file:
			for chunk in iter (lambda: file.read (4096), b''):
				hash.update (chunk)

		return hash.hexdigest ()

	def recurse (self, base_path, work_path, entries_from, entries_to):
		actions = []

		for name in set (entries_from.keys () + entries_to.keys ()):
			entry_from = entries_from.get (name, None)
			entry_to = entries_to.get (name, None)
			source = os.path.join (base_path, name)

			# Define action and recurse depending on "from" and "to" entries
			if isinstance (entry_from, dict):
				# Path was and still is a directory => recurse
				if isinstance (entry_to, dict):
					actions.extend (self.recurse (work_path, entry_from, entry_to, source))

				else:
					# Path was a directory but is now a file => add
					if entry_to is not None:
						actions.append (Action (source, Action.ADD))
						path.duplicate (source, work_path, source)

					# Path was a directory and now isn't => recurse with no rhs
					actions.extend (self.recurse (work_path, entry_from, {}, source))

			elif isinstance (entry_to, dict):
				# Path was a file but is now a directory => del
				if entry_from is not None:
					actions.append (Action (source, Action.DEL))
					path.duplicate (source, work_path, source)

				# Path wasn't a directory and now is => recurse with no lhs
				actions.extend (self.recurse (work_path, {}, entry_to, source))

			elif entry_from != entry_to:
				# Path is now a file => add
				if entry_to is not None:
					actions.append (Action (source, Action.ADD))
					path.duplicate (source, work_path, source)

				# Path is empty => del
				else:
					actions.append (Action (source, Action.DEL))

		return actions

	def scan (self, path):
		entries = {}

		for name in os.listdir (path):
			source = os.path.join (path, name)

			if not self.follow and os.path.islink (source):
				continue
			elif os.path.isdir (source):
				entry = self.scan (source)
			elif os.path.isfile (source):
				entry = self.digest (source)
			else:
				continue

			entries[name] = entry

		return entries
