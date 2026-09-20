<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/lib/bootstrap.php';

$cfg = app_config();
require_admin_ip($cfg);
require_admin_session();

if ($_SERVER['REQUEST_METHOD'] !== 'POST' || !csrf_verify($_POST['_csrf'] ?? null)) {
    http_response_code(403);
    exit('Forbidden');
}

$csvPath = dirname(__DIR__) . '/data/questionnaire_items_i18n.csv';
if (!is_file($csvPath)) {
    http_response_code(500);
    exit('Missing questionnaire CSV on server.');
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
if ($fh === false) {
    http_response_code(500);
    exit('Cannot read questionnaire CSV.');
}
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

header('Location: /admin/index.php?importado=' . $n);
exit;
