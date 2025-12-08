from typing import Optional, Dict, List, Tuple
from math import floor
from collections import Counter, defaultdict
from deck.schemas.schema import Candidate

def _validate_caps(max_share_per_pos: Optional[Dict[str, float]]) -> None:
    """
    Hard caps semantics: sum may be <= 1.0 (leftover means other POS can fill it).
    We reject sums > 1.0 to avoid ambiguous intent.
    """
    if not max_share_per_pos:
        return
    total = sum(max(0.0, v) for v in max_share_per_pos.values())
    if total > 1.0 + 1e-9:
        raise ValueError(
            f"max_share_per_pos sums to {total:.3f} (> 1). "
            "Lower the shares or spread across more POS."
        )

def _caps_to_counts(deck_limit: int, max_share_per_pos: Optional[Dict[str, float]]) -> Dict[str, int]:
    """
    Convert cap shares to integer limits against the deck budget.
    We do NOT normalize if sum < 1.0 (leftover is allowed).
    Output is a dictionary of POS -> count.
    """
    if not max_share_per_pos:
        return {}
    return {pos: max(0, floor(max(0.0, share) * deck_limit))
            for pos, share in max_share_per_pos.items()}

def _normalize_targets(target_share_per_pos: Dict[str, float]) -> Dict[str, float]:
    """
    Soft targets semantics: proportions to *aim for*.
    Normalize to sum = 1 so the 'need' math is stable even if sliders sum to ~0.98/1.02.
    """
    if not target_share_per_pos:
        return {}
    total = sum(max(0.0, v) for v in target_share_per_pos.values())
    if total <= 0:
        return {k: 0.0 for k in target_share_per_pos}
    return {k: max(0.0, v) / total for k, v in target_share_per_pos.items()}

def _bucketize_by_pos(candidates: list[Candidate]) -> dict[str, list[Candidate]]:
    """Group candidates by POS. Each bucket sorted by score descending; drop zero coverage."""
    buckets: dict[str, list[Candidate]] = defaultdict(list)
    for rc in candidates:
        if rc.cov_share > 0.0:
            buckets[rc.pos].append(rc)
    for pos, bucket in buckets.items():
        bucket.sort(key=lambda x: x.score, reverse=True)
    return buckets

def _is_eligible(pos: str,
                buckets: dict[str, list[Candidate]],
                pos_counts: Counter,
                caps: dict[str, int]) -> bool:
    """Eligible = bucket non-empty AND under its hard cap (if any)."""
    if not buckets.get(pos):
        return False
    cap = caps.get(pos)
    return (cap is None) or (pos_counts.get(pos, 0) < cap)

def _global_best_head(buckets: Dict[str, List[Candidate]],
                     pos_counts: Counter,
                     caps: Dict[str, int]) -> Tuple[Optional[str], Optional[Candidate]]:
    """Return (pos, item) for the best available head across eligible buckets."""
    best_pos: Optional[str] = None
    best_item: Optional[Candidate] = None
    for p, bucket in buckets.items():
        if not _is_eligible(p, buckets, pos_counts, caps):
            continue
        head = bucket[0]
        if best_item is None or head.score > best_item.score:
            best_item, best_pos = head, p
    return best_pos, best_item

def _compute_needs(pos_counts: Counter,
                   targets: Dict[str, float],
                   buckets: Dict[str, List[Candidate]],
                   caps: Dict[str, int],
                   alpha: float = 1.0) -> Dict[str, float]:
    """
    Smoothed need per POS: need = target_share - current_share,
    where current_share ≈ (count + α) / (N + α * P). Ineligible POS -> -inf.
    """
    needs: Dict[str, float] = {}
    if not targets:
        return needs

    P = len(targets)
    N = sum(pos_counts.values())
    denom = N + alpha * P

    for pos, t in targets.items():
        if not _is_eligible(pos, buckets, pos_counts, caps):
            needs[pos] = float("-inf")
            continue
        s_hat = (pos_counts.get(pos, 0) + alpha) / denom if denom > 0 else (1.0 / P)
        needs[pos] = t - s_hat
    return needs


