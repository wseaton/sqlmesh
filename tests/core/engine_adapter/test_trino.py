# type: ignore
from unittest.mock import call

from pytest_mock.plugin import MockerFixture

from sqlmesh.core.engine_adapter import TrinoEngineAdapter
from sqlmesh.core.engine_adapter.shared import DataObject, DataObjectType


def test_create_table_properties(mocker: MockerFixture):
    connection_mock = mocker.NonCallableMock()
    cursor_mock = mocker.Mock()
    connection_mock.cursor.return_value = cursor_mock
    adapter = TrinoEngineAdapter(lambda: connection_mock)
    get_data_objects_mock = mocker.Mock()
    get_data_objects_mock.return_value = [
        DataObject(
            catalog="test_catalog",
            schema="test_schema",
            name="test_table",
            type=DataObjectType.TABLE,
        ),
        DataObject(
            catalog="test_catalog", schema="test_schema", name="test_view", type=DataObjectType.VIEW
        ),
        DataObject(
            catalog="test_catalog",
            schema="ignore_schema",
            name="test_table",
            type=DataObjectType.TABLE,
        ),
    ]
    adapter._TrinoEngineAdapter_get_data_objects = get_data_objects_mock
    adapter.drop_schema(
        "test_schema",
        "test_catalog",
        ignore_if_not_exists=True,
        cascade=True,
    )
    cursor_mock.execute.assert_has_calls(
        [
            call("DROP TABLE IF EXISTS `test_catalog`.`test_schema`.`test_table`"),
            call("DROP TABLE IF EXISTS `test_catalog`.`test_schema`.`test_view`"),
            call("DROP SCHEMA IF EXISTS `test_schema` CASCADE"),
        ]
    )