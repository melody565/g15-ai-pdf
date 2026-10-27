CREATE TABLE IF NOT EXISTS module_0308_sessions (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS module_0308_applications (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES module_0308_sessions(id) ON DELETE CASCADE,
    username VARCHAR(32) NOT NULL,
    full_name VARCHAR(60) NOT NULL,
    email VARCHAR(254) NOT NULL DEFAULT '',
    phone VARCHAR(32) NOT NULL DEFAULT '',
    organization VARCHAR(120) NOT NULL,
    title VARCHAR(80) NOT NULL,
    requested_role VARCHAR(30) NOT NULL,
    purpose VARCHAR(1000) NOT NULL,
    contact_method VARCHAR(10) NOT NULL,
    password_hash TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending_contact',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT module_0308_contact_method_valid CHECK(contact_method IN ('email','sms')),
    CONSTRAINT module_0308_application_status_valid CHECK(status IN ('pending_contact','pending_review','changes_requested','rejected','approved')),
    CONSTRAINT module_0308_application_version_valid CHECK(version > 0)
);
CREATE UNIQUE INDEX IF NOT EXISTS module_0308_session_username_unique ON module_0308_applications(session_id, LOWER(username));
CREATE INDEX IF NOT EXISTS module_0308_app_session_updated_idx ON module_0308_applications(session_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS module_0308_deliveries (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES module_0308_sessions(id) ON DELETE CASCADE,
    application_id BIGINT NOT NULL REFERENCES module_0308_applications(id) ON DELETE CASCADE,
    channel VARCHAR(10) NOT NULL,
    destination_masked VARCHAR(254) NOT NULL,
    delivery_status VARCHAR(30) NOT NULL,
    code_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    attempts SMALLINT NOT NULL DEFAULT 0,
    resend_available_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verified_at TIMESTAMPTZ,
    CONSTRAINT module_0308_delivery_channel_valid CHECK(channel IN ('email','sms')),
    CONSTRAINT module_0308_delivery_status_valid CHECK(delivery_status IN ('simulated_ready','simulated_failed','verified','expired','superseded')),
    CONSTRAINT module_0308_delivery_attempts_valid CHECK(attempts BETWEEN 0 AND 5)
);
CREATE INDEX IF NOT EXISTS module_0308_delivery_session_idx ON module_0308_deliveries(session_id, created_at DESC);

CREATE TABLE IF NOT EXISTS module_0308_users (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES module_0308_sessions(id) ON DELETE CASCADE,
    application_id BIGINT NOT NULL UNIQUE REFERENCES module_0308_applications(id) ON DELETE CASCADE,
    username VARCHAR(32) NOT NULL,
    display_name VARCHAR(60) NOT NULL,
    sandbox_role VARCHAR(30) NOT NULL,
    password_hash TEXT NOT NULL,
    user_status VARCHAR(20) NOT NULL DEFAULT 'active',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT module_0308_user_status_valid CHECK(user_status IN ('active','disabled')),
    CONSTRAINT module_0308_user_version_valid CHECK(version > 0)
);
CREATE UNIQUE INDEX IF NOT EXISTS module_0308_user_session_username_unique ON module_0308_users(session_id, LOWER(username));

CREATE TABLE IF NOT EXISTS module_0308_audit_events (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES module_0308_sessions(id) ON DELETE CASCADE,
    entity_type VARCHAR(30) NOT NULL,
    entity_id BIGINT,
    event_type VARCHAR(50) NOT NULL,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS module_0308_audit_session_idx ON module_0308_audit_events(session_id, created_at DESC);

