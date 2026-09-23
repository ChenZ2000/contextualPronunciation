from __future__ import annotations

import unittest

from tests.core_loader import load

lifecycle = load("lifecycle")


class FakeExtensionPoint:
	def __init__(self):
		self.handlers = []

	def register(self, handler):
		self.handlers.append(handler)

	def unregister(self, handler):
		self.handlers.remove(handler)


class LifecycleTests(unittest.TestCase):
	def test_registration_and_unregistration_are_idempotent(self):
		point = FakeExtensionPoint()

		def handler(value):
			return value

		registration = lifecycle.ExtensionRegistration(point, handler)
		registration.start()
		registration.start()
		self.assertEqual([handler], point.handlers)
		self.assertTrue(registration.registered)
		registration.stop()
		registration.stop()
		self.assertEqual([], point.handlers)
		self.assertFalse(registration.registered)


if __name__ == "__main__":
	unittest.main()
