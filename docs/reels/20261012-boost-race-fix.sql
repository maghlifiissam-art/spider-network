-- boost race + grants hardening (code-review 2026-10-12).
-- 1) boost_post: serialize on the channel row (FOR UPDATE) + guarded decrement.
-- 2) trigger guard: boost_credits can only change from boost_post (transaction-local setting),
--    so the existing "edit own channel" UPDATE policy cannot refill credits.
begin;
create or replace function public.boost_post(p_post uuid) returns json
 security definer set search_path=public language plpgsql as $$
declare v_ch uuid; v_cr int;
begin
 if auth.uid() is null then return json_build_object('ok',false,'error','login'); end if;
 select c.id into v_ch from public.posts p join public.channels c on c.id=p.channel_id
  where p.id=p_post and c.owner_id=auth.uid();
 if v_ch is null then return json_build_object('ok',false,'error','not your post'); end if;
 -- serialize concurrent boosts of this channel on its row
 select boost_credits into v_cr from public.channels where id=v_ch for update;
 if v_cr<1 then return json_build_object('ok',false,'error','no credits'); end if;
 if exists(select 1 from public.boosts where post_id=p_post) then return json_build_object('ok',false,'error','already boosted'); end if;
 if exists(select 1 from public.boosts where channel_id=v_ch and expires_at>now()) then return json_build_object('ok',false,'error','boost already active'); end if;
 perform set_config('rimaz.boost_write','on',true);
 update public.channels set boost_credits=boost_credits-1 where id=v_ch and boost_credits>=1 returning boost_credits into v_cr;
 if not found then return json_build_object('ok',false,'error','no credits'); end if;
 insert into public.boosts(post_id,channel_id,expires_at) values (p_post,v_ch,now()+interval '48 hours');
 return json_build_object('ok',true);
end $$;
create or replace function public.guard_boost_credits() returns trigger language plpgsql as $$
begin
  if new.boost_credits is distinct from old.boost_credits
     and coalesce(current_setting('rimaz.boost_write', true),'') <> 'on' then
    raise exception 'boost_credits is managed by the platform';
  end if;
  return new;
end $$;
drop trigger if exists trg_guard_boost_credits on public.channels;
create trigger trg_guard_boost_credits before update on public.channels
  for each row execute function public.guard_boost_credits();
commit;
-- for manual admin credit changes in the SQL editor: run
--   select set_config('rimaz.boost_write','on',false);
-- in the same query batch as the UPDATE.
