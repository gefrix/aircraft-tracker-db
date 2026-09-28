CREATE TABLE IF NOT EXISTS countries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    south_latitude DOUBLE PRECISION NOT NULL,
    north_latitude DOUBLE PRECISION NOT NULL,
    west_longitude DOUBLE PRECISION NOT NULL,
    east_longitude DOUBLE PRECISION NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_latitude_bounds CHECK (south_latitude <= north_latitude),
    CONSTRAINT valid_longitude_bounds CHECK (west_longitude <= east_longitude)
);

CREATE TABLE IF NOT EXISTS aeroplanes (
    country_id INTEGER NOT NULL REFERENCES countries(id) ON DELETE CASCADE,
    icao24 VARCHAR(6) NOT NULL,
    callsign VARCHAR(32) NOT NULL,
    origin_country VARCHAR(100) NOT NULL,
    velocity DOUBLE PRECISION,
    altitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    on_ground BOOLEAN NOT NULL DEFAULT FALSE,
    last_contact BIGINT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (country_id, icao24),
    CONSTRAINT non_negative_velocity CHECK (velocity IS NULL OR velocity >= 0)
);

CREATE INDEX IF NOT EXISTS idx_aeroplanes_velocity ON aeroplanes (velocity);
CREATE INDEX IF NOT EXISTS idx_aeroplanes_callsign_lower ON aeroplanes (LOWER(callsign));
CREATE INDEX IF NOT EXISTS idx_aeroplanes_origin_country ON aeroplanes (origin_country);

