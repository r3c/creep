#!/usr/bin/env python

import hashlib
import os

from ..action import Action

class HashSource:
	def __init__ (self, directory, options):
		self.algorithm = options.get ('algorithm', 'md5')
		self.directory = directory
		self.follow = options.get ('follow', False)

	def current (self):
		return self.scan (self.directory)

	def diff (self, logger, work, rev_from, rev_to):
		return self.prepare (work, rev_from or {}, rev_to or {}, '')

	def digest (self, path):
		hash = hashlib.new (self.algorithm)

		with open (path, 'rb') as file:
			for chunk in iter (lambda: file.read (4096), b''):
				hash.update (chunk)

		return hash.hexdigest ()

	def prepare (self, work, entries_from, entries_to, base):
		actions = []

		for name in set (entries_from.keys () + entries_to.keys ()):
			entry_from = entries_from.get (name, None)
			entry_to = entries_to.get (name, None)
			path = os.path.join (base, name)

			# Define action and recurse depending on "from" and "to" entries
			if isinstance (entry_from, dict):
				if isinstance (entry_to, dict):
					actions.extend (self.prepare (work, entry_from, entry_to, path))
					action = None
				else:
					actions.extend (self.prepare (work, entry_from, {}, path))
					action = entry_to is not None and Action (path, Action.ADD) or None
			else:
				if isinstance (entry_to, dict):
					actions.extend (self.prepare (work, {}, entry_to, path))
					action = entry_from is not None and Action (path, Action.DEL) or None
				elif entry_from != entry_to:
					action = Action (path, entry_to is not None and Action.ADD or Action.DEL)
				else:
					action = None

			# Prepare and append action
			if action is not None:
				action.prepare (work)
				actions.append (action)

		return actions

	def scan (self, base):
		entries = {}

		for name in os.listdir (base):
			path = os.path.join (base, name)

			if not self.follow and os.path.islink (path):
				continue
			elif os.path.isdir (path):
				entry = self.scan (path)
			elif os.path.isfile (path):
				entry = self.digest (path)
			else:
				continue

			entries[name] = entry

		return entries
