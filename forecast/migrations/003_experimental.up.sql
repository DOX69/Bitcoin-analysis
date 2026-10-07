CREATE SCHEMA IF NOT EXISTS forecast_experimental;
CREATE TABLE IF NOT EXISTS forecast_experimental.emissions (
    origin_week date PRIMARY KEY,
    emission_date date NOT NULL,
    model_sha256 text NOT NULL CHECK (model_sha256 ~ '^[a-f0-9]{64}$'),
    source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[a-f0-9]{64}$'),
    payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[a-f0-9]{64}$'),
    payload jsonb NOT NULL,
    published_at timestamptz NOT NULL DEFAULT now()
);
