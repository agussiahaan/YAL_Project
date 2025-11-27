-- admins
create table admins(
 id bigint generated always as identity primary key,
 username text,
 password text,
 created_at timestamp default now()
);
-- files
create table files(
 id bigint generated always as identity primary key,
 filename text,
 filepath text,
 public_url text,
 filesize bigint,
 uploaded_at timestamp default now(),
 source text
);
-- schedules
create table schedules(
 id bigint generated always as identity primary key,
 title text,
 description text,
 visibility text,
 file_id bigint,
 scheduled_at timestamp,
 duration_minutes int,
 looping boolean,
 stream_key text,
 rtmp_url text,
 status text,
 created_at timestamp default now()
);
-- history
create table history(
 id bigint generated always as identity primary key,
 schedule_id bigint,
 started_at timestamp,
 ended_at timestamp,
 duration int,
 status text,
 log text
);
