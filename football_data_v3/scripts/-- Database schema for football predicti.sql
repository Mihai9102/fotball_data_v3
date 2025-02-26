-- Database schema for football predictions application

-- Drop tables if they exist
DROP TABLE IF EXISTS cote;
DROP TABLE IF EXISTS predictii;
DROP TABLE IF EXISTS meciuri;

-- Create tables
CREATE TABLE meciuri (
    id INTEGER PRIMARY KEY,
    league_id INTEGER NOT NULL,
    localteam_id INTEGER NOT NULL,
    visitorteam_id INTEGER NOT NULL,
    starting_at_timestamp TIMESTAMP NOT NULL,
    localteam_name VARCHAR(100),
    visitorteam_name VARCHAR(100),
    league_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE predictii (
    id SERIAL PRIMARY KEY,
    meci_id INTEGER NOT NULL,
    tip_predictie VARCHAR(50) NOT NULL,
    predictie VARCHAR(50) NOT NULL,
    probabilitate REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meci_id) REFERENCES meciuri(id),
    UNIQUE (meci_id, tip_predictie, predictie)
);

CREATE TABLE cote (
    id SERIAL PRIMARY KEY,
    meci_id INTEGER NOT NULL,
    bookmaker_id INTEGER NOT NULL,
    bookmaker_name VARCHAR(100),
    tip_pariu VARCHAR(100) NOT NULL,
    cota REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meci_id) REFERENCES meciuri(id),
    UNIQUE (meci_id, bookmaker_id, tip_pariu)
);

-- Indexes for better query performance
CREATE INDEX idx_predictii_meci_id ON predictii(meci_id);
CREATE INDEX idx_cote_meci_id ON cote(meci_id);
CREATE INDEX idx_meciuri_league_id ON meciuri(league_id);
CREATE INDEX idx_meciuri_date ON meciuri(starting_at_timestamp);
