-- RIMAZ counter hardening. No paid serving or payment collection.
begin;
create table if not exists public.view_receipts (
 actor text not null check(length(actor)=43), kind text not null check(kind in ('video','ad')),
 target uuid not null, accepted_at timestamptz not null, ad_day date,
 primary key(actor,kind,target)
);
create table if not exists public.view_budgets (
 scope text primary key, window_start timestamptz not null, requests integer not null check(requests>=0)
);
alter table public.view_receipts enable row level security;
alter table public.view_budgets enable row level security;
revoke all on public.view_receipts, public.view_budgets from public,anon,authenticated,service_role;
create table if not exists public.ad_budget (
 ad_id uuid primary key references public.ads(id) on delete cascade,
 advertiser_user_id uuid references auth.users(id), currency text not null default 'USD' check(currency='USD'),
 funded_microusd bigint not null default 0 check(funded_microusd=0),
 spent_microusd bigint not null default 0 check(spent_microusd=0),
 unit_price_microusd integer not null default 1000 check(unit_price_microusd=1000),
 state text not null default 'free' check(state in ('free','paused'))
);
-- Funding is deliberately disabled by constraints, not just by absent UI.
create table if not exists public.ad_funding_receipts (
 provider_transaction_id text primary key,
 ad_id uuid not null references public.ad_budget(ad_id),
 amount_microusd bigint not null check(amount_microusd>0),
 currency text not null check(currency='USD'), verified_at timestamptz not null
);
alter table public.ad_budget enable row level security;
alter table public.ad_funding_receipts enable row level security;
revoke all on public.ad_budget, public.ad_funding_receipts from public,anon,authenticated,service_role;
insert into public.ad_budget(ad_id) select id from public.ads on conflict do nothing;
create or replace function public.view_budget_take(s text, lim integer)
returns boolean language plpgsql security definer set search_path=pg_catalog as $$
declare n integer; t timestamptz:=clock_timestamp();
begin
 if s is null or length(s)>100 or lim<1 or lim>6000 then raise exception 'invalid budget'; end if;
 insert into public.view_budgets(scope,window_start,requests) values(s,t,1)
 on conflict(scope) do update set
 requests=case when public.view_budgets.window_start<=t-interval '60 seconds' then 1 else least(public.view_budgets.requests+1,lim+1) end,
 window_start=case when public.view_budgets.window_start<=t-interval '60 seconds' then t else public.view_budgets.window_start end
 returning requests into n;
 return n<=lim;
end $$;
revoke all on function public.view_budget_take(text,integer) from public,anon,authenticated,service_role;
create or replace function public.view_token_budget()
returns boolean language plpgsql security definer set search_path=pg_catalog as $$
begin
 if auth.role() is distinct from 'service_role' then raise exception 'not allowed'; end if;
 return public.view_budget_take('visitor_issue',600);
end $$;
revoke all on function public.view_token_budget() from public,anon,authenticated;
grant execute on function public.view_token_budget() to service_role;
create or replace function public.record_view(k text,tgt uuid,actor_key text)
returns text language plpgsql security definer set search_path=pg_catalog as $$
declare t timestamptz:=clock_timestamp(); d date; r public.view_receipts%rowtype; v bigint;
begin
 if auth.role() is distinct from 'service_role' then raise exception 'not allowed'; end if;
 if k not in ('video','ad') or k is null or tgt is null or actor_key is null or actor_key !~ '^[A-Za-z0-9_-]{43}$' then return 'invalid'; end if;
 if not public.view_budget_take('all_views',6000) then return 'limited'; end if;
 if not public.view_budget_take('actor:'||actor_key,120) then return 'limited'; end if;
 d:=(t at time zone 'Africa/Casablanca')::date;
 if k='video' then
   if not exists(select 1 from public.posts where id=tgt) then return 'missing'; end if;
 else
   if not exists(select 1 from public.ads where id=tgt and active and views<500) then return 'capped'; end if;
 end if;
 -- Transaction-scoped advisory lock serializes receipts, including first insert.
 perform pg_advisory_xact_lock(hashtextextended(actor_key||':'||k||':'||tgt::text,0));
 select * into r from public.view_receipts where actor=actor_key and kind=k and target=tgt;
 if found and ((k='video' and r.accepted_at>t-interval '1 hour') or (k='ad' and r.ad_day=d)) then return 'duplicate'; end if;
 if k='video' then
   update public.posts set views=views+1 where id=tgt returning views into v;
   if not found then return 'missing'; end if;
   insert into public.view_daily(day,views) values(d,1) on conflict(day) do update set views=public.view_daily.views+1;
 else
   update public.ads set views=views+1 where id=tgt and active and views<500 returning views into v;
   if not found then return 'capped'; end if;
 end if;
 insert into public.view_receipts(actor,kind,target,accepted_at,ad_day) values(actor_key,k,tgt,t,d)
 on conflict(actor,kind,target) do update set accepted_at=excluded.accepted_at,ad_day=excluded.ad_day;
 -- Bounded cleanup never removes a live hourly/day dedup window.
 delete from public.view_receipts where ctid in (select ctid from public.view_receipts where accepted_at<t-interval '32 days' limit 100);
 delete from public.view_budgets where scope in (select scope from public.view_budgets where window_start<t-interval '2 days' limit 100);
 return 'accepted';
end $$;
revoke all on function public.record_view(text,uuid,text) from public,anon,authenticated;
grant execute on function public.record_view(text,uuid,text) to service_role;
commit;
-- Old RPC revocation is a separate final cutover after endpoint/client verification.
create or replace function public.protect_view_count()
returns trigger language plpgsql set search_path=pg_catalog as $$
begin
 if new.views is distinct from old.views and auth.role() in ('anon','authenticated') then
   raise exception 'view counter is server managed';
 end if;
 return new;
end $$;
revoke all on function public.protect_view_count() from public,anon,authenticated;
create trigger rimaz_protect_post_views before update on public.posts
 for each row execute function public.protect_view_count();
create trigger rimaz_protect_ad_views before update on public.ads
 for each row execute function public.protect_view_count();
revoke execute on function public.bump_view(uuid), public.ad_view(uuid) from public,anon,authenticated;
