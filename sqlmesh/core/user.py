import typing as t
from enum import Enum

from sqlmesh.utils.pydantic import PydanticModel


class UserRole(str, Enum):
    """A role to associate the user with"""

    REQUIRED_APPROVER = "required_approver"
    BOT = "bot"

    @property
    def is_required_approver(self) -> bool:
        return self == UserRole.REQUIRED_APPROVER

    @property
    def is_bot(self) -> bool:
        return self == UserRole.BOT


class User(PydanticModel):
    """SQLMesh user information that can be used for notifications"""

    username: str
    """The name to refer to the user"""
    github_username: t.Optional[str] = None
    """The github login username"""
    slack_username: t.Optional[str] = None
    """The slack username"""
    email: t.Optional[str] = None
    """The email for the user (full address)"""
    roles: t.List[UserRole] = []
    """List of roles to associate with the user"""

    @property
    def is_required_approver(self) -> bool:
        """Indicates if this is a required approver for PR approvals."""
        return UserRole.REQUIRED_APPROVER in self.roles

    @property
    def is_bot(self) -> bool:
        """Indicates if this is a CI/CD bot account. There should only be one of these per project"""
        return UserRole.BOT in self.roles
