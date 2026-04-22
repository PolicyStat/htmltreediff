def build_pairwise_match_matrix(old_hashes, new_hashes):
    n = len(old_hashes)
    m = len(new_hashes)
    match_matrix = [[False] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            match_matrix[i][j] = (old_hashes[i] == new_hashes[j])
    return match_matrix


def compute_longest_common_subsequence_lengths_table(match_matrix):
    n = len(match_matrix)
    m = len(match_matrix[0]) if n > 0 else 0
    lcs_lengths = [[0] * (m + 1) for _ in range(n + 1)]
    for i in reversed(range(n)):
        for j in reversed(range(m)):
            if match_matrix[i][j]:
                lcs_lengths[i][j] = 1 + lcs_lengths[i + 1][j + 1]
            else:
                lcs_lengths[i][j] = max(lcs_lengths[i + 1][j], lcs_lengths[i][j + 1])
    return lcs_lengths


def traceback_longest_common_subsequence_matched_pairs(match_matrix, lcs_lengths):
    n = len(match_matrix)
    m = len(match_matrix[0]) if n > 0 else 0
    matched_pairs = []
    i, j = 0, 0
    while i < n and j < m:
        if match_matrix[i][j] and lcs_lengths[i][j] == 1 + lcs_lengths[i + 1][j + 1]:
            matched_pairs.append((i, j))
            i += 1
            j += 1
        elif lcs_lengths[i + 1][j] >= lcs_lengths[i][j + 1]:
            i += 1
        else:
            j += 1
    return matched_pairs


def group_consecutive_pairs_into_blocks(matched_pairs, n, m):
    blocks = []
    k = 0
    while k < len(matched_pairs):
        a, b = matched_pairs[k]
        size = 1
        while (
            k + size < len(matched_pairs) and matched_pairs[k + size] == (a + size, b + size)
        ):
            size += 1
        blocks.append((a, b, size))
        k += size
    blocks.append((n, m, 0))  # sentinel
    return blocks


def matching_blocks_from_hashes(old_hashes, new_hashes):
    n = len(old_hashes)
    m = len(new_hashes)
    match_matrix = build_pairwise_match_matrix(old_hashes, new_hashes)
    lcs_lengths = compute_longest_common_subsequence_lengths_table(match_matrix)
    matched_pairs = traceback_longest_common_subsequence_matched_pairs(
        match_matrix,
        lcs_lengths,
    )
    return group_consecutive_pairs_into_blocks(matched_pairs, n, m)
