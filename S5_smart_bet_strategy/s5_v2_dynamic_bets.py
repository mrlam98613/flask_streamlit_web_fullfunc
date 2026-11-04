"""S5 v2 動態候選球池及主力／配腳配額。"""
from __future__ import annotations

import random
from functools import lru_cache
from itertools import product

'''
S5_v2 驗證程式 
=== 總結 ===
A+B     3球=4注
A+C     3球=5注, 3.5球=1注, 4.5球=1注
A+D     3球=4注
B+C     3球=4注
B+D     3球=2注
C+D     3球=5注, 3.5球=1注
A+B+C   3球=4注
A+B+D   3球=3注, 3.5球=1注
A+C+D   3球=4注, 4球=1注
B+C+D   3球=4注, 3.5球=1注
A+B+C+D 3球=4注, 4球=1注
'''

def pool_size(groups: dict[str, list[int]], pool_name: str) -> int:
    """計算指定組合的動態候選球池總數。"""
    return sum(len(groups[group]) for group in pool_name.split("+"))


def _quota_matrix(group_names, sizes, base_count, main_group, rng):
    """建立基本注配額矩陣，並優先讓主力組取得每注 2–3 球。"""
    total = base_count * 6
    reserve = sum(sizes.values()) - total
    used = sizes.copy()
    # 優先把餘球留在配腳組；不足時才留在主力組。
    for group in sorted(group_names, key=lambda g: (g == main_group, sizes[g])):
        # 每組至少要能在每一張基本注出現 1 球，否則無法組成矩陣。
        take = min(reserve, max(0, used[group] - base_count))
        used[group] -= take
        reserve -= take
        if reserve == 0:
            break
    patterns = [p for p in product(range(7), repeat=len(group_names)) if sum(p) == 6 and all(p)]
    main_index = group_names.index(main_group)
    ordered_patterns = sorted(patterns, key=lambda p: (0 if 2 <= p[main_index] <= 3 else 1, rng.random()))

    @lru_cache(maxsize=None)
    def solve(rows_left, remaining_tuple):
        """用遞迴搜尋找出每列 6 球且總配額剛好用完的方案。"""
        if rows_left == 0:
            return () if not any(remaining_tuple) else None
        for values in ordered_patterns:
            if all(values[i] <= remaining_tuple[i] for i in range(len(group_names))):
                next_remaining = tuple(remaining_tuple[i] - values[i] for i in range(len(group_names)))
                result = solve(rows_left - 1, next_remaining)
                if result is not None:
                    return (values,) + result
        return None

    solution = solve(base_count, tuple(used[group] for group in group_names))
    if solution is not None:
        return [dict(zip(group_names, values)) for values in solution], used
    raise ValueError(f"無法建立可行配額：{group_names} {sizes}")


def generate_dynamic_bets(candidate_groups, pool_name, main_group, seed):
    """依動態候選池產生不重複基本注及餘球補球注。"""
    rng = random.Random(seed)
    group_names = pool_name.split("+")
    numbers = {group: list(candidate_groups[group]) for group in group_names}
    for values in numbers.values():
        rng.shuffle(values)
    sizes = {group: len(values) for group, values in numbers.items()}
    total = sum(sizes.values())
    if total < 6:
        raise ValueError(f"候選球池不足 6 球：{pool_name}={total}")
    base_count = total // 6
    quotas, used = _quota_matrix(group_names, sizes, base_count, main_group, rng)
    basic = []
    for quota in quotas:
        ticket = []
        for group, count in quota.items():
            ticket.extend(numbers[group][:count])
            del numbers[group][:count]
        basic.append(tuple(sorted(ticket)))
    remainder = sorted(number for values in numbers.values() for number in values)
    if remainder:
        need = 6 - len(remainder)
        source = [number for ticket in basic for number in ticket]
        supplement = remainder + rng.sample(source, need)
        basic.append(tuple(sorted(supplement)))
    return basic, {"quota": quotas, "remainder": remainder, "pool_size": total, "base_count": base_count}


def limit_previous_overlap(bets, candidate_groups, previous_numbers, seed):
    """將每注與上一期 N1–N7 的重複號碼限制在最多 2 球。"""
    rng = random.Random(seed)
    previous = set(previous_numbers)
    repaired = []
    for ticket in bets:
        values = list(ticket)
        repeated = [number for number in values if number in previous]
        if len(repeated) > 2:
            replacements = []
            for number in repeated[2:]:
                group = next((name for name, pool in candidate_groups.items() if number in pool), None)
                if group is None:
                    continue
                choices = [
                    candidate for candidate in candidate_groups[group]
                    if candidate not in previous and candidate not in values and candidate not in replacements
                ]
                if choices:
                    replacements.append((number, rng.choice(choices)))
            for old, new in replacements:
                values[values.index(old)] = new
        repaired.append(tuple(sorted(values)))
    return repaired
