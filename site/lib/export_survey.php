<?php
declare(strict_types=1);

/** Pause longer than this is treated as a break, not item reading time. */
const EXPORT_MAX_ITEM_GAP_SECONDS = 600;
/** Minimum valid item times before a participant can be flagged. */
const EXPORT_MIN_VALID_TIMES = 10;
/** One-sided robust fence: mediana − k × DAM. */
const EXPORT_MAD_K = 2.5;

/**
 * @param list<float|int> $values
 */
function export_median(array $values): ?float
{
    $n = count($values);
    if ($n === 0) {
        return null;
    }
    $xs = array_values($values);
    sort($xs, SORT_NUMERIC);
    $mid = intdiv($n, 2);
    if ($n % 2 === 1) {
        return (float)$xs[$mid];
    }
    return ((float)$xs[$mid - 1] + (float)$xs[$mid]) / 2.0;
}

/**
 * Median absolute deviation around $center.
 *
 * @param list<float|int> $values
 */
function export_mad(array $values, float $center): ?float
{
    if (!$values) {
        return null;
    }
    $devs = [];
    foreach ($values as $x) {
        $devs[] = abs((float)$x - $center);
    }
    return export_median($devs);
}

function export_parse_time(mixed $value): ?int
{
    $s = trim((string)$value);
    if ($s === '') {
        return null;
    }
    $t = strtotime($s);
    return $t === false ? null : $t;
}

/**
 * Per-item times, participant relative pace, and too-fast flags for this export.
 *
 * @param list<array<string,mixed>> $rows
 * @return array{
 *   item_medians: array<string,float>,
 *   item_time: array<string,array<string,float>>,
 *   relative: array<string,array<string,float>>,
 *   pace: array<string,float>,
 *   too_fast: array<string,true>,
 *   cutoff: float|null,
 *   pace_median: float|null,
 *   pace_mad: float|null
 * }
 */
function export_compute_timing(array $rows): array
{
    $byParticipant = [];
    $meta = [];
    foreach ($rows as $row) {
        $pid = (string)($row['participant_id'] ?? '');
        if ($pid === '') {
            continue;
        }
        $meta[$pid] = $row;
        $itemId = trim((string)($row['item_id'] ?? ''));
        if ($itemId === '') {
            continue;
        }
        $byParticipant[$pid][] = $row;
    }

    /** @var array<string,list<float>> $itemTimes */
    $itemTimes = [];
    /** @var array<string,array<string,float>> $itemTime */
    $itemTime = [];

    foreach ($byParticipant as $pid => $list) {
        usort($list, static function (array $a, array $b): int {
            return (int)($a['position'] ?? 0) <=> (int)($b['position'] ?? 0);
        });
        $prevTs = null;
        $isFirst = true;
        foreach ($list as $row) {
            $ts = export_parse_time($row['answered_at'] ?? null);
            if ($isFirst) {
                $isFirst = false;
                if ($ts !== null) {
                    $prevTs = $ts;
                }
                continue;
            }
            if ($ts !== null && $prevTs !== null) {
                $dt = $ts - $prevTs;
                if ($dt > 0 && $dt <= EXPORT_MAX_ITEM_GAP_SECONDS) {
                    $iid = (string)$row['item_id'];
                    $sec = (float)$dt;
                    $itemTimes[$iid][] = $sec;
                    $itemTime[$pid][$iid] = $sec;
                }
            }
            if ($ts !== null) {
                $prevTs = $ts;
            }
        }
    }

    $itemMedians = [];
    foreach ($itemTimes as $iid => $xs) {
        $m = export_median($xs);
        if ($m !== null && $m > 0) {
            $itemMedians[$iid] = $m;
        }
    }

    /** @var array<string,array<string,float>> $relative */
    $relative = [];
    /** @var array<string,list<float>> $relLists */
    $relLists = [];
    foreach ($itemTime as $pid => $items) {
        foreach ($items as $iid => $dt) {
            $med = $itemMedians[$iid] ?? null;
            if ($med === null || $med <= 0) {
                continue;
            }
            $rel = $dt / $med;
            $relative[$pid][$iid] = $rel;
            $relLists[$pid][] = $rel;
        }
    }

    $pace = [];
    foreach ($relLists as $pid => $rels) {
        $m = export_median($rels);
        if ($m !== null) {
            $pace[$pid] = $m;
        }
    }

    $reference = [];
    foreach ($pace as $pid => $p) {
        $row = $meta[$pid] ?? [];
        $nTimes = count($relLists[$pid] ?? []);
        $att = (string)($row['attention_ok'] ?? '');
        $status = (string)($row['status'] ?? '');
        if ($status === 'completed' && $att === '1' && $nTimes >= EXPORT_MIN_VALID_TIMES) {
            $reference[] = $p;
        }
    }

    $paceMedian = export_median($reference);
    $paceMad = $paceMedian === null ? null : export_mad($reference, $paceMedian);
    $cutoff = null;
    $tooFast = [];
    if ($paceMedian !== null && $paceMad !== null && $paceMad > 0) {
        $cutoff = $paceMedian - EXPORT_MAD_K * $paceMad;
        foreach ($pace as $pid => $p) {
            $nTimes = count($relLists[$pid] ?? []);
            if ($nTimes >= EXPORT_MIN_VALID_TIMES && $p < $cutoff) {
                $tooFast[$pid] = true;
            }
        }
    }

    return [
        'item_medians' => $itemMedians,
        'item_time' => $itemTime,
        'relative' => $relative,
        'pace' => $pace,
        'too_fast' => $tooFast,
        'cutoff' => $cutoff,
        'pace_median' => $paceMedian,
        'pace_mad' => $paceMad,
    ];
}

