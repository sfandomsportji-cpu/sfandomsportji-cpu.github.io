-- 경기별 한 줄 투표 (Supabase SQL Editor에서 한 번 실행)
create table if not exists public.game_votes (
  id bigint generated always as identity primary key,
  game_id text not null check (game_id ~ '^[a-z0-9-]{3,120}$'),
  side text not null check (side in ('away','home')),
  voter text not null check (char_length(voter) between 8 and 64),
  created_at timestamptz not null default now(),
  unique (game_id, voter)
);
alter table public.game_votes enable row level security;
drop policy if exists "anon can vote" on public.game_votes;
create policy "anon can vote" on public.game_votes for insert to anon with check (true);
-- 표 자체는 읽지 못하고, 집계 뷰만 읽을 수 있다
create or replace view public.game_vote_counts as
  select game_id, side, count(*)::int as votes from public.game_votes group by game_id, side;
grant select on public.game_vote_counts to anon;
grant insert on public.game_votes to anon;
