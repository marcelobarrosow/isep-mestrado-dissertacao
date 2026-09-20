<?php
declare(strict_types=1);

/** 8 blocks of 12 item_ids after seed-42 shuffle of the full catalog. */
function build_blocks(): array
{
    $rows = db_all('SELECT item_id FROM items ORDER BY item_id');
    $ids = array_map(static fn($r) => (string)$r['item_id'], $rows);
    if (count($ids) < 8) {
        throw new RuntimeException('Catalog too small; import items first.');
    }
    $seed = 42;
    mt_srand($seed);
    for ($i = count($ids) - 1; $i > 0; $i--) {
        $j = mt_rand(0, $i);
        [$ids[$i], $ids[$j]] = [$ids[$j], $ids[$i]];
    }
    mt_srand();

    $blocks = array_chunk($ids, 12);
    $blocks = array_slice($blocks, 0, 8);
    while (count($blocks) < 8) {
        $blocks[] = [];
    }
    return $blocks;
}

function blocks_for_participant_index(int $index1based): array
{
    // 15 block-pair combinations; session index uses modulo. This is the
    // rotation cycle length, not the sample size (156 / 63 / 52).
    $plan = [
        [0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 0],
        [0, 2], [1, 3], [4, 6], [5, 7], [0, 4], [1, 5], [2, 6],
    ];
    $i = ($index1based - 1) % count($plan);
    return $plan[$i];
}

function ordered_items_for_participant(int $participantId, int $blockA, int $blockB): array
{
    $blocks = build_blocks();
    $ids = array_values(array_unique(array_merge($blocks[$blockA] ?? [], $blocks[$blockB] ?? [])));
    mt_srand(42 + $participantId);
    for ($i = count($ids) - 1; $i > 0; $i--) {
        $j = mt_rand(0, $i);
        [$ids[$i], $ids[$j]] = [$ids[$j], $ids[$i]];
    }
    mt_srand();
    return $ids;
}

/** @return list<string> */
function all_item_ids(): array
{
    $rows = db_all('SELECT item_id FROM items ORDER BY item_id');
    return array_map(static fn($r) => (string)$r['item_id'], $rows);
}

/**
 * Assignment payload (back-compat with legacy flat JSON arrays).
 *
 * @return array{core: list<string>, extra: list<string>, unlocked: bool}
 */
function parse_assignment(?string $json): array
{
    $data = json_decode((string)$json, true);
    if (!is_array($data) || $data === []) {
        return ['core' => [], 'extra' => [], 'unlocked' => false];
    }
    if (array_is_list($data)) {
        return [
            'core' => array_values(array_map('strval', $data)),
            'extra' => [],
            'unlocked' => false,
        ];
    }
    $core = isset($data['core']) && is_array($data['core'])
        ? array_values(array_map('strval', $data['core']))
        : [];
    $extra = isset($data['extra']) && is_array($data['extra'])
        ? array_values(array_map('strval', $data['extra']))
        : [];
    return [
        'core' => $core,
        'extra' => $extra,
        'unlocked' => !empty($data['unlocked']),
    ];
}

function encode_assignment(array $assignment): string
{
    return json_encode([
        'core' => array_values($assignment['core'] ?? []),
        'extra' => array_values($assignment['extra'] ?? []),
        'unlocked' => !empty($assignment['unlocked']),
    ], JSON_UNESCAPED_UNICODE);
}

/** Active item list for the current participant state. */
function assignment_order(array $assignment): array
{
    $core = $assignment['core'] ?? [];
    if (!empty($assignment['unlocked'])) {
        return array_values(array_merge($core, $assignment['extra'] ?? []));
    }
    return array_values($core);
}

function make_core_assignment(int $participantId, int $blockA, int $blockB): array
{
    return [
        'core' => ordered_items_for_participant($participantId, $blockA, $blockB),
        'extra' => [],
        'unlocked' => false,
    ];
}

/** Remaining catalog items (not in core), shuffled per participant. */
function bonus_items_for_participant(int $participantId, array $coreIds): array
{
    $left = array_values(array_diff(all_item_ids(), $coreIds));
    mt_srand(9000 + $participantId);
    for ($i = count($left) - 1; $i > 0; $i--) {
        $j = mt_rand(0, $i);
        [$left[$i], $left[$j]] = [$left[$j], $left[$i]];
    }
    mt_srand();
    return $left;
}

function unlock_bonus_assignment(int $participantId, array $assignment): array
{
    $core = $assignment['core'] ?? [];
    $assignment['extra'] = bonus_items_for_participant($participantId, $core);
    $assignment['unlocked'] = true;
    return $assignment;
}
