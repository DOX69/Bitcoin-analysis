drop schema if exists bronze cascade;
create schema bronze;

create table bronze.btc_usd_ohlcv (
    time timestamp without time zone not null,
    low double precision not null,
    high double precision not null,
    open double precision not null,
    close double precision not null,
    volume double precision not null,
    date date not null,
    ingest_date_time timestamp without time zone not null
);

create table bronze.eth_usd_ohlcv (like bronze.btc_usd_ohlcv);

insert into bronze.btc_usd_ohlcv values
    ('2024-01-01 00:00:00', 90, 110, 95, 105, 9, '2024-01-01', '2024-01-01 01:00:00'),
    ('2024-01-01 00:00:00', 100, 120, 110, 115, 10, '2024-01-01', '2024-01-01 02:00:00'),
    ('2024-01-02 00:00:00', 110, 130, 115, 125, 11, '2024-01-02', '2024-01-02 02:00:00'),
    ('2024-01-08 00:00:00', 120, 140, 125, 135, 12, '2024-01-08', '2024-01-08 02:00:00'),
    ('2024-02-01 00:00:00', 130, 150, 135, 145, 13, '2024-02-01', '2024-02-01 02:00:00'),
    ('2024-12-30 00:00:00', 200, 260, 250, 240, 14, '2024-12-30', '2024-12-30 02:00:00'),
    ('2024-12-31 00:00:00', 180, 280, 240, 210, 15, '2024-12-31', '2024-12-31 02:00:00'),
    ('2025-01-01 00:00:00', 300, 360, 310, 350, 16, '2025-01-01', '2025-01-01 02:00:00'),
    ('2025-01-05 00:00:00', 290, 390, 350, 380, 17, '2025-01-05', '2025-01-05 02:00:00');

create table bronze.usd_chf_rates (
    time timestamp without time zone not null,
    rate double precision not null,
    date date not null,
    ingest_date_time timestamp without time zone not null
);

create table bronze.usd_eur_rates (like bronze.usd_chf_rates);

insert into bronze.usd_chf_rates values
    ('2024-01-01', 0.80, '2024-01-01', '2024-01-01 01:00:00'),
    ('2024-01-01', 0.90, '2024-01-01', '2024-01-01 02:00:00'),
    ('2024-01-03', 0.92, '2024-01-03', '2024-01-03 02:00:00'),
    ('2024-02-01', 0.95, '2024-02-01', '2024-02-01 02:00:00');

insert into bronze.usd_eur_rates values
    ('2024-01-01', 0.94, '2024-01-01', '2024-01-01 01:00:00'),
    ('2024-01-01', 0.95, '2024-01-01', '2024-01-01 02:00:00'),
    ('2024-01-02', 0.96, '2024-01-02', '2024-01-02 02:00:00'),
    ('2024-02-01', 0.98, '2024-02-01', '2024-02-01 02:00:00');

create table bronze.bgeometrics_btc_technical_indicators (
    d date not null,
    "unixTs" text not null,
    rsi double precision not null,
    macd double precision not null,
    macdsignal double precision not null,
    macdhist double precision not null,
    sma7 double precision not null,
    sma50 double precision not null,
    sma200 double precision not null,
    ema7 double precision not null,
    ema50 double precision not null,
    ema200 double precision not null,
    ingest_date_time timestamp without time zone not null
);

insert into bronze.bgeometrics_btc_technical_indicators values
    ('2024-01-01', '1', 40, 1, 2, 3, 4, 5, 6, 7, 8, 9, '2024-01-01 01:00:00'),
    ('2024-01-01', '1', 40, 10, 11, 12, 13, 14, 15, 16, 17, 18, '2024-01-01 02:00:00'),
    ('2024-01-08', '8', 50, 20, 21, 22, 23, 24, 25, 26, 27, 28, '2024-01-08 02:00:00'),
    ('2024-02-01', '32', 60, 30, 31, 32, 33, 34, 35, 36, 37, 38, '2024-02-01 02:00:00');
