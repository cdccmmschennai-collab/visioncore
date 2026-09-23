import os
import shutil
import psycopg
from pathlib import Path

LOCAL_DB = {
    "host": "127.0.0.1",
    "port": 5433,
    "dbname": "visioncore",
    "user": "visioncore",
    "password": "visioncore",
}

PROD_DB = {
    "host": "127.0.0.1",
    "port": 15434,
    "dbname": "visioncore",
    "user": "visioncore",
    "password": os.environ["PROD_DB_PASSWORD"],
}

SOURCE_USER_ID = 3
TARGET_USER_ID = 3

def main():
    local = psycopg.connect(**LOCAL_DB)
    prod = psycopg.connect(**PROD_DB)

    local_cur = local.cursor()
    prod_cur = prod.cursor()

    print("Reading Local user1 batches...")

    local_cur.execute("""
        SELECT id, reference, status, total_images, total_tags,
               created_at, updated_at, is_batch_process,
               team, claude_config_id
        FROM batches
        WHERE user_id = %s
        ORDER BY id
    """, (SOURCE_USER_ID,))

    local_batches = local_cur.fetchall()

    print(f"Local user1 batches: {len(local_batches)}")

    # Safety check
    references = [r[1] for r in local_batches]

    prod_cur.execute("""
        SELECT reference
        FROM batches
        WHERE reference = ANY(%s)
    """, (references,))

    conflicts = {r[0] for r in prod_cur.fetchall()}

    if conflicts:
        print("\nSTOP: Production batch conflicts found:")
        for ref in sorted(conflicts):
            print("  ", ref)
        prod.rollback()
        local.close()
        prod.close()
        raise SystemExit(1)

    print("Batch-reference conflicts: 0")

    migrated_batches = 0
    migrated_items = 0
    migrated_images = 0
    reused_tags = 0
    new_tags = 0

    for batch in local_batches:
        (
            local_batch_id,
            reference,
            status,
            total_images,
            total_tags,
            created_at,
            updated_at,
            is_batch_process,
            team,
            claude_config_id,
        ) = batch

        print(f"\nMigrating batch: {reference}")

        prod_cur.execute("""
            INSERT INTO batches
            (
                reference,
                user_id,
                status,
                total_images,
                total_tags,
                created_at,
                updated_at,
                is_batch_process,
                team,
                claude_config_id
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            reference,
            TARGET_USER_ID,
            status,
            total_images,
            total_tags,
            created_at,
            updated_at,
            is_batch_process,
            team,
            None,
        ))

        prod_batch_id = prod_cur.fetchone()[0]

        local_cur.execute("""
            SELECT
                bi.id,
                bi.asset_tag_id,
                bi.tag_number,
                bi.description,
                bi.status,
                bi.error_message,
                bi.created_at,
                bi.updated_at,
                bi.retry_count
            FROM batch_items bi
            WHERE bi.batch_id = %s
            ORDER BY bi.id
        """, (local_batch_id,))

        items = local_cur.fetchall()

        for item in items:
            (
                local_item_id,
                local_asset_tag_id,
                tag_number,
                description,
                item_status,
                error_message,
                item_created_at,
                item_updated_at,
                retry_count,
            ) = item

            # Find existing Production asset_tag
            prod_cur.execute("""
                SELECT id
                FROM asset_tags
                WHERE tag_number = %s
            """, (tag_number,))

            existing = prod_cur.fetchone()

            if existing:
                prod_asset_tag_id = existing[0]
                reused_tags += 1
            else:
                # Read complete Local asset_tag
                local_cur.execute("""
                    SELECT
                        tag_number,
                        description,
                        ai_payload,
                        final_payload,
                        ai_excel_path,
                        template_excel_path,
                        edited_by_id,
                        created_by_id,
                        revision,
                        created_at,
                        updated_at
                    FROM asset_tags
                    WHERE id = %s
                """, (local_asset_tag_id,))

                asset = local_cur.fetchone()

                if not asset:
                    raise RuntimeError(
                        f"Missing Local asset_tag {local_asset_tag_id} "
                        f"for {tag_number}"
                    )

                (
                    a_tag_number,
                    a_description,
                    ai_payload,
                    final_payload,
                    ai_excel_path,
                    template_excel_path,
                    edited_by_id,
                    created_by_id,
                    revision,
                    a_created_at,
                    a_updated_at,
                ) = asset

                # Keep Production user IDs valid.
                # Do not blindly copy Local creator/editor IDs.
                prod_created_by = (
                    TARGET_USER_ID
                    if created_by_id == SOURCE_USER_ID
                    else None
                )

                prod_edited_by = (
                    TARGET_USER_ID
                    if edited_by_id == SOURCE_USER_ID
                    else None
                )

                prod_cur.execute("""
                    INSERT INTO asset_tags
                    (
                        tag_number,
                        description,
                        ai_payload,
                        final_payload,
                        ai_excel_path,
                        template_excel_path,
                        edited_by_id,
                        created_by_id,
                        revision,
                        created_at,
                        updated_at
                    )
                    VALUES
                    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                """, (
                    a_tag_number,
                    a_description,
                    ai_payload,
                    final_payload,
                    ai_excel_path,
                    template_excel_path,
                    prod_edited_by,
                    prod_created_by,
                    revision,
                    a_created_at,
                    a_updated_at,
                ))

                prod_asset_tag_id = prod_cur.fetchone()[0]
                new_tags += 1

            prod_cur.execute("""
                INSERT INTO batch_items
                (
                    batch_id,
                    asset_tag_id,
                    tag_number,
                    description,
                    status,
                    error_message,
                    created_at,
                    updated_at,
                    retry_count
                )
                VALUES
                (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                prod_batch_id,
                prod_asset_tag_id,
                tag_number,
                description,
                item_status,
                error_message,
                item_created_at,
                item_updated_at,
                retry_count,
            ))

            prod_item_id = prod_cur.fetchone()[0]

            # Get Local images
            local_cur.execute("""
                SELECT
                    id,
                    original_filename,
                    stored_path,
                    media_type,
                    size_bytes,
                    created_at,
                    updated_at,
                    content_hash
                FROM tag_images
                WHERE item_id = %s
                ORDER BY id
            """, (local_item_id,))

            images = local_cur.fetchall()

            for image in images:
                (
                    local_image_id,
                    original_filename,
                    stored_path,
                    media_type,
                    size_bytes,
                    image_created_at,
                    image_updated_at,
                    content_hash,
                ) = image

                # Check whether same physical image already exists
                prod_cur.execute("""
                    SELECT id
                    FROM tag_images
                    WHERE content_hash = %s
                    LIMIT 1
                """, (content_hash,))

                existing_image = prod_cur.fetchone()

                if existing_image:
                    print(
                        f"    Image already exists by hash: "
                        f"{original_filename}"
                    )
                    continue

                # Keep same relative storage path.
                prod_cur.execute("""
                    INSERT INTO tag_images
                    (
                        item_id,
                        original_filename,
                        stored_path,
                        media_type,
                        size_bytes,
                        created_at,
                        updated_at,
                        content_hash
                    )
                    VALUES
                    (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    prod_item_id,
                    original_filename,
                    stored_path,
                    media_type,
                    size_bytes,
                    image_created_at,
                    image_updated_at,
                    content_hash,
                ))

                migrated_images += 1

            migrated_items += 1

        migrated_batches += 1

        # Commit each batch so a huge migration does not stay in
        # one transaction.
        prod.commit()

        print(
            f"    Items migrated: {len(items)}"
        )

    print("\n====================================")
    print("MIGRATION COMPLETED")
    print("====================================")
    print(f"Batches migrated : {migrated_batches}")
    print(f"Items migrated   : {migrated_items}")
    print(f"New asset tags   : {new_tags}")
    print(f"Reused tags      : {reused_tags}")
    print(f"Images migrated  : {migrated_images}")
    print("====================================")

    local.close()
    prod.close()


if __name__ == "__main__":
    main()