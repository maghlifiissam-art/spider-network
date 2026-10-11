-- RIMAZ "visibility credit" (رصيد الظهور), user-approved 2026-10-11.
-- 3 boosts per channel (existing channels get 3 once via the column default),
-- each boost pins the video under admin pins for 48h. One active boost per channel,
-- one boost per video ever. Zero cost.
begin;
alter table public.channels add column if not exists boost_credits integer not null default 3 check(boost_credits>=0);
create table if not exists public.boosts (
 post_id uuid primary key references public.posts(id) on delete cascade,
 channel_id uuid not null references public.channels(id) on delete cascade,
 created_at timestamptz not null default now(),
 expires_at timestamptz not null
);
create index if not exists boosts_active_idx on public.boosts(expires_at);
alter table public.boosts enable row level security;
drop policy if exists "active boosts are readable" on public.boosts;
create policy "active boosts are readable" on public.boosts for select using (expires_at > now());
-- no insert/update/delete policies: writes only via boost_post()
create or replace function public.boost_post(p_post uuid) returns json
 security definer set search_path=public language plpgsql as $$
declare v_ch uuid; v_cr int;
begin
 if auth.uid() is null then return json_build_object('ok',false,'error','login'); end if;
 select c.id, c.boost_credits into v_ch, v_cr
   from public.posts p join public.channels c on c.id=p.channel_id
  where p.id=p_post and c.owner_id=auth.uid();
 if v_ch is null then return json_build_object('ok',false,'error','not your post'); end if;
 if v_cr<1 then return json_build_object('ok',false,'error','no credits'); end if;
 if exists(select 1 from public.boosts where post_id=p_post) then return json_build_object('ok',false,'error','already boosted'); end if;
 if exists(select 1 from public.boosts where channel_id=v_ch and expires_at>now()) then return json_build_object('ok',false,'error','boost already active'); end if;
 update public.channels set boost_credits=boost_credits-1 where id=v_ch;
 insert into public.boosts(post_id,channel_id,expires_at) values (p_post,v_ch,now()+interval '48 hours');
 return json_build_object('ok',true);
end $$;
commit;
