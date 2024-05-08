import hashlib
from datetime import datetime
import pandas as pd
import requests

from dagster import (
    AssetExecutionContext,
    MetadataValue,
    asset,
    MaterializeResult,
)
from dagster_duckdb import DuckDBResource

from ..resources import SqliteResource


# * INGEST 1
@asset(compute_kind="HackerNews API")
def topstories_api_ingest(
    context: AssetExecutionContext, duckdb: DuckDBResource
) -> MaterializeResult:
    """Ingest top stories from the Hacker News API into data warehouse."""
    newstories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    top_new_story_ids = requests.get(newstories_url).json()[:100]

    results = []
    for item_id in top_new_story_ids:
        item = requests.get(
            f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
        ).json()
        results.append(item)

        if len(results) % 20 == 0:
            context.log.info(f"Got {len(results)} items so far.")

    df = pd.DataFrame(results)

    df["data_transfer_timestamp"] = pd.Timestamp.now()

    # Calculate hashkey based on title
    df["hashkey"] = df["title"].apply(lambda x: hashlib.sha256(x.encode()).hexdigest())

    with duckdb.get_connection() as conn:
        df.to_sql("api_ingest", con=conn, if_exists="append", index=False)
        total_num_records = conn.execute("SELECT COUNT(*) FROM api_ingest").fetchone()[
            0
        ]

    return MaterializeResult(
        metadata={
            "total_num_records": total_num_records,  # Metadata can be any key-value pair
            "preview": MetadataValue.md(df.head().to_markdown()),
        }
    )


# * INGEST 2
@asset(compute_kind="sqlite")
def topstories_sqlite_ingest(
    context: AssetExecutionContext, sqlite: SqliteResource, duckdb: DuckDBResource
) -> MaterializeResult:
    """Ingest top stories from local Hacker News database into data warehouse."""

    # Connect to the SQLite database and read the data
    conn = sqlite.get_connection()
    df = pd.read_sql("SELECT * FROM api_ingest", con=conn)

    context.log.info(f"Read {len(df)} records from SQLite.")

    # Convert string-type columns back to list
    for col in df.columns:
        if col == "kids":
            df[col] = df[col].apply(
                lambda x: x.split(", ") if isinstance(x, str) else x
            )

    # Add data_transfer_timestamp and hashkey
    df["data_transfer_timestamp"] = pd.Timestamp.now()
    df["hashkey"] = df["title"].apply(lambda x: hashlib.sha256(x.encode()).hexdigest())

    # Save df to DuckDB
    with duckdb.get_connection() as conn:
        df.to_sql("sqlite_ingest", con=conn, if_exists="append", index=False)
        total_num_records = conn.execute(
            "SELECT COUNT(*) FROM sqlite_ingest"
        ).fetchone()[0]

    return MaterializeResult(
        metadata={
            "total_num_records": total_num_records,
            "preview": MetadataValue.md(df.head().to_markdown()),
        }
    )


# * TRANSFORM 1
@asset(
    deps=[topstories_api_ingest, topstories_sqlite_ingest],
    compute_kind="duckdb",
)
def common_table(duckdb: DuckDBResource) -> MaterializeResult:
    """Merge different sources into one common table in the data warehouse."""
    with duckdb.get_connection() as conn:
        # Check if the table exists
        table_exists = (
            conn.execute(
                """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = 'common_table'
            """
            ).fetchone()[0]
            > 0
        )

        # If the table does not exist, create it
        if not table_exists:
            conn.execute(
                """
                CREATE TABLE common_table AS
                SELECT * FROM api_ingest
                UNION ALL
                SELECT * FROM sqlite_ingest
                """
            )
        else:
            # If the table exists, append only new data which was not already added (based on the title hashkey)
            conn.execute(
                """
                INSERT INTO common_table
                SELECT * FROM api_ingest
                WHERE hashkey NOT IN (SELECT hashkey FROM common_table)
                UNION ALL
                SELECT * FROM sqlite_ingest
                WHERE hashkey NOT IN (SELECT hashkey FROM common_table)
                """
            )

        total_num_records = conn.execute(
            "SELECT COUNT(*) FROM common_table"
        ).fetchone()[0]

    return MaterializeResult(metadata={"total_num_records": total_num_records})


# * TRANSFORM 2
@asset(
    deps=[common_table],
    compute_kind="duckdb",
)
def most_frequent_title_words(duckdb: DuckDBResource) -> MaterializeResult:
    """Count most frequent words in the titles of the top stories and save them to the data warehouse."""
    stopwords = ["a", "the", "an", "of", "to", "in", "for", "and", "with", "on", "is"]

    with duckdb.get_connection() as conn:
        topstories = pd.read_sql("SELECT * FROM common_table", conn)

        word_counts = {}
        for raw_title in topstories["title"]:
            title = raw_title.lower()
            for word in title.split():
                cleaned_word = word.strip(".,-!?:;()[]'\"-")
                if cleaned_word not in stopwords and len(cleaned_word) > 0:
                    word_counts[cleaned_word] = word_counts.get(cleaned_word, 0) + 1

        top_words = {
            pair[0]: pair[1]
            for pair in sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[
                :25
            ]
        }

        # Convert the top_words dictionary to a DataFrame
        df_top_words = pd.DataFrame(list(top_words.items()), columns=["word", "count"])

        # Replace the entire table
        df_top_words.to_sql("top_words", con=conn, if_exists="replace", index=False)

    return MaterializeResult(
        metadata={"top_words": MetadataValue.md(df_top_words.head().to_markdown())}
    )


# * FRONTEND
@asset(
    deps=[most_frequent_title_words],
    compute_kind="matplotlib",
)
def streamlit_dashboard(context: AssetExecutionContext) -> MaterializeResult:
    """Trigger the Streamlit app to reload the data."""
    # Path to a file that the Streamlit app will check to determine if it needs to reload data
    signal_file_path = "frontend/streamlit_reload_signal.txt"

    # Write the current timestamp to the file
    with open(signal_file_path, "w") as file:
        file.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    context.log.info("Streamlit reload signal updated.")

    return MaterializeResult(
        metadata={
            "signal_update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "streamlit_link": MetadataValue.md(
                "[Streamlit App](http://localhost:8502)"
            ),
        }
    )
