"""S5 v2 動態候選球池及主力／配腳配額。"""
from __future__ import annotations

import random
from functools import lru_cache
from itertools import combinations, product

try:
    from .s5_v2_config import GROUPS
except ImportError:
    from s5_v2_config import GROUPS

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


def _has_group_triple(numbers, group_names):
    """檢查同一分組是否同時含 n、n+1、n+2。"""
    selected = set(numbers)
    return any(
        number in selected and number + 1 in selected and number + 2 in selected
        for group in group_names
        for number in GROUPS[group]
    )


def _build_basic_bets(candidate_groups, group_names, quotas, previous_numbers, rng, node_limit=50000):
    """分配基本注，並找出同樣符合限制的內部補球注。"""
    assigned = {group: set() for group in group_names}
    previous = set(previous_numbers)
    nodes = 0

    def build_row(row_index, completed):
        nonlocal nodes
        if row_index == len(quotas):
            if not all(
                len(assigned[group]) == sum(row[group] for row in quotas)
                for group in group_names
            ):
                return None
            reserved = [
                number
                for group in group_names
                for number in candidate_groups[group]
                if number not in assigned[group]
            ]
            if len(reserved) > 6:
                return None
            source = [number for ticket in completed for number in ticket if number not in reserved]
            need = 6 - len(reserved)
            for _ in range(3000):
                if len(source) < need:
                    return None
                supplement = tuple(sorted(reserved + rng.sample(source, need)))
                if len(set(supplement)) != 6:
                    continue
                if supplement in completed or _has_group_triple(supplement, group_names):
                    continue
                if len(set(supplement) & previous) > 2:
                    continue
                return completed + [supplement]
            return None

        quota = quotas[row_index]
        row_numbers = []
        ordered_groups = sorted(group_names, key=lambda g: len(list(combinations(candidate_groups[g], quota[g]))))

        def choose_group(group_index):
            nonlocal nodes
            if nodes >= node_limit:
                return None
            if group_index == len(ordered_groups):
                ticket = tuple(sorted(row_numbers))
                if len(ticket) != 6 or len(set(ticket)) != 6:
                    return None
                if _has_group_triple(ticket, group_names):
                    return None
                if len(set(ticket) & previous) > 2:
                    return None
                result = build_row(row_index + 1, completed + [ticket])
                if result is not None:
                    return result
                return None

            group = ordered_groups[group_index]
            needed = quota[group]
            available = [n for n in candidate_groups[group] if n not in assigned[group]]
            options = [choice for choice in combinations(available, needed) if not _has_group_triple(choice, [group])]
            rng.shuffle(options)
            for choice in options:
                nodes += 1
                assigned[group].update(choice)
                row_numbers.extend(choice)
                result = choose_group(group_index + 1)
                if result is not None:
                    return result
                del row_numbers[-len(choice):]
                assigned[group].difference_update(choice)
                if nodes >= node_limit:
                    break
            return None

        return choose_group(0)

    return build_row(0, [])


def generate_dynamic_bets(candidate_groups, pool_name, main_group, seed, previous_numbers=()):
    """產生基本注；候選球有餘數時才輸出補球注。"""
    rng = random.Random(seed)
    group_names = pool_name.split("+")
    original_numbers = {group: list(dict.fromkeys(candidate_groups[group])) for group in group_names}
    original_total = sum(len(values) for values in original_numbers.values())
    if original_total < 6:
        raise ValueError(f"候選球池不足 6 球：{pool_name}={original_total}")

    base_count = original_total // 6
    extra_trials = []
    if original_total % 6 == 0:
        previous = set(previous_numbers)
        possible_by_group = {}
        for group in group_names:
            possible = [number for number in GROUPS[group] if number not in original_numbers[group]]
            rng.shuffle(possible)
            possible.sort(key=lambda number: number in previous)
            if possible:
                possible_by_group[group] = possible[:2]
        # Try one alternative internal ball per eligible group; a second candidate
        # is retained to handle cases where the first creates an awkward quota.
        extra_trials = [(group, number) for group, values in possible_by_group.items() for number in values]
        rng.shuffle(extra_trials)
    # If no distinct same-group ball exists, or all augmented layouts fail, try
    # the original pool. The hidden adjustment ball never changes output count.
    extra_trials.append(None)

    last_quota_error = None
    for extra_index, extra_ball in enumerate(extra_trials):
        numbers = {group: values.copy() for group, values in original_numbers.items()}
        if extra_ball is not None:
            numbers[extra_ball[0]].append(extra_ball[1])
        sizes = {group: len(values) for group, values in numbers.items()}
        for quota_attempt in range(4):
            attempt_rng = random.Random(seed + extra_index * 1009 + quota_attempt)
            try:
                quotas, _used = _quota_matrix(group_names, sizes, base_count, main_group, attempt_rng)
            except ValueError as error:
                last_quota_error = error
                continue

            # Search several randomized quota matrices before trying another
            # internal buffer-ball choice or the original candidate pool.
            basic = _build_basic_bets(
                numbers,
                group_names,
                quotas,
                previous_numbers,
                attempt_rng,
                node_limit=100000,
            )
            if basic is None:
                continue

            basic_bets = basic[:base_count]
            supplement = basic[base_count] if len(basic) > base_count else None
            used_numbers = {number for ticket in basic_bets for number in ticket}
            buffer_numbers = sorted(
                number for values in numbers.values() for number in values if number not in used_numbers
            )
            output_bets = basic_bets
            if original_total % 6:
                if supplement is None:
                    continue
                output_bets = basic_bets + [supplement]
            return output_bets, {
                "quota": quotas,
                "remainder": buffer_numbers,
                "pool_size": original_total,
                "base_count": base_count,
                "internal_extra_ball": extra_ball,
                "supplement": supplement if original_total % 6 else None,
            }

    detail = f"；配額錯誤：{last_quota_error}" if last_quota_error else ""
    raise ValueError(
        f"{pool_name} 嘗試不同內部補球及配額後，仍找不到符合條件的基本注 "
        f"（同組不可三連號、上期重複最多 2 球）{detail}。"
    )


def limit_previous_overlap(bets, candidate_groups, previous_numbers, seed):
    """最終檢查每注六球、同組無三連號，且與上一期最多重複兩球。"""
    previous = set(previous_numbers)
    groups = list(candidate_groups)
    for index, ticket in enumerate(bets, start=1):
        if len(ticket) != 6 or len(set(ticket)) != 6:
            raise ValueError(f"第 {index} 注不是六個不同號碼：{ticket}")
        if _has_group_triple(ticket, groups):
            raise ValueError(f"第 {index} 注有同組三連號：{ticket}")
        overlap = len(set(ticket) & previous)
        if overlap > 2:
            raise ValueError(f"第 {index} 注與上一期重複 {overlap} 球，超過上限 2 球：{ticket}")
    return bets
