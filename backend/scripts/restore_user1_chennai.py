"""Restore one Chennai user's extraction data from LOCAL into PRODUCTION.

Scope is deliberately narrow: batches owned by --username whose team is
CHENNAI, their batch_items and tag_images, the asset_tags that user created,
plus that user's Claude api_usage / activities rows missing from production.
No other user's or branch's rows are ever read for insertion, and nothing in
production is ever UPDATEd or DELETEd.

Local is a sync mirror of production (app/services/sync_client.py), so the
rows being restored carry the ids production originally gave them. Those are
re-inserted under the SAME ids, which keeps the local mirror's future sync
pulls matching instead of colliding. Every id and business key is checked
first; any conflict aborts before a single write.

api_usage and activities are not id-mirrored in every case (api_usage is
never synced), so those are de-duplicated by content fingerprint and inserted
with fresh production ids.

Usage (credentials come only from env vars and are never printed):
    LOCAL_DSN="host=localhost port=5433 dbname=visioncore user=... password=..."
    PROD_DSN="host=localhost port=15433 dbname=visioncore user=... password=..."
    python scripts/restore_user1_chennai.py                 # dry run (default)
    python scripts/restore_user1_chennai.py --apply         # one transaction
Writes <out-dir>/files_manifest.txt: storage-relative photo paths to copy.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

TEAM = "CHENNAI"
OTHER_TEAMS = ("HYDERABAD", "QATAR")

TIMESTAMPS = ("created_at", "updated_at")
BATCH_COLS = ("id", "reference", "user_id", "status", "total_images", "total_tags",
              "is_batch_process", "team", "claude_config_id") + TIMESTAMPS
TAG_COLS = ("id", "tag_number", "description", "ai_payload", "final_payload", "ai_excel_path",
            "template_excel_path", "edited_by_id", "created_by_id", "revision") + TIMESTAMPS
ITEM_COLS = ("id", "batch_id", "asset_tag_id", "tag_number", "description", "status",
             "error_message", "retry_count") + TIMESTAMPS
IMAGE_COLS = ("id", "item_id", "original_filename", "stored_path", "media_type", "size_bytes",
              "content_hash") + TIMESTAMPS
USAGE_COLS = ("user_id", "tag_number", "model", "input_tokens", "output_tokens", "cost_usd",
              "latency_ms", "success", "error_message", "team", "claude_config_id") + TIMESTAMPS
ACTIVITY_COLS = ("user_id", "action", "tag_number", "description", "detail", "meta") + TIMESTAMPS


class Abort(Exception):
    pass


def fetch(conn, sql, *args):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, args)
        return cur.fetchall()


def team_counts(conn) -> dict[str, dict[str, object]]:
    """Per-team row counts + Claude cost, used for the before/after proof."""
    rows = fetch(conn, """
        select t.team::text as team,
          (select count(*) from users u where u.team = t.team) as users,
          (select count(*) from batches b where b.team = t.team) as batches,
          (select count(*) from batch_items i join batches b on b.id = i.batch_id where b.team = t.team) as batch_items,
          (select count(*) from tag_images g join batch_items i on i.id = g.item_id
             join batches b on b.id = i.batch_id where b.team = t.team) as tag_images,
          (select count(*) from asset_tags a join users u on u.id = a.created_by_id where u.team = t.team) as asset_tags,
          (select count(*) from activities a join users u on u.id = a.user_id where u.team = t.team) as activities,
          (select count(*) from api_usage x where x.team = t.team) as api_usage,
          (select round(coalesce(sum(cost_usd), 0)::numeric, 6) from api_usage x where x.team = t.team) as cost_usd
        from unnest(enum_range(null::claude_config_team)) as t(team) order by 1""")
    return {r.pop("team"): r for r in rows}


def print_counts(title, counts):
    print(f"\n{title}")
    cols = list(next(iter(counts.values())))
    print(f"  {'team':10}" + "".join(f"{c:>12}" for c in cols))
    for team, r in counts.items():
        print(f"  {team:10}" + "".join(f"{str(r[c]):>12}" for c in cols))


def user_by_name(conn, username):
    rows = fetch(conn, "select id, username, role::text, team::text, is_active from users where username = %s", username)
    return rows[0] if rows else None


def existing(conn, table, ids):
    if not ids:
        return {}
    return {r["id"]: r for r in fetch(conn, f"select * from {table} where id = any(%s)", list(ids))}


def same(a, b, cols):
    return all(a[c] == b[c] for c in cols)


def classify(table, local_rows, prod_rows_by_id, cols, key=None, prod_by_key=None):
    """-> rows to insert, rows already present identically. Aborts on conflict."""
    to_insert, present, conflicts = [], [], []
    for row in local_rows:
        prod = prod_rows_by_id.get(row["id"])
        if prod is not None:
            if key is None or prod[key] == row[key]:
                present.append(row)  # same row already in production — leave it untouched
            else:
                conflicts.append(f"{table} id {row['id']} is taken by a different row ({key}={prod[key]!r})")
            continue
        if key is not None and row[key] in prod_by_key:
            conflicts.append(f"{table} {key}={row[key]!r} exists under a different id ({prod_by_key[row[key]]})")
            continue
        to_insert.append(row)
    if conflicts:
        raise Abort("\n  ".join([f"{len(conflicts)} {table} conflict(s):"] + conflicts[:25]))
    return to_insert, present


def insert_rows(conn, table, cols, rows, jsonb_cols=()):
    if not rows:
        return 0
    sql = (f"insert into {table} ({', '.join(cols)}) values ({', '.join(['%s'] * len(cols))}) "
           "on conflict do nothing")
    n = 0
    with conn.cursor() as cur:
        for r in rows:
            cur.execute(sql, [Jsonb(r[c]) if c in jsonb_cols else r[c] for c in cols])
            n += cur.rowcount
    if n != len(rows):
        raise Abort(f"{table}: expected {len(rows)} inserts, got {n} — rolled back")
    return n


def bump_sequence(conn, table):
    """Never moves a sequence backwards — only ensures it is past max(id)."""
    with conn.cursor() as cur:
        cur.execute(f"""select setval(pg_get_serial_sequence('{table}', 'id'),
                          greatest((select max(id) from {table}),
                                   (select last_value from {table}_id_seq)))""")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--username", default="user1")
    ap.add_argument("--apply", action="store_true", help="write to production (default: dry run)")
    ap.add_argument("--out-dir", default=".")
    args = ap.parse_args()

    local = psycopg.connect(os.environ["LOCAL_DSN"])
    local.read_only = True
    prod = psycopg.connect(os.environ["PROD_DSN"])
    prod.read_only = not args.apply

    try:
        # ---- users: must already exist on both sides, both CHENNAI ----------
        lu, pu = user_by_name(local, args.username), user_by_name(prod, args.username)
        if not lu or lu["team"] != TEAM:
            raise Abort(f"local user {args.username!r} missing or not {TEAM}: {lu}")
        if not pu or pu["team"] != TEAM:
            raise Abort(f"production user {args.username!r} missing or not {TEAM}: {pu}")
        if lu["id"] != pu["id"]:
            raise Abort(f"user id differs (local {lu['id']} / prod {pu['id']}); same-id restore is unsafe")
        uid = lu["id"]
        print(f"User {args.username!r}: id={uid} team={TEAM} role={pu['role']} active={pu['is_active']} (exists in production — not modified)")

        # Every other user id referenced by restored rows must resolve to the
        # same username in production, or it gets nulled (SET NULL columns only).
        local_names = {r["id"]: r["username"] for r in fetch(local, "select id, username from users")}
        prod_ids = {r["username"]: r["id"] for r in fetch(prod, "select id, username from users")}

        def map_user(local_id):
            if local_id is None:
                return None
            return prod_ids.get(local_names.get(local_id))

        # ---- read the local scope ------------------------------------------
        batches = fetch(local, "select * from batches where user_id = %s and team = %s order by id", uid, TEAM)
        bids = [b["id"] for b in batches]
        items = fetch(local, "select * from batch_items where batch_id = any(%s) order by id", bids)
        iids = [i["id"] for i in items]
        images = fetch(local, "select * from tag_images where item_id = any(%s) order by id", iids)
        tags = fetch(local, "select * from asset_tags where created_by_id = %s order by id", uid)

        prod_cfg = fetch(prod, "select id from claude_api_configs where team = %s", TEAM)
        prod_cfg_id = prod_cfg[0]["id"] if prod_cfg else None
        for b in batches:
            b["team"] = TEAM
            b["claude_config_id"] = prod_cfg_id if b["claude_config_id"] is not None else None
        for t in tags:
            t["created_by_id"] = uid
            t["edited_by_id"] = map_user(t["edited_by_id"])

        # ---- classify against production -----------------------------------
        prod_refs = {r["reference"]: r["id"] for r in fetch(prod, "select id, reference from batches where reference = any(%s)", [b["reference"] for b in batches])}
        prod_tagnums = {r["tag_number"]: r["id"] for r in fetch(prod, "select id, tag_number from asset_tags where tag_number = any(%s)", [t["tag_number"] for t in tags])}
        b_new, b_have = classify("batches", batches, existing(prod, "batches", bids), BATCH_COLS, "reference", prod_refs)
        t_new, t_have = classify("asset_tags", tags, existing(prod, "asset_tags", [t["id"] for t in tags]), TAG_COLS, "tag_number", prod_tagnums)
        i_new, i_have = classify("batch_items", items, existing(prod, "batch_items", iids), ITEM_COLS, "batch_id")
        g_new, g_have = classify("tag_images", images, existing(prod, "tag_images", [g["id"] for g in images]), IMAGE_COLS, "item_id")

        # batch_items.asset_tag_id must resolve after the restore, else SET NULL
        restorable_tag_ids = {t["id"] for t in tags} | set(existing(prod, "asset_tags", [i["asset_tag_id"] for i in items if i["asset_tag_id"]]))
        unlinked = [i for i in i_new if i["asset_tag_id"] and i["asset_tag_id"] not in restorable_tag_ids]
        for i in unlinked:
            i["asset_tag_id"] = None

        # ---- api_usage / activities: fingerprint de-dup, fresh ids ---------
        def usage_fp(u):
            return (u["tag_number"] or "", u["model"], u["input_tokens"], u["output_tokens"], u["created_at"])
        prod_usage = {usage_fp(u) for u in fetch(prod, "select * from api_usage where user_id = %s", uid)}
        usage = [u for u in fetch(local, "select * from api_usage where user_id = %s order by id", uid)
                 if usage_fp(u) not in prod_usage]
        for u in usage:
            u["team"], u["claude_config_id"] = TEAM, None

        fp_act = "action::text, coalesce(tag_number,''), created_at"
        prod_act = {tuple(r.values()) for r in fetch(prod, f"select {fp_act} from activities where user_id = %s", uid)}
        activities = [a for a in fetch(local, "select * from activities where user_id = %s order by id", uid)
                      if (a["action"], a["tag_number"] or "", a["created_at"]) not in prod_act]

        # ---- files ----------------------------------------------------------
        def rel(p):
            parts = Path(p.replace("\\", "/")).parts
            return "/".join(parts[parts.index("uploads"):]) if "uploads" in parts else None
        manifest = sorted({rel(g["stored_path"]) for g in g_new} - {None})
        bad_paths = [g["stored_path"] for g in g_new if rel(g["stored_path"]) is None]
        if bad_paths:
            raise Abort(f"{len(bad_paths)} image paths are not under uploads/: {bad_paths[:5]}")
        out = Path(args.out_dir) / "files_manifest.txt"
        out.write_text("\n".join(manifest) + ("\n" if manifest else ""), encoding="utf-8")

        # ---- plan -----------------------------------------------------------
        print("\nPLAN (insert = missing from production; present = identical row already there, skipped)")
        for name, new, have in (("asset_tags", t_new, t_have), ("batches", b_new, b_have),
                                ("batch_items", i_new, i_have), ("tag_images", g_new, g_have)):
            print(f"  {name:12} local={len(new) + len(have):5}  insert={len(new):5}  present={len(have):5}")
        print(f"  {'activities':12} insert={len(activities):5}  (not already in production by action+tag+time)")
        print(f"  {'api_usage':12} insert={len(usage):5}  cost_usd={sum(float(u['cost_usd']) for u in usage):.6f}")
        print(f"  batch_items whose asset tag is not restorable (asset_tag_id -> NULL): {len(unlinked)}")
        print(f"  photo files to copy: {len(manifest)}  (manifest: {out})")
        before = team_counts(prod)
        print_counts("PRODUCTION BEFORE", before)

        if not args.apply:
            print("\nDRY RUN — nothing written. Re-run with --apply to perform the restore.")
            return 0

        # ---- apply: one transaction, FK order -------------------------------
        with prod.transaction():
            with prod.cursor() as cur:
                cur.execute("set constraints all immediate")
            n_tags = insert_rows(prod, "asset_tags", TAG_COLS, t_new, jsonb_cols=("ai_payload", "final_payload"))
            n_batches = insert_rows(prod, "batches", BATCH_COLS, b_new)
            n_items = insert_rows(prod, "batch_items", ITEM_COLS, i_new)
            n_images = insert_rows(prod, "tag_images", IMAGE_COLS, g_new)
            n_acts = insert_rows(prod, "activities", ACTIVITY_COLS, activities, jsonb_cols=("meta",))
            n_usage = insert_rows(prod, "api_usage", USAGE_COLS, usage)
            for table in ("asset_tags", "batches", "batch_items", "tag_images", "activities", "api_usage"):
                bump_sequence(prod, table)

            after = team_counts(prod)
            for team in OTHER_TEAMS:
                if after[team] != before[team]:
                    raise Abort(f"{team} counts changed ({before[team]} -> {after[team]}) — rolled back")
            print_counts("PRODUCTION AFTER (inside transaction, before commit)", after)
        print(f"\nCOMMITTED: asset_tags={n_tags} batches={n_batches} batch_items={n_items} "
              f"tag_images={n_images} activities={n_acts} api_usage={n_usage}")
        return 0
    except Abort as e:
        print(f"\nABORTED — no changes written.\n  {e}", file=sys.stderr)
        return 2
    finally:
        local.close()
        prod.close()


if __name__ == "__main__":
    sys.exit(main())
