import types
from ctypes import util
from typing import re
import logging

from numba.core.typing.cffi_utils import _type_map
from sqlalchemy.engine.default import DefaultDialect
from sqlalchemy.dialects import registry
from sqlalchemy.sql.compiler import IdentifierPreparer

# from wherobots.db import connect as wherobots_connect
from wherobots.db.region import Region
from wherobots.db.runtime import Runtime
from wherobots.db.errors import NotSupportedError, OperationalError
from sqlalchemy.exc import DBAPIError, NoSuchTableError
import logging

print("\n\n\nRunning within wherobots-python-dbapi\n\n\n")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class WherobotsIdentifierPreparer(IdentifierPreparer):
    def __init__(self, dialect):
        super(WherobotsIdentifierPreparer, self).__init__(dialect, initial_quote='`', final_quote='`')

class WherobotsDialect1(DefaultDialect):
    name = 'wherobots1'
    driver = 'wherobots1'
    paramstyle = 'named'
    supports_sane_rowcount = True
    supports_sane_multi_rowcount = True
    supports_native_boolean = True
    supports_statement_cache = True

    @classmethod
    def dbapi(cls):
        print("\nRunning dbapi()\n")
        import wherobots.db as wherobots_db
        wherobots_db.paramstyle = 'named'
        return wherobots_db

    def create_connect_args(self, url):
        print("\nRunning create_connect_args()\n")
        runtime = url.query.get("runtime", "SEDONA")
        region = url.query.get("region", "AWS_US_WEST_2")
        print("\nRunning create_connect_args\n")

        if isinstance(runtime, str):
            runtime = Runtime[runtime]

        if isinstance(region, str):
            region = Region[region]

        opts = {
            "api_key": url.username,
            "runtime": runtime,
            "region": region
        }
        return ([], opts)

    def get_schema_names(self, connection, **kw):
        logger.info("Fetching schema names...")
        result = connection.execute('SHOW SCHEMAS IN wherobots_open_data')
        return [row[0] for row in result]

    def _get_table_columns(self, connection, table_name, schema):
        logger.info(f"Fetching columns for table {table_name} in schema {schema}...")
        full_table = table_name
        if schema:
            full_table = f"wherobots_open_data.{schema}.{table_name}"

        try:
            rows = connection.execute(f'DESCRIBE {full_table}').fetchall()
        except OperationalError as e:
            regex_fmt = r'TExecuteStatementResp.*SemanticException.*Table not found {}'
            regex = regex_fmt.format(re.escape(full_table))
            if re.search(regex, str(e)):
                raise NoSuchTableError(full_table)
            else:
                raise
        else:
            regex = r'Table .* does not exist'
            if len(rows) == 1 and re.match(regex, rows[0].col_name):
                raise NoSuchTableError(full_table)
            return rows

    def has_table(self, connection, table_name, schema=None, **kw):
        logger.info(f"Checking existence of table {table_name} in schema {schema}...")
        try:
            self._get_table_columns(connection, table_name, schema)
            return True
        except NoSuchTableError:
            return False

    def get_columns(self, connection, table_name, schema=None, **kw):
        logger.info(f"Fetching columns for table {table_name} in schema {schema}...")
        rows = self._get_table_columns(connection, table_name, schema)
        rows = [[col.strip() if col else None for col in row] for row in rows]
        rows = [row for row in rows if row[0] and row[0] != '# col_name']
        result = []
        for (col_name, col_type, _comment) in rows:
            if col_name == '# Partition Information':
                break
            col_type = re.search(r'^\w+', col_type).group(0)
            try:
                coltype = _type_map[col_type]
            except KeyError:
                logger.warning(f"Did not recognize type '{col_type}' of column '{col_name}'")
                coltype = types.NullType

            result.append({
                'name': col_name,
                'type': coltype,
                'nullable': True,
                'default': None,
            })
        return result

    # def get_table_names(self, connection, schema=None, **kw):
    #     print("\nRunning get_table_names()\n")
    #     query = 'SHOW TABLES'
    #     if schema:
    #         query += ' IN wherobots_open_data.' + self.identifier_preparer.quote_identifier(schema)
    #     print(f"\nQuery: {query}\n")
    #     result = connection.execute(query)
    #     # print(f"\nResult: {result}\n")
    #     return [row[0] for row in result]

    def get_table_names(self, connection, schema=None, **kw):
        logger.info(f"Fetching table names in schema {schema}...")
        query = 'SHOW TABLES'
        if schema:
            query += f' IN wherobots_open_data.{schema}'
        print(f"\n\n\n       get_table_names() Query - {query}")
        result = connection.execute(query)
        print(f"       get_table_names() result - {result}\n\n\n")
        resultSet = [row[1] for row in result]
        print(f"       get_table_names() resultSet - {resultSet}\n\n\n")
        return resultSet

    def do_rollback(self, dbapi_connection):
        print("\nRunning do_rollback()\n")
        pass

    def do_rollback_to_savepoint(self, connection, name):
        print("\nRunning do_rollback_to_savepoint()\n")
        pass

    def do_commit(self, dbapi_connection):
        print("\nRunning do_commit()\n")
        pass

    def do_execute(self, cursor, statement, parameters, context=None):
        print("\nRunning do_execute()\n")
        print(f"\n    Cursor: {cursor}\n")
        print(f"\n    statement: {statement}\n")
        print(f"\n    parameters: {parameters}\n")
        cursor.execute(statement, parameters)
        cursor.fetchall()

# # Register the dialect
registry.register("wherobots1", __name__, "WherobotsDialect1")