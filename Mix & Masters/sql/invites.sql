
CREATE TABLE IF NOT EXISTS invites (
    guild_id BIGINT,
    code TEXT PRIMARY KEY,
    uses SMALLINT,
    max_uses SMALLINT,
    users JSONB,
    inviter BIGINT
);
