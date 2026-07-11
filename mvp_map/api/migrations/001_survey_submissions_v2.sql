-- Migration: 001_survey_submissions_v2
-- Applied: run once against production database
-- Removes map calibration and traffic volume columns from the route survey,
-- and adds overall satisfaction, ride-again intent, and trip purpose.

BEGIN;

ALTER TABLE survey_submissions
    DROP COLUMN IF EXISTS map_lts_calibration,
    DROP COLUMN IF EXISTS traffic_volume;

ALTER TABLE survey_submissions
    ADD COLUMN IF NOT EXISTS overall_satisfaction INTEGER
        CHECK (overall_satisfaction BETWEEN 1 AND 5),
    ADD COLUMN IF NOT EXISTS would_ride_again     VARCHAR(20),
    ADD COLUMN IF NOT EXISTS trip_purpose         VARCHAR(30);

COMMIT;
