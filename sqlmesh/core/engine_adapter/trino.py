from __future__ import annotations

import typing as t
import uuid

import pandas as pd
from sqlglot import exp

from sqlmesh.core.dialect import pandas_to_sql
from sqlmesh.core.engine_adapter.base import EngineAdapter
if t.TYPE_CHECKING:
    from sqlmesh.core._typing import TableName
    from sqlmesh.core.engine_adapter._typing import Query, QueryOrDF




class TrinoEngineAdapter(EngineAdapter):
    DIALECT = "trino"
    DEFAULT_BATCH_SIZE = 1000
    ESCAPE_JSON = True
    SUPPORTS_MATERIALIZED_VIEWS = True

    @property
    def cursor(self) -> t.Any:

        # set it to `qmark` since that doesn't cause issues.
        cursor = self._connection_pool.get_cursor()
        cursor.paramstyle = "qmark"
        return cursor


    def _short_hash(self) -> str:
        return uuid.uuid4().hex[:8]
