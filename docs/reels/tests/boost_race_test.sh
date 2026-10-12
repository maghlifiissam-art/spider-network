#!/usr/bin/env bash
# boost_post race regression test (code-review 2026-10-12).
# Proves: with boost_credits=1, two concurrent boosts on DIFFERENT posts of the
# same channel yield exactly one ok:true, one boost row, credits==0 (never -1).
# Also proves the owner cannot refill boost_credits directly (trigger guard).
#
# Usage:
#   RIMAZ_JWT=<owner user jwt> RIMAZ_UID=<owner uuid> \
#   [RIMAZ_BASE=https://eyasbfywyatrkpkljxek.supabase.co] \
#   [RIMAZ_KEY=sb_publishable_...] bash boost_race_test.sh
#
# Needs an admin to pre-set credits=1 on the created channel (SQL editor:
#   select set_config('rimaz.boost_write','on',false);
#   update public.channels set boost_credits=1 where id='<channel>';
# ) OR run with RIMAZ_ADMIN_SQL=1 against a local psql. Cleanup is manual if run fails midway.
set -u
BASE="${RIMAZ_BASE:-https://eyasbfywyatrkpkljxek.supabase.co}/rest/v1"
KEY="${RIMAZ_KEY:?publishable key required}"
JWT="${RIMAZ_JWT:?owner jwt required}"
UIDC="${RIMAZ_UID:?owner uuid required}"
H=(-H "apikey: $KEY" -H "Authorization: Bearer $JWT" -H 'Content-Type: application/json')
fail(){ echo "FAIL: $*"; exit 1; }

CH=$(curl -s -X POST "$BASE/channels" "${H[@]}" -H 'Prefer: return=representation' \
  -d "{\"owner_id\":\"$UIDC\",\"handle\":\"boosttest$RANDOM\",\"name\":\"boost-race-test\"}" | jq -r '.[0].id')
[ "$CH" = null ] && fail "channel create"
echo "channel=$CH"

# Q2 guard: owner refill must be blocked by trg_guard_boost_credits
MSG=$(curl -s -X PATCH "$BASE/channels?id=eq.$CH" "${H[@]}" -d '{"boost_credits":5}' | jq -r '.message // "NO-ERROR"')
[ "$MSG" = "boost_credits is managed by the platform" ] || fail "refill NOT blocked: $MSG"
echo "refill blocked OK"

P1=$(curl -s -X POST "$BASE/posts" "${H[@]}" -H 'Prefer: return=representation' \
  -d "{\"owner_id\":\"$UIDC\",\"channel_id\":\"$CH\",\"kind\":\"video\",\"media_url\":\"https://eyasbfywyatrkpkljxek.supabase.co/storage/v1/object/public/media/qa/race-1.mp4\"}" | jq -r '.[0].id')
P2=$(curl -s -X POST "$BASE/posts" "${H[@]}" -H 'Prefer: return=representation' \
  -d "{\"owner_id\":\"$UIDC\",\"channel_id\":\"$CH\",\"kind\":\"video\",\"media_url\":\"https://eyasbfywyatrkpkljxek.supabase.co/storage/v1/object/public/media/qa/race-2.mp4\"}" | jq -r '.[0].id')
[ "$P1" = null -o "$P2" = null ] && fail "post create"
echo "posts=$P1,$P2  -- NOW set boost_credits=1 via admin, then press enter"; read -r _

curl -s -X POST "$BASE/rpc/boost_post" "${H[@]}" -d "{\"p_post\":\"$P1\"}" > /tmp/race1.json &
curl -s -X POST "$BASE/rpc/boost_post" "${H[@]}" -d "{\"p_post\":\"$P2\"}" > /tmp/race2.json &
wait
OKS=$(cat /tmp/race1.json /tmp/race2.json | jq -s 'map(select(.ok==true)) | length')
CR=$(curl -s "$BASE/channels?id=eq.$CH&select=boost_credits" "${H[@]}" | jq -r '.[0].boost_credits')
N=$(curl -s "$BASE/boosts?channel_id=eq.$CH&select=post_id" "${H[@]}" | jq 'length')
echo "ok_count=$OKS boosts=$N credits=$CR"
[ "$OKS" = 1 ] && [ "$N" = 1 ] && [ "$CR" = 0 ] || fail "race outcome wrong (want 1/1/0)"

# cleanup (RLS DELETE may be a no-op for owners; run as admin if rows remain)
curl -s -o /dev/null -X DELETE "$BASE/boosts?channel_id=eq.$CH" "${H[@]}"
curl -s -o /dev/null -X DELETE "$BASE/posts?channel_id=eq.$CH" "${H[@]}"
curl -s -o /dev/null -X DELETE "$BASE/channels?id=eq.$CH" "${H[@]}"
echo "PASS"
