"""Small idempotent wrapper around NVDA extension-point registration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class ExtensionRegistration:
	def __init__(self, extension_point: Any, handler: Callable[..., Any]):
		self._extension_point = extension_point
		self._handler = handler
		self._registered = False

	@property
	def registered(self) -> bool:
		return self._registered

	def start(self) -> None:
		if self._registered:
			return
		self._extension_point.register(self._handler)
		self._registered = True

	def stop(self) -> None:
		if not self._registered:
			return
		self._extension_point.unregister(self._handler)
		self._registered = False
