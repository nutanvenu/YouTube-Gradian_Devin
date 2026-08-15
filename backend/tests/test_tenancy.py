import pytest
from conftest import ParentFamily


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "suffix", "body"),
    [
        ("get", "", None),
        ("post", "/children", {"name": "Other", "date_of_birth": "2015-01-01", "timezone": "UTC"}),
        ("get", "/children", None),
        ("get", "/guardians", None),
        ("post", "/guardians/invite", {"email": "other@example.com"}),
        ("post", "/children/{child_id}/pairing", None),
        ("patch", "/children/{child_id}", {"name": "Other"}),
        ("delete", "/children/{child_id}", None),
    ],
)
async def test_every_family_route_enforces_tenancy(
    client, parent_a: ParentFamily, parent_b: ParentFamily, method: str, suffix: str, body
) -> None:
    path = f"/v1/families/{parent_a.family_id}{suffix.format(child_id=parent_a.child_id)}"
    response = await client.request(
        method.upper(),
        path,
        json=body,
        headers={"Authorization": f"Bearer {parent_b.token}"},
    )
    assert response.status_code == 404
