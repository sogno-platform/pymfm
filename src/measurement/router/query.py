import datetime
import os
from typing import Literal, Optional, Union
import pandas as pd
from sqlalchemy import (
    DateTime,
    Float,
    MetaData,
    String,
    create_engine,
    text,
    Table,
    Column,
    and_ as sqland,
    case,
)
from fastapi import HTTPException
import sqlalchemy


DB_URL = f"postgresql://{os.getenv('POSTGRES_USER','postgres')}:{os.getenv('POSTGRES_PASSWORD','')}@{os.getenv('POSTGRES_HOST','localhost')}:5432/{os.getenv('POSTGRES_DB','postgres')}"
ENGINE = create_engine(DB_URL, echo=True)
META = MetaData()


make_ht_query_template = text("SELECT create_hypertable(:table_name, by_range('timestamp'))")


def list_all_tables():
    META.reflect(ENGINE)
    return list(META.tables.keys())


def get_alch_table(name: str):
    return Table(
        name,
        META,
        Column("timestamp", DateTime, default=datetime.datetime.now(), nullable=False),
        Column("value", Float),
        Column("unit", String),
        extend_existing=True,
    )


def delete_table(table_id: str):
    tab = get_alch_table(table_id)
    with ENGINE.connect() as conn:
        tab.drop(conn, True)
        conn.commit()


def create_table(table_id: str):
    tab = get_alch_table(table_id)

    with ENGINE.begin() as conn:
        tab.create(bind=conn, checkfirst=True)
        try:
            conn.execute(make_ht_query_template.params(table_name=tab.name))
        except sqlalchemy.exc.DatabaseError:
            print("Hyper table could not be created, likely because it already exist.")
        conn.close()


def update_columns(table_id: str, data: pd.DataFrame):
    tab = get_alch_table(table_id)
    start = data.index.min()
    end = data.index.max()

    get_times_query = (
        tab.select().with_only_columns(tab.c.timestamp).where(sqland(tab.c.timestamp >= start, tab.c.timestamp <= end))
    )
    # split df index into existing and new entries
    with ENGINE.connect() as conn:
        existing_ts = [r[0] for r in conn.execute(get_times_query) if r[0] in data.index]
        new_ts = [ts for ts in data.index if ts not in existing_ts]
        conn.commit()

    update_dict = data.loc[existing_ts].to_dict()

    update_query = (
        tab.update()
        .filter(tab.c.timestamp.in_(existing_ts))
        .values(
            {
                tab.c.value: case(
                    update_dict["value"], value=tab.c.timestamp
                ),  # lookup what to insert in "value" dict, use timestamp as key and insert into "value" colum of db
                tab.c.unit: case(
                    update_dict["unit"], value=tab.c.timestamp
                ),  # lookup what to insert in "unit" dict, use timestamp as key and insert into "unit" colum of db
            }
        )
    )

    with ENGINE.connect() as conn:
        # update existing
        conn.execute(update_query)
        # add new
        data.loc[new_ts].to_sql(table_id, con=conn, if_exists="append")
        conn.commit()


def insert_data(table_id: str, data: pd.DataFrame, if_exists: Literal["fail"] | Literal["append"] | Literal["update"]):
    tab = get_alch_table(table_id)

    if if_exists == "update":
        update_columns(table_id, data)
    else:
        with ENGINE.connect() as conn:
            data.to_sql(table_id, con=conn, if_exists=if_exists)
            conn.commit()


def get_data(table_id: str, start: Optional[datetime.datetime] = None, end: Optional[datetime.datetime] = None):
    tab = get_alch_table(table_id)
    if start and end:
        get_query = tab.select().where(sqland(tab.c.timestamp >= start, tab.c.timestamp <= end))
    elif start:
        get_query = tab.select().where(tab.c.timestamp >= start)
    elif end:
        get_query = tab.select().where(tab.c.timestamp <= end)
    else:
        get_query = tab.select()

    get_query = get_query.params(table_name=table_id)
    with ENGINE.begin() as conn:
        try:
            return pd.read_sql(get_query, con=conn, index_col="timestamp")
        except sqlalchemy.exc.ProgrammingError:
            raise HTTPException(404, "Measurement does not exist")


if __name__ == "__main__":
    print(get_data("test_data2", start=datetime.datetime(2024, 9, 12, 0, 5, 0)))
