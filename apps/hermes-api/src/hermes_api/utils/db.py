from sqlalchemy.ext.asyncio import AsyncSession


async def delete_and_commit(session: AsyncSession, entity: object) -> None:
    await session.delete(entity)
    await session.commit()
