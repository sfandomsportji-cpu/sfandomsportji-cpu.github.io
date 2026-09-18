-- SFANDOM Community v1
-- Public schema only. Do not store secrets or production data in GitHub.
-- Target: PostgreSQL-compatible relational design.

create table if not exists community_channels (
  id bigserial primary key,
  slug varchar(64) not null unique,
  name varchar(120) not null,
  description text,
  sort_order integer not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists community_users (
  id bigserial primary key,
  public_handle varchar(48) not null unique,
  display_name varchar(80) not null,
  avatar_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists community_posts (
  id bigserial primary key,
  channel_id bigint not null references community_channels(id),
  author_id bigint references community_users(id),
  title varchar(180) not null,
  body text not null,
  media_url text,
  status varchar(24) not null default 'published',
  is_pinned boolean not null default false,
  view_count bigint not null default 0,
  comment_count integer not null default 0,
  reaction_count integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint community_posts_status_chk
    check (status in ('draft','published','hidden','deleted'))
);

create table if not exists community_comments (
  id bigserial primary key,
  post_id bigint not null references community_posts(id) on delete cascade,
  author_id bigint references community_users(id),
  parent_comment_id bigint references community_comments(id) on delete cascade,
  body text not null,
  status varchar(24) not null default 'published',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint community_comments_status_chk
    check (status in ('published','hidden','deleted'))
);

create table if not exists community_reactions (
  id bigserial primary key,
  post_id bigint references community_posts(id) on delete cascade,
  comment_id bigint references community_comments(id) on delete cascade,
  user_id bigint not null references community_users(id) on delete cascade,
  reaction_type varchar(24) not null default 'like',
  created_at timestamptz not null default now(),
  constraint community_reactions_target_chk
    check (
      (post_id is not null and comment_id is null)
      or
      (post_id is null and comment_id is not null)
    ),
  unique (post_id, user_id, reaction_type),
  unique (comment_id, user_id, reaction_type)
);

create table if not exists community_reports (
  id bigserial primary key,
  reporter_id bigint references community_users(id),
  post_id bigint references community_posts(id) on delete cascade,
  comment_id bigint references community_comments(id) on delete cascade,
  reason varchar(80) not null,
  detail text,
  status varchar(24) not null default 'open',
  created_at timestamptz not null default now(),
  reviewed_at timestamptz,
  constraint community_reports_target_chk
    check (
      (post_id is not null and comment_id is null)
      or
      (post_id is null and comment_id is not null)
    ),
  constraint community_reports_status_chk
    check (status in ('open','reviewing','resolved','dismissed'))
);

create index if not exists idx_community_posts_channel_created
  on community_posts(channel_id, created_at desc);

create index if not exists idx_community_comments_post_created
  on community_comments(post_id, created_at asc);

insert into community_channels (slug, name, description, sort_order)
values
  ('hot-talk', 'HOT TALK', 'Trending fan conversations', 10),
  ('match-chat', 'MATCH CHAT', 'Live and post-match discussion', 20),
  ('fan-picks', 'FAN PICKS', 'Fan selections and predictions', 30),
  ('video-lounge', 'VIDEO LOUNGE', 'Short-form sports video lounge', 40)
on conflict (slug) do nothing;
