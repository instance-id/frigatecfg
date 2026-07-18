"""Mock form helper for simulating Flask/Werkzeug form submissions in tests."""

from __future__ import annotations


class MockForm:
    """Simulates a Werkzeug ImmutableMultiDict for form parsing.

    Supports .get(key, default) and .getlist(key) like Flask's request.form.
    """

    def __init__(self, data: dict[str, str | list[str]] | None = None):
        self._data: dict[str, list[str]] = {}
        if data:
            for key, value in data.items():
                if isinstance(value, list):
                    self._data[key] = value
                else:
                    self._data[key] = [value]

    def get(self, key: str, default: str | None = None) -> str | None:
        values = self._data.get(key)
        if values is None or not values:
            return default
        return values[0]

    def getlist(self, key: str) -> list[str]:
        return self._data.get(key, [])

    def __contains__(self, key: str) -> bool:
        return key in self._data and bool(self._data[key])
