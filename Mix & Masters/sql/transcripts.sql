
CREATE TABLE IF NOT EXISTS transcripts (
    message_id BIGINT PRIMARY KEY,
    author_id BIGINT,
    channel_id BIGINT,
    category_id BIGINT,
    message_content TEXT,
    created_at TIMESTAMP
);