function export_fmt_number(?float $value, int $decimals): string
{
    if ($value === null) {
        return '';
    }
    return number_format($value, $decimals, '.', '');
}

function export_fmt_seconds(?float $value): string
{
    if ($value === null) {
        return '';
    }
    if (abs($value - round($value)) < 0.05) {
        return (string)(int)round($value);
    }
    return number_format($value, 1, '.', '');
}

function export_label_lang(string $lang): string
{
    return match ($lang) {
        'pt' => 'Português',
        'en' => 'Inglês',
        default => $lang,
    };
}

function export_label_status(string $status): string
{
    return match ($status) {
        'in_progress' => 'em curso',
        'completed' => 'concluído',
        'abandoned' => 'abandonado',
        default => $status,
    };
}

function export_label_attention(mixed $value): string
{
    $s = trim((string)$value);
    if ($s === '') {
        return '';
    }
    return $s === '1' ? 'Sim' : 'Não';
}

function export_label_condition(string $condition): string
{
    return match ($condition) {
        'baseline' => 'linha de base',
        'pipeline' => 'pipeline',
        default => $condition,
    };
}

function export_motivo_exclusao(array $row, bool $tooFast): string
{
    $db = trim((string)($row['excluded_reason'] ?? ''));
    if ($db === 'attention_fail') {
        return 'falha no item de atenção';
    }
    if ($db === 'no_consent') {
        return 'sem consentimento';
    }
    if ($tooFast) {
        return 'ritmo demasiado rápido';
    }
    return '';
}

/**
 * @param array<string,mixed> $row
 * @param array<string,mixed> $timing
 * @return array<string,string>
 */
function export_map_row(array $row, array $timing): array
{
    $pid = (string)($row['participant_id'] ?? '');
    $itemId = trim((string)($row['item_id'] ?? ''));
    $tooFast = isset($timing['too_fast'][$pid]);
    $seconds = $itemId !== '' ? ($timing['item_time'][$pid][$itemId] ?? null) : null;
    $itemMed = $itemId !== '' ? ($timing['item_medians'][$itemId] ?? null) : null;
    $rel = $itemId !== '' ? ($timing['relative'][$pid][$itemId] ?? null) : null;
    $hasPace = isset($timing['pace'][$pid]);

    return [
        'participante' => $pid,
        'idioma' => export_label_lang((string)($row['lang'] ?? '')),
        'estado' => export_label_status((string)($row['status'] ?? '')),
        'atenção' => export_label_attention($row['attention_ok'] ?? ''),
        'motivo de exclusão' => export_motivo_exclusao($row, $tooFast),
        'início' => (string)($row['started_at'] ?? ''),
        'conclusão' => (string)($row['finished_at'] ?? ''),
        'última actualização' => (string)($row['updated_at'] ?? ''),
        'código do item' => $itemId,
        'classificação' => (string)($row['score'] ?? ''),
        'ordem' => (string)($row['position'] ?? ''),
        'respondido em' => (string)($row['answered_at'] ?? ''),
        'estímulo' => (string)($row['stimulus_id'] ?? ''),
        'época' => (string)($row['epoch_id'] ?? ''),
        'condição' => export_label_condition((string)($row['condition'] ?? '')),
        'modelo' => (string)($row['model_id'] ?? ''),
        'tempo da resposta (s)' => export_fmt_seconds($seconds),
        'mediana do item (s)' => export_fmt_seconds($itemMed),
        'ritmo relativo' => $rel === null ? '' : export_fmt_number($rel, 3),
        'ritmo demasiado rápido' => $hasPace ? ($tooFast ? 'Sim' : 'Não') : '',
    ];
}

/** @return list<string> */
function export_csv_headers(): array
{
    return [
        'participante',
        'idioma',
        'estado',
        'atenção',
        'motivo de exclusão',
        'início',
        'conclusão',
        'última actualização',
        'código do item',
        'classificação',
        'ordem',
        'respondido em',
        'estímulo',
        'época',
        'condição',
        'modelo',
        'tempo da resposta (s)',
        'mediana do item (s)',
        'ritmo relativo',
        'ritmo demasiado rápido',
    ];
}
