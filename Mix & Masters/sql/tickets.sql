
CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    price INTEGER,
    category_id BIGINT,
    created_at TIMESTAMP,
    active BOOLEAN,
    extra_packages TEXT[],
    information_embed_id BIGINT
);

-- ALTER TABLE tickets ADD COLUMN extra_packages TEXT[];
-- ALTER TABLE tickets ADD COLUMN information_embed_id BIGINT;