"""Read-only: report what Gemini-sourced data exists in the DB. Deletes nothing."""
import asyncio

from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.models import ApiUsage, AssetTag, Batch, BatchItem, Activity, ActivityAction


async def main() -> None:
    async with AsyncSessionLocal() as session:
        print("=== ApiUsage.model distinct values + counts ===")
        rows = (await session.execute(
            select(ApiUsage.model, func.count()).group_by(ApiUsage.model)
        )).all()
        for model, count in rows:
            print(f"  {model!r}: {count}")

        gemini_tag_numbers = set(
            (await session.scalars(
                select(ApiUsage.tag_number)
                .where(ApiUsage.model.ilike("%gemini%"), ApiUsage.tag_number.is_not(None))
                .distinct()
            )).all()
        )
        print(f"\nDistinct tag_numbers with a Gemini ApiUsage row: {len(gemini_tag_numbers)}")

        gemini_usage_count = await session.scalar(
            select(func.count()).select_from(ApiUsage).where(ApiUsage.model.ilike("%gemini%"))
        )
        print(f"ApiUsage rows (Gemini, incl. failures with no tag_number): {gemini_usage_count}")

        if gemini_tag_numbers:
            asset_tags = (await session.scalars(
                select(AssetTag).where(AssetTag.tag_number.in_(gemini_tag_numbers))
            )).all()
            print(f"\nAssetTag rows matching those tag_numbers: {len(asset_tags)}")
            for t in asset_tags:
                print(f"  id={t.id} tag_number={t.tag_number!r} description={t.description!r} created_at={t.created_at}")

            batch_items = (await session.scalars(
                select(BatchItem).where(BatchItem.tag_number.in_(gemini_tag_numbers))
            )).all()
            print(f"\nBatchItem rows matching those tag_numbers: {len(batch_items)}")
            batch_ids = sorted({bi.batch_id for bi in batch_items})
            for bi in batch_items:
                print(f"  id={bi.id} batch_id={bi.batch_id} tag_number={bi.tag_number!r} status={bi.status.value}")

            print(f"\nDistinct batches touched: {batch_ids}")
            for bid in batch_ids:
                batch = await session.get(Batch, bid)
                total_items = await session.scalar(
                    select(func.count()).select_from(BatchItem).where(BatchItem.batch_id == bid)
                )
                gemini_items_in_batch = sum(1 for bi in batch_items if bi.batch_id == bid)
                print(f"  batch {bid} reference={batch.reference!r} total_items={total_items} gemini_items={gemini_items_in_batch} status={batch.status.value}")

            activity_count = await session.scalar(
                select(func.count()).select_from(Activity).where(
                    Activity.tag_number.in_(gemini_tag_numbers),
                    Activity.action == ActivityAction.EXTRACT,
                )
            )
            print(f"\nActivity rows (action=extract) for those tag_numbers: {activity_count}")
        else:
            print("\nNo AssetTag/BatchItem lookup needed - no Gemini tag_numbers found.")


if __name__ == "__main__":
    asyncio.run(main())
