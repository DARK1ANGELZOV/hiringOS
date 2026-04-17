from enum import StrEnum


class Role(StrEnum):
    CANDIDATE = 'candidate'
    HR = 'hr'
    MANAGER = 'manager'
    ADMIN = 'admin'


ROLE_HIERARCHY: dict[Role, int] = {
    Role.CANDIDATE: 1,
    Role.HR: 2,
    Role.MANAGER: 3,
    Role.ADMIN: 4,
}


def has_role(required: set[Role], actual: Role) -> bool:
    return actual in required

