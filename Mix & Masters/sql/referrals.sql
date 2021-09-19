
CREATE TABLE IF NOT EXISTS referrals (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    referred_id BIGINT,
    reffered_at TIMESTAMP
)
