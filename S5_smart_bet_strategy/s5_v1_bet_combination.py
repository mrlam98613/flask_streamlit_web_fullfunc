"""S5 v1：無冷熱號的 A/B/C/D 投注組合核心。"""

from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import combinations, product
from typing import Iterable

GROUPS = {"A": tuple(range(1, 10)), "B": tuple(range(10, 21)), "C": tuple(range(21, 32)), "D": tuple(range(32, 41))}


@dataclass(frozen=True)
class PoolSpec:
    name: str
    groups: tuple[str, ...]

    @property
    def numbers(self):
        return tuple(number for group in self.groups for number in GROUPS[group])

    @property
    def base_bets(self):
        return len(self.numbers) // 6

    @property
    def remainder(self):
        return len(self.numbers) % 6

    @property
    def supplement_picks(self):
        return 6 - self.remainder if self.remainder else 0


POOL_SPECS = tuple(PoolSpec("+".join(groups), groups) for size in (2, 3, 4) for groups in combinations(GROUPS, size))


def quota_patterns(groups: tuple[str, ...], main_group: str | None = None):
    if main_group and main_group not in groups:
        raise ValueError("主力組必須在候選球池內")
    return [values for values in product(range(7), repeat=len(groups)) if sum(values) == 6 and all(values)]


def _choose_quota_matrix(spec, rng, available, main_group=None):
    patterns = quota_patterns(spec.groups, main_group)
    for _ in range(500):
        rows, remaining = [], available.copy()
        for _ in range(spec.base_bets):
            choices = [p for p in patterns if all(p[i] <= remaining[group] for i, group in enumerate(spec.groups))]
            if not choices:
                break
            values = rng.choice(choices)
            row = dict(zip(spec.groups, values))
            rows.append(row)
            for group, value in row.items():
                remaining[group] -= value
        if len(rows) == spec.base_bets and all(value == 0 for value in remaining.values()):
            return rows
    rows = [dict.fromkeys(spec.groups, 0) for _ in range(spec.base_bets)]
    for group, count in available.items():
        for index in range(count):
            rows[index % spec.base_bets][group] += 1
    return rows


def generate_bets(spec: PoolSpec, seed: int | None = None, main_group: str | None = None):
    rng = random.Random(seed)
    numbers = list(spec.numbers)
    rng.shuffle(numbers)
    used = numbers[: spec.base_bets * 6]
    by_group = {group: [number for number in used if number in GROUPS[group]] for group in spec.groups}
    available = {group: len(values) for group, values in by_group.items()}
    quota = _choose_quota_matrix(spec, rng, available, main_group or spec.groups[0])
    basic = []
    for row in quota:
        ticket = []
        for group, count in row.items():
            ticket.extend(by_group[group][:count])
            del by_group[group][:count]
        rng.shuffle(ticket)
        basic.append(tuple(sorted(ticket)))
    remainder = sorted(numbers[spec.base_bets * 6:])
    if spec.supplement_picks:
        supplement = remainder + rng.sample([n for ticket in basic for n in ticket], spec.supplement_picks)
        basic.append(tuple(sorted(supplement)))
    return basic, {"quota": quota, "remainder": remainder, "base_bets": spec.base_bets}


def hit_summary(bets: Iterable[tuple[int, ...]], draw_numbers: Iterable[int]):
    numbers = list(draw_numbers)
    main_draw = set(numbers[:6])
    special = numbers[6] if len(numbers) >= 7 else None
    scores = []
    for ticket in bets:
        score = float(len(set(ticket) & main_draw))
        if score < 6 and special is not None and special in ticket:
            score += 0.5
        scores.append(score)
    distribution = {score: scores.count(score) for score in (3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0)}
    return {
        "max_hit": max(scores, default=0),
        "hit_6": distribution[6.0],
        "hit_5_plus": sum(count for score, count in distribution.items() if score >= 5.0),
        "distribution": distribution,
    }


def load_draws(csv_path):
    import pandas as pd
    frame = pd.read_csv(csv_path, encoding="utf-8-sig")
    return [{"date": str(row.iloc[0]), "numbers": [int(row.iloc[index]) for index in range(1, 8)]} for _, row in frame.iterrows()]
