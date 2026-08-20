import asyncio
from sqlalchemy import func, select
from app.db.session import AsyncSessionLocal
from app.models import ApiUsage, AssetTag, Batch, BatchItem, Activity


async def main() -> None:
    async with AsyncSessionLocal() as session:
        for label, model in [("Batch", Batch), ("BatchItem", BatchItem),
                              ("AssetTag", AssetTag), ("ApiUsage", ApiUsage),
                              ("Activity", Activity)]:
            total = await session.scalar(select(func.count()).select_from(model))
            print(f"{label}: {total}")

        all_batch_ids = set((await session.scalars(select(Batch.id))).all())
        touched = set(range(1, 54))
        print("\nBatches NOT touched by the Gemini tag_number list:", sorted(all_batch_ids - touched))

        claude_tags = set((await session.scalars(
            select(ApiUsage.tag_number).where(ApiUsage.model == "claude-sonnet-5", ApiUsage.tag_number.is_not(None))
        )).all())
        print("Claude-derived tag_numbers:", claude_tags)


if __name__ == "__main__":
    asyncio.run(main())
