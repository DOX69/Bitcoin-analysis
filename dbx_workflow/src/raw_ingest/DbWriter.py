from datetime import datetime, timezone

import pandas as pd
from psycopg import errors, sql


BRONZE_SCHEMA = "bronze"
OHLCV_COLUMNS = {
    "time": "TIMESTAMP NOT NULL",
    "low": "DOUBLE PRECISION NOT NULL",
    "high": "DOUBLE PRECISION NOT NULL",
    "open": "DOUBLE PRECISION NOT NULL",
    "close": "DOUBLE PRECISION NOT NULL",
    "volume": "DOUBLE PRECISION NOT NULL",
}
RATE_COLUMNS = {
    "time": "TIMESTAMP NOT NULL",
    "rate": "DOUBLE PRECISION NOT NULL",
}
TABLE_COLUMNS = {
    "btc_usd_ohlcv": OHLCV_COLUMNS,
    "eth_usd_ohlcv": OHLCV_COLUMNS,
    "usd_chf_rates": RATE_COLUMNS,
    "usd_eur_rates": RATE_COLUMNS,
    "bgeometrics_btc_technical_indicators": {
        "time": "TIMESTAMP NOT NULL",
        "d": "DATE NOT NULL",
        "unixTs": "BIGINT",
        "rsi": "DOUBLE PRECISION",
        "macd": "DOUBLE PRECISION",
        "macdsignal": "DOUBLE PRECISION",
        "macdhist": "DOUBLE PRECISION",
        "sma7": "DOUBLE PRECISION",
        "sma50": "DOUBLE PRECISION",
        "sma200": "DOUBLE PRECISION",
        "ema7": "DOUBLE PRECISION",
        "ema50": "DOUBLE PRECISION",
        "ema200": "DOUBLE PRECISION",
    },
}


def _table_columns(table_name):
    try:
        return TABLE_COLUMNS[table_name]
    except KeyError as error:
        raise ValueError(f"Table not allowed: {table_name}") from error


def get_latest_date(connection, table_name):
    _table_columns(table_name)
    query = sql.SQL("SELECT max(date) FROM {}.{}").format(
        sql.Identifier(BRONZE_SCHEMA), sql.Identifier(table_name)
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchone()[0]
    except errors.UndefinedTable:
        return None


class DbWriter:
    def __init__(self, connection, logger, table_name, pandas_df, run_id):
        self.connection = connection
        self.logger = logger
        self.table_name = table_name
        self.pandas_df = pandas_df
        self.run_id = run_id
        self.columns = _table_columns(table_name)

    def save_batch(self):
        if self.pandas_df.empty:
            return 0

        rows = self._rows()
        try:
            with self.connection.transaction():
                with self.connection.cursor() as cursor:
                    cursor.execute(
                        sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                            sql.Identifier(BRONZE_SCHEMA)
                        )
                    )
                    cursor.execute(self._create_table_query())
                    cursor.executemany(self._upsert_query(), rows)
        except Exception:
            self.logger.exception(
                "Failed to save batch to %s.%s",
                BRONZE_SCHEMA,
                self.table_name,
            )
            raise

        self.logger.info(
            "Saved %s rows to %s.%s",
            len(rows),
            BRONZE_SCHEMA,
            self.table_name,
        )
        return len(rows)

    def _rows(self):
        ingest_date_time = datetime.now(timezone.utc)
        rows = []
        for record in self.pandas_df.to_dict("records"):
            time = pd.Timestamp(record["time"]).to_pydatetime()
            values = [time.date(), time]
            values.extend(record[column] for column in tuple(self.columns)[1:])
            values.extend((ingest_date_time, self.run_id))
            rows.append(tuple(values))
        return rows

    def _create_table_query(self):
        source_columns = [
            sql.SQL("{} {}").format(sql.Identifier(name), sql.SQL(data_type))
            for name, data_type in self.columns.items()
        ]
        definitions = [sql.SQL("date DATE PRIMARY KEY"), *source_columns]
        definitions.extend(
            [
                sql.SQL("ingest_date_time TIMESTAMPTZ NOT NULL"),
                sql.SQL("run_id TEXT NOT NULL"),
            ]
        )
        return sql.SQL("CREATE TABLE IF NOT EXISTS {}.{} ({})").format(
            sql.Identifier(BRONZE_SCHEMA),
            sql.Identifier(self.table_name),
            sql.SQL(", ").join(definitions),
        )

    def _upsert_query(self):
        column_names = [
            "date",
            *self.columns,
            "ingest_date_time",
            "run_id",
        ]
        updates = [
            sql.SQL("{} = EXCLUDED.{}").format(
                sql.Identifier(column), sql.Identifier(column)
            )
            for column in column_names
            if column != "date"
        ]
        return sql.SQL(
            "INSERT INTO {}.{} ({}) VALUES ({}) "
            "ON CONFLICT (date) DO UPDATE SET {}"
        ).format(
            sql.Identifier(BRONZE_SCHEMA),
            sql.Identifier(self.table_name),
            sql.SQL(", ").join(map(sql.Identifier, column_names)),
            sql.SQL(", ").join(sql.Placeholder() * len(column_names)),
            sql.SQL(", ").join(updates),
        )
