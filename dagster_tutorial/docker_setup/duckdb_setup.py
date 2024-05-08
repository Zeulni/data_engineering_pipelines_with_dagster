import duckdb


def delete_all_duckdb_records():
    # Connect to the DuckDB database
    con = duckdb.connect("data/dagster_tutorial.duckdb")

    # List of tables to delete records from
    tables = ["api_ingest", "sqlite_ingest", "common_table", "top_words"]

    # Loop over the tables and delete all records
    for table in tables:
        query = f"DELETE FROM {table}"
        con.execute(query)

    # Commit the changes and close the connection
    con.commit()
    con.close()


if __name__ == "__main__":
    delete_all_duckdb_records()
