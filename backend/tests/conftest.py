import os
import subprocess
import sys
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from uuid import uuid4

import asyncpg
import httpx
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.app import app
from app.core.config import get_settings
from app.core.db import get_session


@dataclass(frozen=True)
class ParentFamily:
    token: str
    family_id: str
    child_id: str


@dataclass(frozen=True)
class PairedDevice:
    parent: ParentFamily
    device_id: str
    device_token: str


@pytest_asyncio.fixture(scope="session")
async def test_database_url() -> AsyncGenerator[str]:
    source = get_settings().database_url
    database = f"guardian_test_{uuid4().hex}"
    admin = await asyncpg.connect(
        user="guardian",
        password="guardian",
        database="guardian",
        host="localhost",
        port=5432,
    )
    try:
        await admin.execute(f'CREATE DATABASE "{database}"')
    finally:
        await admin.close()
    url = source.rsplit("/", 1)[0] + f"/{database}"
    environment = os.environ | {"GUARDIAN_DATABASE_URL": url}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=environment,
        check=True,
    )
    try:
        yield url
    finally:
        cleanup = await asyncpg.connect(
            user="guardian",
            password="guardian",
            database="guardian",
            host="localhost",
            port=5432,
        )
        try:
            await cleanup.execute(f'ALTER DATABASE "{database}" WITH ALLOW_CONNECTIONS false')
            await cleanup.execute(f'DROP DATABASE "{database}"')
        finally:
            await cleanup.close()


@pytest_asyncio.fixture
async def client(test_database_url: str) -> AsyncGenerator[httpx.AsyncClient]:
    engine = create_async_engine(test_database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session() -> AsyncGenerator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as value:
            yield value
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest_asyncio.fixture
async def parent_a(client: httpx.AsyncClient) -> ParentFamily:
    signup = await client.post(
        "/v1/auth/signup",
        json={"email": f"{uuid4()}@example.com", "password": "correct horse battery staple"},
    )
    token = signup.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    family = await client.post("/v1/families", json={"name": "Family A"}, headers=headers)
    family_id = family.json()["id"]
    child = await client.post(
        f"/v1/families/{family_id}/children",
        json={"name": "Alex", "date_of_birth": "2017-08-15", "timezone": "UTC"},
        headers=headers,
    )
    return ParentFamily(token, family_id, child.json()["id"])


@pytest_asyncio.fixture
async def parent_b(client: httpx.AsyncClient) -> ParentFamily:
    signup = await client.post(
        "/v1/auth/signup",
        json={"email": f"{uuid4()}@example.com", "password": "correct horse battery staple"},
    )
    token = signup.json()["access_token"]
    family = await client.post(
        "/v1/families", json={"name": "Family B"}, headers={"Authorization": f"Bearer {token}"}
    )
    family_id = family.json()["id"]
    child = await client.post(
        f"/v1/families/{family_id}/children",
        json={"name": "Blair", "date_of_birth": "2013-08-15", "timezone": "UTC"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return ParentFamily(token, family_id, child.json()["id"])


@pytest_asyncio.fixture
async def database_session(test_database_url: str) -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine(test_database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def paired_device(
    client: httpx.AsyncClient, parent_a: ParentFamily
) -> PairedDevice:
    headers = {"Authorization": f"Bearer {parent_a.token}"}
    pairing = await client.post(
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}/pairing",
        headers=headers,
    )
    payload = pairing.json()["qr_payload"]
    code = payload.rsplit("code=", 1)[1]
    redeemed = await client.post(
        "/v1/devices/pair",
        json={
            "session_id": pairing.json()["session_id"],
            "code": code,
            "child_profile_id": parent_a.child_id,
            "platform": "ANDROID",
            "public_key": "test-device-public-key-000000000000000000000000",
        },
    )
    return PairedDevice(parent_a, redeemed.json()["device_id"], redeemed.json()["device_token"])


@pytest_asyncio.fixture
async def revoked_device(client: httpx.AsyncClient, paired_device: PairedDevice) -> PairedDevice:
    response = await client.post(
        f"/v1/families/{paired_device.parent.family_id}/devices/{paired_device.device_id}/revoke",
        headers={"Authorization": f"Bearer {paired_device.parent.token}"},
    )
    assert response.status_code == 204
    return paired_device
