CREATE SCHEMA IF NOT EXISTS forecast;
CREATE TABLE forecast.versions (
    id text PRIMARY KEY,
    manifest jsonb NOT NULL,
    artifact_prefix text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    withdrawn boolean NOT NULL DEFAULT false
);
CREATE TABLE forecast.publication (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    active_version text REFERENCES forecast.versions(id),
    rollback_version text REFERENCES forecast.versions(id)
);
INSERT INTO forecast.publication(singleton) VALUES (true);
CREATE TABLE forecast.emissions (
    id text PRIMARY KEY,
    version_id text NOT NULL REFERENCES forecast.versions(id),
    origin_week date NOT NULL UNIQUE,
    emission_date date NOT NULL,
    created_at timestamptz NOT NULL,
    status text NOT NULL CHECK(status IN ('valid','delayed','invalidated')),
    payload jsonb NOT NULL
);
CREATE TABLE forecast.scores (
    emission_id text NOT NULL REFERENCES forecast.emissions(id),
    horizon integer NOT NULL CHECK(horizon BETWEEN 1 AND 52),
    observation_revision text NOT NULL,
    observed double precision NOT NULL CHECK(observed > 0 AND observed < 'Infinity'),
    metrics jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(emission_id,horizon,observation_revision)
);
CREATE FUNCTION forecast.keep_original() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Forecast history is permanent'; END IF;
    IF TG_TABLE_NAME = 'emissions' AND
       (to_jsonb(NEW) - 'status') = (to_jsonb(OLD) - 'status') THEN RETURN NEW; END IF;
    IF TG_TABLE_NAME = 'versions' AND
       (to_jsonb(NEW) - 'withdrawn') = (to_jsonb(OLD) - 'withdrawn') THEN RETURN NEW; END IF;
    RAISE EXCEPTION 'Forecast original values are immutable';
END $$;
CREATE TRIGGER immutable_emissions BEFORE UPDATE OR DELETE ON forecast.emissions FOR EACH ROW EXECUTE FUNCTION forecast.keep_original();
CREATE TRIGGER immutable_scores BEFORE UPDATE OR DELETE ON forecast.scores FOR EACH ROW EXECUTE FUNCTION forecast.keep_original();
CREATE TRIGGER immutable_versions BEFORE UPDATE OR DELETE ON forecast.versions FOR EACH ROW EXECUTE FUNCTION forecast.keep_original();
