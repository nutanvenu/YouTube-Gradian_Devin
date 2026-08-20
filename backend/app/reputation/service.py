from datetime import UTC, datetime, timedelta
from typing import Final, Literal, Protocol, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..policies.signing import signer
from .models import ReputationEntry, ReputationRevision, ReputationState
from .schemas import ReputationEntryOut

REPUTATION_TTL: Final = timedelta(days=30)
MAX_DELTA_CHAIN: Final = 32
ReputationVerdict = Literal["KNOWN_SAFE", "KNOWN_RISK", "UNKNOWN"]


class ReputationClassifier(Protocol):
    async def classify(self, identifier: str) -> tuple[ReputationVerdict, str, str]:
        """Return verdict, source, and deterministic rationale."""


class NoCuratedVerdictClassifier:
    """Production-safe placeholder until a reviewed reputation provider is supplied."""

    async def classify(self, identifier: str) -> tuple[ReputationVerdict, str, str]:
        del identifier
        return (
            "UNKNOWN",
            "guardian-no-curated-verdict",
            "No curated verdict is available; no score or heuristic was fabricated.",
        )


classifier: ReputationClassifier = NoCuratedVerdictClassifier()


def normalize_domain_identifier(identifier: str) -> str:
    value = identifier.strip().rstrip(".").lower()
    if (
        not value
        or len(value) > 253
        or any(char.isspace() for char in value)
        or any(char in value for char in "/?#:")
        or "." not in value
    ):
        raise ValueError("identifier must be a normalized domain without a URL or path")
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("identifier is not a valid domain") from exc
    labels = value.split(".")
    if any(not label or len(label) > 63 for label in labels):
        raise ValueError("identifier contains an invalid label")
    return value


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _entry_value(entry: ReputationEntry) -> dict[str, object]:
    return ReputationEntryOut.model_validate(entry).model_dump(mode="json")


def _signed_document(
    kind: str,
    version: int,
    base_version: int | None,
    entries: list[dict[str, object]],
) -> dict[str, object]:
    issued_at = _now()
    return signer.sign_document(
        {
            "schema_version": 1,
            "kind": kind,
            "bundle_version": version,
            "base_version": base_version,
            "issued_at": issued_at.isoformat().replace("+00:00", "Z"),
            "expires_at": (_now() + REPUTATION_TTL).isoformat().replace("+00:00", "Z"),
            "entries": entries,
            "signature": "",
        }
    )


async def _ensure_state(session: AsyncSession) -> ReputationState:
    state = await session.scalar(
        select(ReputationState).where(ReputationState.id == 1).with_for_update()
    )
    if state is not None:
        return state
    state = ReputationState(id=1, current_version=0)
    session.add(state)
    await session.flush()
    return state


async def current_entries(session: AsyncSession) -> list[ReputationEntry]:
    return list(
        (
            await session.scalars(
                select(ReputationEntry).order_by(
                    ReputationEntry.target_kind, ReputationEntry.identifier
                )
            )
        ).all()
    )


async def sync_for_version(
    session: AsyncSession, version: int
) -> tuple[int, dict[str, object] | None, list[dict[str, object]]]:
    state = await _ensure_state(session)
    current = state.current_version
    if version < 0 or version > current:
        version = 0
    if version == current:
        return current, None, []
    revisions = list(
        (
            await session.scalars(
                select(ReputationRevision)
                .where(ReputationRevision.bundle_version > version)
                .order_by(ReputationRevision.bundle_version)
                .limit(MAX_DELTA_CHAIN + 1)
            )
        ).all()
    )
    chain_is_complete = (
        len(revisions) == current - version
        and all(
            revision.bundle_version == version + index
            for index, revision in enumerate(revisions, start=1)
        )
    )
    if (
        version > 0
        and chain_is_complete
        and all(revision.kind == "DELTA" for revision in revisions)
    ):
        return current, None, [revision.bundle for revision in revisions]
    full = await session.scalar(
        select(ReputationRevision).where(
            ReputationRevision.kind == "FULL",
            ReputationRevision.bundle_version == current,
        )
    )
    if full is None:
        entries = [_entry_value(entry) for entry in await current_entries(session)]
        full_bundle = _signed_document("FULL", current, None, entries)
        return current, full_bundle, []
    return current, full.bundle, []


async def classify_and_store(
    session: AsyncSession, identifier: str
) -> tuple[ReputationVerdict, str]:
    normalized = normalize_domain_identifier(identifier)
    state = await _ensure_state(session)
    existing = await session.scalar(
        select(ReputationEntry).where(
            ReputationEntry.target_kind == "DOMAIN",
            ReputationEntry.identifier == normalized,
        )
    )
    if existing is not None and existing.expires_at > _now():
        return cast(ReputationVerdict, existing.verdict), "CACHED_SERVER_REPUTATION"
    verdict, source, rationale = await classifier.classify(normalized)
    now = _now()
    next_version = state.current_version + 1
    if existing is None:
        existing = ReputationEntry(
            target_kind="DOMAIN",
            identifier=normalized,
            verdict=verdict,
            source=source,
            rationale=rationale,
            expires_at=now + REPUTATION_TTL,
            bundle_version=next_version,
        )
        session.add(existing)
    else:
        existing.verdict = verdict
        existing.source = source
        existing.rationale = rationale
        existing.expires_at = now + REPUTATION_TTL
        existing.bundle_version = next_version
    await session.flush()
    delta = _signed_document("DELTA", next_version, state.current_version, [_entry_value(existing)])
    session.add(
        ReputationRevision(
            bundle_version=next_version,
            kind="DELTA",
            base_version=state.current_version,
            bundle=delta,
        )
    )
    state.current_version = next_version
    await session.flush()
    return verdict, "NO_CURATED_VERDICT" if verdict == "UNKNOWN" else "CURATED_VERDICT"
