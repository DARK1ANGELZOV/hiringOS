from app.models.enums import ProfileOptionType
from app.models.profile_option import ProfileOption
from app.repositories.base import BaseRepository
from sqlalchemy import select


class ProfileOptionRepository(BaseRepository[ProfileOption]):
    async def list_by_type(self, *, option_type: ProfileOptionType, limit: int = 500) -> list[ProfileOption]:
        result = await self.db.execute(
            select(ProfileOption)
            .where(ProfileOption.option_type == option_type)
            .order_by(ProfileOption.value.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_type_and_normalized(self, *, option_type: ProfileOptionType, normalized_value: str) -> ProfileOption | None:
        result = await self.db.execute(
            select(ProfileOption).where(
                ProfileOption.option_type == option_type,
                ProfileOption.normalized_value == normalized_value,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        option_type: ProfileOptionType,
        value: str,
        normalized_value: str,
        created_by_user_id,
    ) -> ProfileOption:
        row = ProfileOption(
            option_type=option_type,
            value=value,
            normalized_value=normalized_value,
            created_by_user_id=created_by_user_id,
        )
        self.db.add(row)
        await self.db.flush()
        return row
