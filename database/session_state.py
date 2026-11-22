"""Per-connection bookkeeping shared by the storage backends.

* `once(key)`: True only the first time per connection session. Used so schema
  and data-label checks run once, not before every query that needs them.
* `write_generation`: increases on every write. Read-only results may be
  cached against it; any insert/update/delete invalidates them immediately.
"""


class SessionState:
    def _init_session_state(self) -> None:
        self._once_keys = set()
        self.write_generation = 0

    def once(self, key: str) -> bool:
        if key in self._once_keys:
            return False
        self._once_keys.add(key)
        return True

    def _mark_write(self) -> None:
        self.write_generation += 1

    def _reset_session_state(self) -> None:
        self._once_keys.clear()
        self.write_generation += 1
