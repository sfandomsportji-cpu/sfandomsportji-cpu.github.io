-- SFANDOM Community DB V1
-- Code/schema only. Live data belongs in the cloud database.

create extension if not exists pgcrypto;

create table if not exists public.posts (
  id uuid primary key default gen_random_uuid(),
  category text not null default 'lounge'
    check (category in ('nba','football','baseball','lounge')),
  title text not null check (char_length(trim(title)) between 1 and 120),
  body text not null check (char_length(trim(body)) between 1 and 5000),
  nickname text not null check (char_length(trim(nickname)) between 1 and 30),
  status text not null default 'published'
    check (status in ('published','hidden','deleted')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.comments (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references public.posts(id) on delete cascade,
  body text not null check (char_length(trim(body)) between 1 and 2000),
  nickname text not null check (char_length(trim(nickname)) between 1 and 30),
  status text not null default 'published'
    check (status in ('published','hidden','deleted')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists posts_created_at_idx
  on public.posts (created_at desc);

create index if not exists posts_category_created_at_idx
  on public.posts (category, created_at desc);

create index if not exists comments_post_created_at_idx
  on public.comments (post_id, created_at asc);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists posts_set_updated_at on public.posts;
create trigger posts_set_updated_at
before update on public.posts
for each row execute function public.set_updated_at();

drop trigger if exists comments_set_updated_at on public.comments;
create trigger comments_set_updated_at
before update on public.comments
for each row execute function public.set_updated_at();

-- Public prototype policy:
-- browser clients may read published rows and insert valid rows only.
-- update/delete are intentionally disabled until auth/moderation is added.

alter table public.posts enable row level security;
alter table public.comments enable row level security;

drop policy if exists "public_read_posts" on public.posts;
create policy "public_read_posts"
on public.posts for select
using (status = 'published');

drop policy if exists "public_insert_posts" on public.posts;
create policy "public_insert_posts"
on public.posts for insert
with check (
  status = 'published'
  and char_length(trim(title)) between 1 and 120
  and char_length(trim(body)) between 1 and 5000
  and char_length(trim(nickname)) between 1 and 30
);

drop policy if exists "public_read_comments" on public.comments;
create policy "public_read_comments"
on public.comments for select
using (status = 'published');

drop policy if exists "public_insert_comments" on public.comments;
create policy "public_insert_comments"
on public.comments for insert
with check (
  status = 'published'
  and char_length(trim(body)) between 1 and 2000
  and char_length(trim(nickname)) between 1 and 30
);
