from __future__ import annotations

import typing as t
import uuid

import pandas as pd
from sqlglot import exp

from sqlmesh.core.dialect import pandas_to_sql
from sqlmesh.core.engine_adapter.base import EngineAdapter
from sqlmesh.core.engine_adapter.shared import DataObject, DataObjectType

if t.TYPE_CHECKING:

    from trino.dbapi import Connection as TrinoConnection
    from sqlmesh.core.engine_adapter._typing import DF




class TrinoEngineAdapter(EngineAdapter):
    DIALECT = "trino"
    ESCAPE_JSON = False

    @property
    def connection(self) -> TrinoConnection:
        return self.cursor.connection

    def __get_catalog_name(self, catalog_name: t.Optional[str] = None) -> str:
        catalog_name = catalog_name or self.connection.catalog
        if not catalog_name:
            raise ValueError("catalog is required for Trino")
        return catalog_name

    def _fetch_native_df(self, query: t.Union[exp.Expression, str]) -> DF:
        """Fetches a DataFrame that can be either Pandas or PySpark from the cursor"""
        sql = self._to_sql(query)
        return pd.read_sql_query(sql, self.connection)

    def _get_data_objects(
        self, schema_name: str, catalog_name: t.Optional[str] = None
    ) -> t.List[DataObject]:
        """
        Returns all the data objects that exist in the given schema and optionally catalog.
        """
        catalog_name = self.__get_catalog_name(catalog_name)
        query = f"""
            SELECT
                t.table_catalog AS catalog,
                t.table_name AS name,
                t.table_schema AS schema,
                CASE
                    WHEN mv.name is not null THEN 'materializedview'
                    WHEN t.table_type = 'BASE TABLE' THEN 'table'
                    ELSE t.table_type
                END AS type
            FROM { catalog_name }.information_schema.tables t
            LEFT JOIN system.metadata.materialized_views mv
                ON mv.catalog_name = t.table_catalog
                AND mv.schema_name = t.table_schema
                AND mv.name = t.table_name
            WHERE
                t.table_schema = '{ schema_name }'
                AND (mv.catalog_name is null OR mv.catalog_name =  '{ catalog_name }')
                AND (mv.schema_name is null OR mv.schema_name =  '{ schema_name }')
        """
        df = self.fetchdf(query)
        return [
            DataObject(
                catalog=row.catalog,  # type: ignore
                schema=row.schema,  # type: ignore
                name=row.name,  # type: ignore
                type=DataObjectType.from_str(row.type),  # type: ignore
            )
            for row in df.itertuples()
        ]

    def drop_schema(
        self,
        schema_name: str,
        catalog_name: t.Optional[str] = None,
        ignore_if_not_exists: bool = True,
        cascade: bool = False,
    ) -> None:
        """Drop a schema from a name or qualified table name.
        Note: Cascade is not supported so we manually drop all the tables
        """
        catalog_name = self.__get_catalog_name(catalog_name)
        if cascade:
            for data_object in self._get_data_objects(schema_name, catalog_name):
                self.drop_table(
                    str(data_object),
                    exists=False,
                )
        super().drop_schema(schema_name, ignore_if_not_exists=ignore_if_not_exists, cascade=False)