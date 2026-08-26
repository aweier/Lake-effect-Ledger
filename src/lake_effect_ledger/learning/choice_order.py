"""Stable, save-specific ordering for knowledge-check choices."""

from __future__ import annotations

from hashlib import sha256

from lake_effect_ledger.learning.models import CheckOption, KnowledgeCheckDefinition


def ordered_check_options(
    check: KnowledgeCheckDefinition,
    *,
    game_seed: int,
) -> list[CheckOption]:
    """Return a deterministic permutation without mutating authored content."""

    def order_key(option: CheckOption) -> bytes:
        identity = f"lake-ledger-check-order-v1:{game_seed}:{check.id}:{option.id}"
        return sha256(identity.encode("utf-8")).digest()

    return sorted(check.options, key=order_key)
