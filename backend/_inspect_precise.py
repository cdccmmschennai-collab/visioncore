import asyncio
from sqlalchemy import func, select
from app.db.session import AsyncSessionLocal
from app.models import ApiUsage, AssetTag


async def main() -> None:
    async with AsyncSessionLocal() as session:
        # Any tag_number with more than one successful ApiUsage row (shouldn't happen)
        dupes = (await session.execute(
            select(ApiUsage.tag_number, func.count())
            .where(ApiUsage.success.is_(True), ApiUsage.tag_number.is_not(None))
            .group_by(ApiUsage.tag_number)
            .having(func.count() > 1)
        )).all()
        print("tag_numbers with >1 successful ApiUsage row:", dupes)

        gemini_success_tags = set((await session.scalars(
            select(ApiUsage.tag_number).where(
                ApiUsage.success.is_(True), ApiUsage.model.ilike("%gemini%")
            )
        )).all())
        claude_success_tags = set((await session.scalars(
            select(ApiUsage.tag_number).where(
                ApiUsage.success.is_(True), ApiUsage.model == "claude-sonnet-5"
            )
        )).all())
        print(f"\nGemini-successful tag_numbers ({len(gemini_success_tags)}):", sorted(gemini_success_tags))
        print(f"\nClaude-successful tag_numbers ({len(claude_success_tags)}):", sorted(claude_success_tags))
        print("\nOverlap (should be empty):", gemini_success_tags & claude_success_tags)

        all_asset_tags = set((await session.scalars(select(AssetTag.tag_number))).all())
        print(f"\nAssetTag.tag_number total: {len(all_asset_tags)}")
        print("AssetTags with NO successful ApiUsage row at all (orphans, need separate check):",
              sorted(all_asset_tags - gemini_success_tags - claude_success_tags))

        # Failed-only ApiUsage rows (safe to delete regardless if Gemini - they produced no AssetTag)
        gemini_failed_only = await session.scalar(
            select(func.count()).select_from(ApiUsage).where(
                ApiUsage.success.is_(False), ApiUsage.model.ilike("%gemini%")
            )
        )
        print(f"\nGemini ApiUsage rows with success=False: {gemini_failed_only}")


if __name__ == "__main__":
    asyncio.run(main())
