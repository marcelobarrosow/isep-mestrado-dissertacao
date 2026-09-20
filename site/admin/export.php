<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/lib/bootstrap.php';
require_once dirname(__DIR__) . '/lib/export_survey.php';

$cfg = app_config();
require_admin_ip($cfg);

if (empty($_SESSION['admin_ok'])) {
    header('Location: index.php');
    exit;
}

$sql = 'SELECT
          p.id AS participant_id,
          p.lang,
          p.status,
          p.attention_ok,
          p.excluded_reason,
          p.started_at,
          p.finished_at,
          p.updated_at,
          r.item_id,
          r.score,
          r.position,
          r.answered_at,
          i.stimulus_id,
          i.epoch_id,
          i.condition_name AS `condition`,
          i.model_id
        FROM participants p
        LEFT JOIN ratings r ON r.participant_id = p.id
        LEFT JOIN items i ON i.item_id = r.item_id
        ORDER BY p.id, r.position';

$rows = db_all($sql);
$timing = export_compute_timing($rows);
$headers = export_csv_headers();

header('Content-Type: text/csv; charset=utf-8');
header('Content-Disposition: attachment; filename="exportacao_questionario_' . date('Ymd_His') . '.csv"');
$out = fopen('php://output', 'w');
fprintf($out, "\xEF\xBB\xBF");
fputcsv($out, $headers);
foreach ($rows as $row) {
    $mapped = export_map_row($row, $timing);
    fputcsv($out, array_map(static fn($k) => $mapped[$k] ?? '', $headers));
}
fclose($out);
exit;
