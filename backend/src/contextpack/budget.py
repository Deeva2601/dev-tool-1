"""Shrink a file set until its token sum fits a hard cap."""

from dataclasses import dataclass

from contextpack.compress import compress
from contextpack.models import Compression
from contextpack.tokens import count_tokens

_NEXT: dict[str, Compression] = {
    "full": "skeleton",
    "skeleton": "outline",
}


@dataclass
class BudgetItem:
    relative_path: str
    size_bytes: int
    language: str
    raw: str
    mode: Compression
    pinned: bool
    variants: dict[str, str]
    content: str
    tokens: int


@dataclass
class BudgetFit:
    kept: list[BudgetItem]
    omitted: list[str]


def prepare_item(
    relative_path: str,
    size_bytes: int,
    language: str,
    raw: str,
    mode: Compression,
    pinned: bool,
) -> BudgetItem:
    variants = {
        "full": compress(raw, language, "full"),
        "skeleton": compress(raw, language, "skeleton"),
        "outline": compress(raw, language, "outline"),
    }
    content = variants[mode]
    return BudgetItem(
        relative_path=relative_path,
        size_bytes=size_bytes,
        language=language,
        raw=raw,
        mode=mode,
        pinned=pinned,
        variants=variants,
        content=content,
        tokens=count_tokens(content),
    )


def fit_budget(items: list[BudgetItem], max_tokens: int | None) -> BudgetFit:
    """Downgrade, then omit, until the token sum is within max_tokens.

    A pinned item is never changed. A ``None`` budget leaves every item alone.
    """
    kept = list(items)
    if max_tokens is None or max_tokens < 0:
        return BudgetFit(kept=kept, omitted=[])

    omitted: list[str] = []
    while _total(kept) > max_tokens:
        step = _best_downgrade(kept)
        if step is None:
            break
        item, new_mode = step
        item.mode = new_mode
        item.content = item.variants[new_mode]
        item.tokens = count_tokens(item.content)

    while _total(kept) > max_tokens:
        victims = [item for item in kept if not item.pinned]
        if not victims:
            break
        victim = min(victims, key=lambda item: (item.rank, -item.tokens, item.relative_path))
        kept.remove(victim)
        omitted.append(f"{victim.relative_path} (over-budget)")

    kept.sort(key=lambda item: item.relative_path)
    omitted.sort()
    return BudgetFit(kept=kept, omitted=omitted)


def _total(items: list[BudgetItem]) -> int:
    return sum(item.tokens for item in items)


def _best_downgrade(items: list[BudgetItem]) -> tuple[BudgetItem, Compression] | None:
    best: tuple[tuple[float, int, str], BudgetItem, Compression] | None = None
    for item in items:
        if item.pinned:
            continue
        nxt = _NEXT.get(item.mode)
        if nxt is None:
            continue
        saved = item.tokens - count_tokens(item.variants[nxt])
        key = (-item.rank, saved, item.relative_path)
        if best is None or key > best[0]:
            best = (key, item, nxt)
    if best is None:
        return None
    return best[1], best[2]