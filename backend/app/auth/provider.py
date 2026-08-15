from typing import Protocol

from .models import Parent
from .service import hash_password, verify_password


class AuthProvider(Protocol):
    def hash_password(self, password: str) -> str: ...

    def verify_password(self, password: str, encoded: str) -> bool: ...


class LocalAuthProvider:
    def hash_password(self, password: str) -> str:
        return hash_password(password)

    def verify_password(self, password: str, encoded: str) -> bool:
        return verify_password(password, encoded)


def authenticated_parent(provider: AuthProvider, parent: Parent, password: str) -> bool:
    return provider.verify_password(password, parent.password_hash)
