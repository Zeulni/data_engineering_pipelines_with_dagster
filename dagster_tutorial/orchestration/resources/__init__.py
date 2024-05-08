from dagster import ConfigurableResource

import sqlite3


class SqliteResource(ConfigurableResource):
    database: str

    def get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)
