#!/usr/bin/env bash
# ── Journal Usage Tracking — Manual Test Script ──────────────────────────────
#
# Tests: pin toggle, AI suggest, usage badge data in list
#
# Setup:
#   1. Open https://web-tau-dun-23.vercel.app in Chrome
#   2. DevTools → Application → Local Storage → find key starting with sb-
#      Copy the access_token value from the JSON
#   3. Find your brand_id from the URL when you're on a brand page
#      e.g. /brands/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
#
# Usage:
#   TOKEN="your-jwt-token-here" BRAND_ID="your-brand-uuid" bash test_journal_features.sh

API="https://api-iota-puce.vercel.app"
TOKEN="${TOKEN:?Set TOKEN= to your Supabase JWT access_token}"
BRAND_ID="${BRAND_ID:?Set BRAND_ID= to your brand UUID}"

H_AUTH="Authorization: Bearer $TOKEN"
H_CT="Content-Type: application/json"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Journal Feature Tests — $(date '+%Y-%m-%d %H:%M')"
echo "  API: $API"
echo "  Brand: $BRAND_ID"
echo "═══════════════════════════════════════════════════"

# ── 1. List entries (check times_used / pinned fields exist) ─────────────────
echo ""
echo "▶ 1. List journal entries (shows times_used, pinned, last_used_at)"
ENTRIES=$(curl -s "$API/journal?brand_id=$BRAND_ID&limit=5" \
  -H "$H_AUTH")
echo "$ENTRIES" | python3 -m json.tool 2>/dev/null || echo "$ENTRIES"

