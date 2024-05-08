from dagster import (
    Definitions,
    ScheduleDefinition,
    define_asset_job,
)

from .assets import (
    topstories_api_ingest,
    topstories_sqlite_ingest,
    common_table,
    most_frequent_title_words,
    streamlit_dashboard,
)
from dagster_duckdb import DuckDBResource
from .resources import SqliteResource


api_ingest_resource = DuckDBResource(database="data/dagster_tutorial.duckdb")
sql_ingest_resource = SqliteResource(database="data/hackernews.sqlite")

api_pipeline_job = define_asset_job(
    name="api_pipeline_job",
    selection=[
        topstories_api_ingest,
        common_table,
        most_frequent_title_words,
        streamlit_dashboard,
    ],
)
api_pipeline_schedule = ScheduleDefinition(
    job=api_pipeline_job,
    cron_schedule="0 * * * *",  # every hour
)

sqlite_pipeline_job = define_asset_job(
    name="sqlite_pipeline_job",
    selection=[
        topstories_sqlite_ingest,
        common_table,
        most_frequent_title_words,
        streamlit_dashboard,
    ],
)
sqlite_pipeline_schedule = ScheduleDefinition(
    job=sqlite_pipeline_job,
    cron_schedule="*/15 * * * *",  # every 15 minutes
)

defs = Definitions(
    assets=[
        topstories_api_ingest,
        topstories_sqlite_ingest,
        common_table,
        most_frequent_title_words,
        streamlit_dashboard,
    ],
    resources={"duckdb": api_ingest_resource, "sqlite": sql_ingest_resource},
    jobs=[api_pipeline_job, sqlite_pipeline_job],
    schedules=[api_pipeline_schedule, sqlite_pipeline_schedule],
)
