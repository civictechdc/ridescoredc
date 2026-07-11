CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS survey_submissions (
    submission_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submitted_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    route_ogc_fids       INTEGER[] NOT NULL,
    time_of_day          VARCHAR(20),
    overall_satisfaction INTEGER CHECK (overall_satisfaction BETWEEN 1 AND 5),
    would_ride_again     VARCHAR(20),
    trip_purpose         VARCHAR(30),
    comments             TEXT
);

-- Migrate existing installs: drop removed columns, add new ones
ALTER TABLE survey_submissions DROP COLUMN IF EXISTS map_lts_calibration;
ALTER TABLE survey_submissions DROP COLUMN IF EXISTS traffic_volume;
ALTER TABLE survey_submissions ADD COLUMN IF NOT EXISTS overall_satisfaction INTEGER CHECK (overall_satisfaction BETWEEN 1 AND 5);
ALTER TABLE survey_submissions ADD COLUMN IF NOT EXISTS would_ride_again     VARCHAR(20);
ALTER TABLE survey_submissions ADD COLUMN IF NOT EXISTS trip_purpose         VARCHAR(30);

CREATE TABLE IF NOT EXISTS survey_contiguous_segments (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id    UUID NOT NULL REFERENCES survey_submissions(submission_id) ON DELETE CASCADE,
    sequence_index   INTEGER NOT NULL,
    route_name       VARCHAR,
    ogc_fids         INTEGER[] NOT NULL,
    lts_perceived    INTEGER CHECK (lts_perceived BETWEEN 1 AND 4),
    safety_rating    INTEGER CHECK (safety_rating BETWEEN 1 AND 10),
    stress_factors   TEXT[]
);

CREATE TABLE IF NOT EXISTS survey_granular_segments (
    submission_id          UUID NOT NULL REFERENCES survey_submissions(submission_id) ON DELETE CASCADE,
    ogc_fid                INTEGER NOT NULL,
    contiguous_segment_id  UUID NOT NULL REFERENCES survey_contiguous_segments(id) ON DELETE CASCADE,
    sequence_index         INTEGER NOT NULL,
    PRIMARY KEY (submission_id, ogc_fid)
);

CREATE INDEX IF NOT EXISTS idx_survey_contiguous_submission
    ON survey_contiguous_segments(submission_id);
CREATE INDEX IF NOT EXISTS idx_survey_granular_submission
    ON survey_granular_segments(submission_id);
CREATE INDEX IF NOT EXISTS idx_survey_granular_ogc_fid
    ON survey_granular_segments(ogc_fid);
