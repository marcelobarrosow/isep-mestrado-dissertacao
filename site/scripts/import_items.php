<?php
declare(strict_types=1);
/**
 * CLI-only importer. From the web admin panel use /admin/import.php (session + CSRF).
 *
 * Usage: php scripts/import_items.php [--replace]
 */
require_once dirname(__DIR__) . '/lib/bootstrap.php';

if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    exit('Forbidden — use the admin panel to reimport.');
}

$cfg = app_config();

$csvPath = dirname(__DIR__) . '/data/questionnaire_items_i18n.csv';
if (!is_file($csvPath)) {
    fwrite(STDERR, "Missing $csvPath\n");
    exit(1);
}

$replace = in_array('--replace', $argv ?? [], true);

if ($replace) {
    $ratings = (int)db_value('SELECT COUNT(*) AS c FROM ratings');
    if ($ratings > 0) {
        fwrite(STDERR, "Cannot --replace while ratings exist ($ratings rows).\n");
        exit(1);
    }
    db()->query('DELETE FROM items');
}

$sql = 'INSERT INTO items (
          item_id, stimulus_id, user_message_en, assistant_response_en,
          user_message_pt, assistant_response_pt, epoch_id, model_id, condition_name
        ) VALUES (?,?,?,?,?,?,?,?,?)
        ON DUPLICATE KEY UPDATE
          stimulus_id=VALUES(stimulus_id),
          user_message_en=VALUES(user_message_en),
          assistant_response_en=VALUES(assistant_response_en),
          user_message_pt=VALUES(user_message_pt),
          assistant_response_pt=VALUES(assistant_response_pt),
          epoch_id=VALUES(epoch_id),
          model_id=VALUES(model_id),
          condition_name=VALUES(condition_name)';

$fh = fopen($csvPath, 'r');
$header = fgetcsv($fh);
$n = 0;
while (($row = fgetcsv($fh)) !== false) {
    $data = array_combine($header, $row);
    if (!$data || empty($data['item_id'])) {
        continue;
    }
    db_exec($sql, [
        $data['item_id'],
        $data['stimulus_id'],
        $data['user_message_en'],
        $data['assistant_response_en'],
        $data['user_message_pt'] ?: $data['user_message_en'],
        $data['assistant_response_pt'] ?: $data['assistant_response_en'],
        $data['epoch_id'],
        $data['model_id'],
        $data['condition'],
    ]);
    $n++;
}
fclose($fh);

echo "Imported/updated $n items\n";
