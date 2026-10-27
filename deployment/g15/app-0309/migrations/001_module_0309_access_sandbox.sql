CREATE TABLE IF NOT EXISTS module_0309_sessions (
  id text PRIMARY KEY,
  owner_source text NOT NULL DEFAULT 'signed_teaching_session',
  created_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS module_0309_departments (
  id bigserial PRIMARY KEY, session_id text NOT NULL REFERENCES module_0309_sessions(id) ON DELETE CASCADE,
  name text NOT NULL, parent_id bigint, version integer NOT NULL DEFAULT 1, deleted_at timestamptz,
  UNIQUE(id,session_id), UNIQUE(session_id,name)
);
CREATE TABLE IF NOT EXISTS module_0309_users (
  id bigserial PRIMARY KEY, session_id text NOT NULL REFERENCES module_0309_sessions(id) ON DELETE CASCADE,
  username text NOT NULL, display_name text NOT NULL, department_id bigint NOT NULL,
  clearance integer NOT NULL CHECK(clearance BETWEEN 1 AND 4), enabled boolean NOT NULL DEFAULT true,
  version integer NOT NULL DEFAULT 1, deleted_at timestamptz,
  UNIQUE(id,session_id), UNIQUE(session_id,username),
  FOREIGN KEY(department_id,session_id) REFERENCES module_0309_departments(id,session_id)
);
ALTER TABLE module_0309_departments DROP CONSTRAINT IF EXISTS module_0309_departments_parent_owner_fk;
ALTER TABLE module_0309_departments ADD CONSTRAINT module_0309_departments_parent_owner_fk FOREIGN KEY(parent_id,session_id) REFERENCES module_0309_departments(id,session_id);

CREATE TABLE IF NOT EXISTS module_0309_permission_groups (
  id bigserial PRIMARY KEY, session_id text NOT NULL REFERENCES module_0309_sessions(id) ON DELETE CASCADE,
  name text NOT NULL, description text NOT NULL DEFAULT '', enabled boolean NOT NULL DEFAULT true,
  version integer NOT NULL DEFAULT 1, deleted_at timestamptz, UNIQUE(id,session_id), UNIQUE(session_id,name)
);
CREATE TABLE IF NOT EXISTS module_0309_user_permission_groups (
  session_id text NOT NULL REFERENCES module_0309_sessions(id) ON DELETE CASCADE,
  user_id bigint NOT NULL, group_id bigint NOT NULL, PRIMARY KEY(session_id,user_id,group_id),
  FOREIGN KEY(user_id,session_id) REFERENCES module_0309_users(id,session_id),
  FOREIGN KEY(group_id,session_id) REFERENCES module_0309_permission_groups(id,session_id)
);
CREATE TABLE IF NOT EXISTS module_0309_program_groups (
  id bigserial PRIMARY KEY, session_id text NOT NULL REFERENCES module_0309_sessions(id) ON DELETE CASCADE,
  name text NOT NULL, enabled boolean NOT NULL DEFAULT true, version integer NOT NULL DEFAULT 1,
  deleted_at timestamptz, UNIQUE(id,session_id), UNIQUE(session_id,name)
);
CREATE TABLE IF NOT EXISTS module_0309_programs (
  id bigserial PRIMARY KEY, session_id text NOT NULL REFERENCES module_0309_sessions(id) ON DELETE CASCADE,
  code text NOT NULL, name text NOT NULL, owner_user_id bigint NOT NULL, enabled boolean NOT NULL DEFAULT true,
  version integer NOT NULL DEFAULT 1, deleted_at timestamptz, UNIQUE(id,session_id), UNIQUE(session_id,code),
  FOREIGN KEY(owner_user_id,session_id) REFERENCES module_0309_users(id,session_id)
);
CREATE TABLE IF NOT EXISTS module_0309_program_group_members (
  session_id text NOT NULL REFERENCES module_0309_sessions(id) ON DELETE CASCADE,
  program_group_id bigint NOT NULL, program_id bigint NOT NULL, PRIMARY KEY(session_id,program_group_id,program_id),
  FOREIGN KEY(program_group_id,session_id) REFERENCES module_0309_program_groups(id,session_id),
  FOREIGN KEY(program_id,session_id) REFERENCES module_0309_programs(id,session_id)
);
CREATE TABLE IF NOT EXISTS module_0309_data_groups (
  id bigserial PRIMARY KEY, session_id text NOT NULL REFERENCES module_0309_sessions(id) ON DELETE CASCADE,
  name text NOT NULL, version integer NOT NULL DEFAULT 1, deleted_at timestamptz,
  UNIQUE(id,session_id), UNIQUE(session_id,name)
);
CREATE TABLE IF NOT EXISTS module_0309_user_data_groups (
  session_id text NOT NULL REFERENCES module_0309_sessions(id) ON DELETE CASCADE,
  user_id bigint NOT NULL, data_group_id bigint NOT NULL, PRIMARY KEY(session_id,user_id,data_group_id),
  FOREIGN KEY(user_id,session_id) REFERENCES module_0309_users(id,session_id),
  FOREIGN KEY(data_group_id,session_id) REFERENCES module_0309_data_groups(id,session_id)
);
CREATE TABLE IF NOT EXISTS module_0309_records (
  id bigserial PRIMARY KEY, session_id text NOT NULL REFERENCES module_0309_sessions(id) ON DELETE CASCADE,
  title text NOT NULL, owner_user_id bigint NOT NULL, department_id bigint NOT NULL, data_group_id bigint,
  classification integer NOT NULL CHECK(classification BETWEEN 1 AND 4), version integer NOT NULL DEFAULT 1,
  deleted_at timestamptz, UNIQUE(id,session_id),
  FOREIGN KEY(owner_user_id,session_id) REFERENCES module_0309_users(id,session_id),
  FOREIGN KEY(department_id,session_id) REFERENCES module_0309_departments(id,session_id),
  FOREIGN KEY(data_group_id,session_id) REFERENCES module_0309_data_groups(id,session_id)
);
CREATE TABLE IF NOT EXISTS module_0309_rules (
  id bigserial PRIMARY KEY, session_id text NOT NULL REFERENCES module_0309_sessions(id) ON DELETE CASCADE,
  name text NOT NULL, subject_type text NOT NULL CHECK(subject_type IN('user','permission_group')),
  subject_id bigint NOT NULL, resource_type text NOT NULL CHECK(resource_type IN('program','program_group')),
  resource_id bigint NOT NULL, action text NOT NULL CHECK(action IN('enter','view','edit','approve')),
  effect text NOT NULL CHECK(effect IN('allow','deny')),
  scope text NOT NULL CHECK(scope IN('self','department','department_tree','data_group','all')),
  scope_ref bigint, max_classification integer NOT NULL CHECK(max_classification BETWEEN 1 AND 4),
  active boolean NOT NULL DEFAULT true, starts_at timestamptz, ends_at timestamptz,
  version integer NOT NULL DEFAULT 1, deleted_at timestamptz, UNIQUE(id,session_id)
);
CREATE TABLE IF NOT EXISTS module_0309_audit_events (
  id bigserial PRIMARY KEY, session_id text NOT NULL REFERENCES module_0309_sessions(id) ON DELETE CASCADE,
  event_type text NOT NULL, entity_type text NOT NULL, entity_id bigint,
  detail jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS module_0309_users_owner_idx ON module_0309_users(session_id,deleted_at);
CREATE INDEX IF NOT EXISTS module_0309_records_owner_idx ON module_0309_records(session_id,deleted_at);
CREATE INDEX IF NOT EXISTS module_0309_rules_owner_idx ON module_0309_rules(session_id,active,deleted_at);
CREATE INDEX IF NOT EXISTS module_0309_audit_owner_idx ON module_0309_audit_events(session_id,created_at DESC);