# Extract first entry ID for subsequent tests
ENTRY_ID=$(echo "$ENTRIES" | python3 -c "
import json, sys
data = json.load(sys.stdin)
if data: print(data[0]['id'])
" 2>/dev/null)

if [ -z "$ENTRY_ID" ]; then
  echo ""
  echo "⚠  No journal entries found. Creating a test entry first..."
  CREATE_RESP=$(curl -s -X POST "$API/journal" \
    -H "$H_AUTH" -H "$H_CT" \
    -d "{\"brand_id\":\"$BRAND_ID\",\"title\":\"Test Entry — Pin & Rotation\",\"source_type\":\"note\",\"raw_content\":\"Had a call with a SaaS founder today. They were struggling with positioning their product for mid-market buyers. Key insight: they kept leading with features instead of the outcome. Switched their pitch to 'you close 40% more demos when prospects see the ROI upfront.'\",\"tags\":[\"positioning\",\"SaaS\",\"demo\"]}")
  echo "$CREATE_RESP" | python3 -m json.tool 2>/dev/null
  ENTRY_ID=$(echo "$CREATE_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])" 2>/dev/null)
  echo "  Created entry: $ENTRY_ID"
fi

echo ""
echo "  Entry ID to test: $ENTRY_ID"

# ── 2. Pin the entry ──────────────────────────────────────────────────────────
echo ""
echo "▶ 2. PIN entry (should flip pinned: false → true)"
PIN_RESP=$(curl -s -X PATCH "$API/journal/$ENTRY_ID/pin" \
  -H "$H_AUTH")
echo "$PIN_RESP" | python3 -m json.tool 2>/dev/null || echo "$PIN_RESP"

PINNED=$(echo "$PIN_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('pinned','?'))" 2>/dev/null)
echo ""
if [ "$PINNED" = "True" ] || [ "$PINNED" = "true" ]; then
  echo "  ✅ Pinned = true"
else
  echo "  ❌ Expected pinned=true, got: $PINNED"
fi

# ── 3. Unpin (toggle again) ───────────────────────────────────────────────────
echo ""
echo "▶ 3. UNPIN entry (toggle again — should flip back to false)"
UNPIN_RESP=$(curl -s -X PATCH "$API/journal/$ENTRY_ID/pin" \
  -H "$H_AUTH")
UNPINNED=$(echo "$UNPIN_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('pinned','?'))" 2>/dev/null)
if [ "$UNPINNED" = "False" ] || [ "$UNPINNED" = "false" ]; then
  echo "  ✅ Unpinned = false"
else
  echo "  ❌ Expected pinned=false, got: $UNPINNED"
fi

# ── 4. Re-pin for suggest test ────────────────────────────────────────────────
curl -s -X PATCH "$API/journal/$ENTRY_ID/pin" -H "$H_AUTH" > /dev/null

# ── 5. AI Suggest — no topic (default rotation logic) ────────────────────────
echo ""
echo "▶ 4. AI SUGGEST — no topic (pinned-first + least-used ordering)"
SUGGEST_NOTOPIC=$(curl -s "$API/journal/suggest?brand_id=$BRAND_ID&limit=5" \
  -H "$H_AUTH")
echo "$SUGGEST_NOTOPIC" | python3 -m json.tool 2>/dev/null || echo "$SUGGEST_NOTOPIC"

REASONING=$(echo "$SUGGEST_NOTOPIC" | python3 -c "import json,sys; print(json.load(sys.stdin).get('reasoning',''))" 2>/dev/null)
echo ""
echo "  Reasoning: $REASONING"

# ── 6. AI Suggest — with topic (Haiku relevance ranking) ─────────────────────
echo ""
echo "▶ 5. AI SUGGEST — with topic (AI relevance ranking via Haiku)"
TOPIC="positioning strategy for SaaS companies selling to enterprise buyers"
SUGGEST_TOPIC=$(curl -s -G "$API/journal/suggest" \
  --data-urlencode "brand_id=$BRAND_ID" \
  --data-urlencode "topic=$TOPIC" \
  --data-urlencode "limit=3" \
  -H "$H_AUTH")
echo "$SUGGEST_TOPIC" | python3 -m json.tool 2>/dev/null || echo "$SUGGEST_TOPIC"

REASONING2=$(echo "$SUGGEST_TOPIC" | python3 -c "import json,sys; print(json.load(sys.stdin).get('reasoning',''))" 2>/dev/null)
echo ""
echo "  Reasoning: $REASONING2"

# ── 7. Check pinned entry is first in suggest results ────────────────────────
echo ""
echo "▶ 6. VERIFY pinned entry appears in suggestions"
FIRST_ID=$(echo "$SUGGEST_NOTOPIC" | python3 -c "
import json,sys
data = json.load(sys.stdin)
ids = data.get('suggested_ids', [])
print(ids[0] if ids else 'none')
" 2>/dev/null)

if [ "$FIRST_ID" = "$ENTRY_ID" ]; then
  echo "  ✅ Pinned entry is first in suggest results"
else
  echo "  ℹ  First suggestion: $FIRST_ID (pinned entry: $ENTRY_ID)"
  echo "     (May differ if other pinned entries exist)"
fi

# ── 8. Verify times_used = 0 (not used by pipeline yet) ──────────────────────
echo ""
echo "▶ 7. VERIFY times_used = 0 on the test entry (fresh badge)"
ENTRY_DETAIL=$(curl -s "$API/journal?brand_id=$BRAND_ID&limit=20" -H "$H_AUTH" | \
  python3 -c "
import json,sys
data = json.load(sys.stdin)
entry = next((e for e in data if e['id'] == '$ENTRY_ID'), None)
if entry:
    print(json.dumps({'times_used': entry['times_used'], 'pinned': entry['pinned'], 'last_used_at': entry['last_used_at']}, indent=2))
else:
    print('Entry not found in list')
" 2>/dev/null)
echo "$ENTRY_DETAIL"

# ── 9. IDOR test — try to pin with a fake entry_id ───────────────────────────
echo ""
echo "▶ 8. SECURITY — IDOR test (pin a non-existent entry)"
FAKE_ID="00000000-0000-0000-0000-000000000000"
IDOR_RESP=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$API/journal/$FAKE_ID/pin" -H "$H_AUTH")
if [ "$IDOR_RESP" = "404" ]; then
  echo "  ✅ 404 — IDOR protection working"
else
  echo "  ❌ Expected 404, got: $IDOR_RESP"
fi

# ── 10. Invalid UUID test ─────────────────────────────────────────────────────
echo ""
echo "▶ 9. SECURITY — Invalid UUID rejected"
BAD_RESP=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$API/journal/not-a-real-uuid/pin" -H "$H_AUTH")
if [ "$BAD_RESP" = "400" ]; then
  echo "  ✅ 400 — UUID validation working"
else
  echo "  ❌ Expected 400, got: $BAD_RESP"
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Done. Check the UI at:"
echo "  https://web-tau-dun-23.vercel.app/intelligence?tab=journal"
echo ""
echo "  What to verify in the UI:"
echo "  • ✨ Fresh badge on unused entries"
echo "  • 📌 Pin/Unpin button on each card"
echo "  • AI Suggest panel at top of journal"
echo "  • Pinned cards have blue border"
echo "  • AI-suggested cards have yellow border"
echo "═══════════════════════════════════════════════════"