# ----------------- Main picker -----------------

def pick_until_target(
    filtered_ranked: list[Candidate],
    max_cards: Optional[int],
    target_coverage: Optional[float],
    max_share_per_pos: Optional[dict[str, float]] = None,     # hard caps (sum ≤ 1)
    target_share_per_pos: Optional[dict[str, float]] = None,  # soft targets (normalized)
    hysteresis_eps: float = 0.02,    # ignore tiny needs near boundary
    score_gap_delta: float = 0.15,   # allow global best if it's ≥15% higher than the needed head
) -> Tuple[list[Candidate], dict]:
    """
    POS-aware greedy picker that respects hard caps and optionally steers toward a target mix.
    Stops at target_coverage or max_cards, or when candidates are exhausted.
    Returns (picked, report).
    """
    if target_coverage is not None and not (0.0 <= target_coverage <= 1.0):
        raise ValueError("target_coverage must be within [0, 1].")

    limit = max_cards if (max_cards is not None and int(max_cards) > 0) else len(filtered_ranked)
    # Max share per pos validation - sum <=1
    _validate_caps(max_share_per_pos)
    # Convert cap shares to integer limits against the deck budget
    caps = _caps_to_counts(limit, max_share_per_pos)
    # Normalize target shares to sum = 1
    targets = _normalize_targets(target_share_per_pos)

    buckets = _bucketize_by_pos(filtered_ranked)
    picked: list[Candidate] = []
    pos_counts: Counter = Counter()
    coverage = 0.0
    reason = "exhausted"

    while True:
        # --- Stop checks (top-of-loop prevents “one extra pick”) ---
        if target_coverage is not None and coverage >= target_coverage - 1e-12:
            reason = "target_coverage"; break
        if len(picked) >= limit:
            reason = "max_cards"; break
        if all(len(b) == 0 for b in buckets.values()):
            reason = "exhausted"; break
        if not any(_is_eligible(p, buckets, pos_counts, caps) for p in buckets):
            reason = "exhausted"; break

        # --- Seed with global best on the first iteration ---
        if not picked:
            g_pos, g_item = _global_best_head(buckets, pos_counts, caps)
            if g_item is None:
                reason = "exhausted"; break
            buckets[g_pos].pop(0)
            picked.append(g_item)
            pos_counts[g_pos] += 1
            coverage = min(1.0, coverage + g_item.cov_share)
            continue

        # --- Choose POS: soft need if provided; otherwise global best ---
        needs = _compute_needs(pos_counts, targets, buckets, caps) if targets else {}
        chosen_pos: Optional[str] = None

        if needs:
            pos_star = max(needs, key=needs.get)
            need_star = needs[pos_star]
            if need_star > hysteresis_eps and _is_eligible(pos_star, buckets, pos_counts, caps):
                # Global-utility override: if global best is much stronger than the needed head, take it.
                g_pos, g_item = _global_best_head(buckets, pos_counts, caps)
                needed_head = buckets[pos_star][0] if buckets[pos_star] else None
                if g_item and needed_head and g_item.score >= (1.0 + score_gap_delta) * needed_head.score:
                    chosen_pos = g_pos
                else:
                    chosen_pos = pos_star

        if chosen_pos is None:
            chosen_pos, _ = _global_best_head(buckets, pos_counts, caps)
        if chosen_pos is None:
            reason = "exhausted"; break

        # --- Commit pick ---
        item = buckets[chosen_pos].pop(0)
        picked.append(item)
        pos_counts[chosen_pos] += 1
        coverage = min(1.0, coverage + item.cov_share)

    report = {
        "picked_count": len(picked),
        "achieved_coverage": coverage,
        "pos_counts": dict(pos_counts),
        "stopped_reason": reason,
    }
    if target_coverage is not None and coverage < target_coverage - 1e-12:
        report["note"] = "Target not reached with current caps/availability."
    return picked, report