CREATE TABLE forecast.attempts (
    origin_week date NOT NULL,
    attempt_day date NOT NULL,
    started_at timestamptz NOT NULL,
    finished_at timestamptz,
    status text NOT NULL CHECK(status IN ('started','valid','delayed','failed')),
    error_type text,
    PRIMARY KEY(origin_week, attempt_day),
    CHECK (extract(isodow FROM origin_week) = 1),
    CHECK (attempt_day IN (origin_week + 7, origin_week + 8))
);
CREATE TABLE forecast.maintenance (
    artifact_prefix text PRIMARY KEY,
    rejected_at date,
    purged_at timestamptz
);
CREATE TABLE forecast.reports (
    version_id text NOT NULL REFERENCES forecast.versions(id),
    month date NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    report jsonb NOT NULL,
    PRIMARY KEY(version_id,month)
);
CREATE TABLE forecast.candidate_cycles (
    quarter date PRIMARY KEY,
    started_at timestamptz NOT NULL,
    snapshot_sha256 text NOT NULL
);
