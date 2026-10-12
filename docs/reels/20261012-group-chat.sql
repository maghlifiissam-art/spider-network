-- 2026-10-12: group text chat + open/closed join rules
-- groups.is_closed already exists (default true). Closed groups: admin adds members.
-- Open groups: any signed-in user joins instantly.

create table if not exists public.group_messages (
  id bigint generated always as identity primary key,
  group_id uuid not null references public.groups(id) on delete cascade,
  user_id uuid not null default auth.uid(),
  body text not null check (char_length(body) between 1 and 1000),
  created_at timestamptz not null default now()
);
create index if not exists group_messages_group_created on public.group_messages(group_id, created_at);
alter table public.group_messages enable row level security;
grant select, insert on public.group_messages to authenticated;

create or replace function public.is_group_member(g uuid) returns boolean
language sql security definer stable set search_path = public as $$
  select exists(select 1 from memberships where group_id = g and user_id = auth.uid() and status = 'approved')
$$;

create policy "members read group messages" on public.group_messages
  for select to authenticated using (is_group_member(group_id));

create policy "members send group messages" on public.group_messages
  for insert to authenticated with check (
    user_id = auth.uid()
    and is_group_member(group_id)
    and (select count(*) from group_messages gm
         where gm.user_id = auth.uid() and gm.created_at > now() - interval '1 minute') < 20
  );

-- open groups: instant self-join as approved member
create policy "join open group" on public.memberships
  for insert to public with check (
    user_id = auth.uid() and status = 'approved' and member_role = 'member'
    and exists(select 1 from groups g where g.id = group_id and not g.is_closed)
  );

-- closed groups: group admins add members directly
create policy "group admin adds member" on public.memberships
  for insert to public with check (is_group_admin(group_id));
