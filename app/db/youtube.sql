CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE SCHEMA IF NOT EXISTS "youtube";

CREATE TABLE IF NOT EXISTS youtube.channels (
    channel_id VARCHAR PRIMARY KEY,
    id VARCHAR NOT NULL UNIQUE,
    channel VARCHAR NOT NULL,
    title VARCHAR,
    description TEXT,
    channel_url VARCHAR NOT NULL UNIQUE,
    channel_follower_count INTEGER,
    tags TEXT[],
    banner_path VARCHAR,
    avatar_path VARCHAR
);

CREATE TABLE IF NOT EXISTS youtube.videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id VARCHAR NOT NULL UNIQUE,
    channel_id VARCHAR REFERENCES youtube.channels(channel_id) ON DELETE CASCADE,
    title VARCHAR NOT NULL,
    description TEXT,
    duration INTEGER NOT NULL,
    view_count INTEGER,
    upload_date TIMESTAMP,
    video_path VARCHAR,
    is_downloaded BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS youtube.tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS youtube.video_tags (
    video_id UUID REFERENCES youtube.videos(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES youtube.tags(id) ON DELETE CASCADE,
    PRIMARY KEY (video_id, tag_id)
);

CREATE TABLE IF NOT EXISTS youtube.thumbnails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES youtube.videos(id) ON DELETE CASCADE,
    url VARCHAR NOT NULL,
    width INTEGER,
    height INTEGER,
    thumbnail_path VARCHAR,
    CONSTRAINT uix_thumbnail_url UNIQUE (url)
);
