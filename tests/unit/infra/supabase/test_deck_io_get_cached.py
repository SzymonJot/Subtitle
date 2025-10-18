from infra.supabase.deck_repo import SBDeckIO
from typing import Any, Dict, List, Optional


# --- Fake Supabase client (chainable) -----------------------------------------

class _FakeResponse:
    def __init__(self, data: Optional[List[Dict[str, Any]]]):
        self.data = data

class _FakeQuery:
    def __init__(self, parent, table_name: str, rows: List[Dict[str, Any]]):
        self._parent = parent          # reference to FakeSB for call tracing
        self._table = table_name
        self._rows = rows

    def select(self, columns: str) -> "_FakeQuery":
        self._parent.last_select = columns
        return self

    def in_(self, column: str, values: List[str]) -> "_FakeQuery":
        self._parent.last_in = (column, list(values))
        # simple filter behavior for tests
        self._rows = [r for r in self._rows if r.get(column) in values]
        return self

    def execute(self) -> _FakeResponse:
        return _FakeResponse(self._rows)

class FakeSB:
    """
    Minimal fake Supabase client.
    Seed with: FakeSB({ "table_name": [ {row}, ... ] })
    """
    def __init__(self, seed: Optional[Dict[str, List[Dict[str, Any]]]] = None):
        self._tables = {k: list(v) for k, v in (seed or {}).items()}
        # call trace
        self.last_table: Optional[str] = None
        self.last_select: Optional[str] = None
        self.last_in: Optional[tuple[str, List[str]]] = None

    def table(self, name: str) -> _FakeQuery:
        self.last_table = name
        rows = list(self._tables.get(name, []))  # copy to avoid mutation between calls
        return _FakeQuery(self, name, rows)

    # helpers if you need to mutate during tests
    def set_table_rows(self, name: str, rows: List[Dict[str, Any]]) -> None:
        self._tables[name] = list(rows)

    def clear(self) -> None:
        self._tables.clear()

# --- SUT (System Under Test) --------------------------------------------------
# If you ALREADY have SBDeckIO in infra.supabase.deck_repo, delete the class below
# and:  from infra.supabase.deck_repo import SBDeckIO

class SBDeckIO:
    """Inline minimal implementation for testing; delete if you have the real one."""
    translation_table = "cached_translations"

    def __init__(self, sb: Any):
        self.sb = sb

    def get_cached(self, ids: list[str]) -> dict[str, dict[str, Any]]:
        """
        Return a mapping {cache_id -> row} for the given ids.
        """
        resp = (
            self.sb.table(self.translation_table)
            .select("*")
            .in_("cache_id", ids)
            .execute()
        )
        rows = resp.data or []
        return {row["cache_id"]: row for row in rows if "cache_id" in row}

# --- Tests --------------------------------------------------------------------

def test_get_cached_happy_path():
    fake_sb = FakeSB({
        "cached_translations": [
            {"cache_id": "a", "tw": "hej_tr"},
            {"cache_id": "b", "tw": "då_tr"},
            {"cache_id": "c", "tw": "nej_tr"},
        ]
    })
    io = SBDeckIO(fake_sb)

    out = io.get_cached(["a", "b"])

    # result shape
    assert set(out.keys()) == {"a", "b"}
    assert out["a"]["tw"] == "hej_tr"
    assert out["b"]["tw"] == "då_tr"

    # call shape
    assert fake_sb.last_table == "cached_translations"
    assert fake_sb.last_select == "*"
    assert fake_sb.last_in == ("cache_id", ["a", "b"])

def test_get_cached_empty_ids_returns_empty_dict():
    fake_sb = FakeSB({
        "cached_translations": [
            {"cache_id": "x", "tw": "x_tr"}
        ]
    })
    io = SBDeckIO(fake_sb)

    out = io.get_cached([])

    assert out == {}
    # Still acceptable if you choose to call SB with empty list; if you later
    # short-circuit to skip the call, you can assert last_in is None.
    # For now just ensure no crash:
    assert fake_sb.last_table == "cached_translations"
    assert fake_sb.last_select == "*"

def test_get_cached_unknown_ids_returns_empty_dict():
    fake_sb = FakeSB({
        "cached_translations": [
            {"cache_id": "a", "tw": "hej_tr"}
        ]
    })
    io = SBDeckIO(fake_sb)

    out = io.get_cached(["zzz"])

    assert out == {}
    assert fake_sb.last_in == ("cache_id", ["zzz"])

def test_get_cached_handles_none_data():
    # Simulate execute().data == None by overriding execute for this table
    class FakeQueryNone(_FakeQuery):
        def execute(self) -> _FakeResponse:
            return _FakeResponse(None)

    class FakeSBNone(FakeSB):
        def table(self, name: str) -> _FakeQuery:
            self.last_table = name
            rows = list(self._tables.get(name, []))
            return FakeQueryNone(self, name, rows)

    fake_sb = FakeSBNone({"cached_translations": []})
    io = SBDeckIO(fake_sb)

    out = io.get_cached(["a"])
    assert out == {}

def test_get_cached_ignores_rows_without_cache_id():
    fake_sb = FakeSB({
        "cached_translations": [
            {"cache_id": "a", "tw": "hej_tr"},
            {"wrong_key": "b", "tw": "oops"},
        ]
    })
    io = SBDeckIO(fake_sb)

    out = io.get_cached(["a", "b"])
    assert set(out.keys()) == {"a"}  # "b" row ignored due to missing cache_id
