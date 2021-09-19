
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    ticket_id BIGINT,
    created_at TIMESTAMP
);
