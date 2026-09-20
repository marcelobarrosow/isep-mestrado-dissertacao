<?php
declare(strict_types=1);
require_once __DIR__ . '/lib/bootstrap.php';
$p = require_participant();
set_lang($p['lang']);
if (!(int)$p['consent'] || empty($p['item_order_json'])) {
    header('Location: consent.php');
    exit;
}
if (($p['status'] ?? '') === 'completed') {
    header('Location: thanks.php');
    exit;
}

$progress = sync_progress_from_db($p);
$p = db_one('SELECT * FROM participants WHERE id = ?', [(int)$p['id']]) ?? $p;
$assignment = parse_assignment((string)$p['item_order_json']);
$order = assignment_order($assignment);
$idx = $progress['item_index'];

if ($idx < count($order)) {
    header('Location: survey.php');
    exit;
}

if (!empty($assignment['unlocked'])) {
    touch_participant((int)$p['id'], 'attention', [
        'item_index' => $idx,
        'phase' => 'main',
    ]);
    header('Location: attention.php');
    exit;
}

$bonusPreview = bonus_items_for_participant((int)$p['id'], $assignment['core']);
$remaining = count($bonusPreview);

if ($remaining === 0) {
    touch_participant((int)$p['id'], 'attention', [
        'item_index' => $idx,
        'phase' => 'main',
    ]);
    header('Location: attention.php');
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $choice = $_POST['choice'] ?? '';
    if ($choice === 'stop') {
        touch_participant((int)$p['id'], 'attention', [
            'item_index' => $idx,
            'phase' => 'main',
        ]);
        header('Location: attention.php');
        exit;
    }
    if ($choice === 'continue') {
        $unlocked = unlock_bonus_assignment((int)$p['id'], $assignment);
        $coreLen = count($unlocked['core']);
        touch_participant((int)$p['id'], 'survey_bonus', [
            'item_order_json' => encode_assignment($unlocked),
            'item_index' => $coreLen,
            'phase' => 'main',
            'status' => 'in_progress',
        ]);
        $_SESSION['phase'] = 'main';
        $_SESSION['item_index'] = $coreLen;
        header('Location: survey.php');
        exit;
    }
}

touch_participant((int)$p['id'], 'continue_offer', [
    'item_index' => $idx,
    'phase' => 'main',
]);

$coreDone = count($assignment['core']);
layout_start(t('continue_offer_title'));
?>
<header class="offer-hero">
  <p class="admin-kicker"><?= htmlspecialchars(t('continue_offer_kicker'), ENT_QUOTES, 'UTF-8') ?></p>
  <h1><?= htmlspecialchars(t('continue_offer_title'), ENT_QUOTES, 'UTF-8') ?></h1>
  <p class="admin-lead"><?= htmlspecialchars(sprintf(t('continue_offer_body'), $coreDone, $remaining), ENT_QUOTES, 'UTF-8') ?></p>
</header>
<div class="card">
  <p><?= htmlspecialchars(t('continue_offer_note'), ENT_QUOTES, 'UTF-8') ?></p>
  <form method="post" class="actions offer-actions">
    <button type="submit" name="choice" value="continue"><?= htmlspecialchars(t('continue_offer_yes'), ENT_QUOTES, 'UTF-8') ?></button>
    <button type="submit" name="choice" value="stop" class="secondary"><?= htmlspecialchars(t('continue_offer_no'), ENT_QUOTES, 'UTF-8') ?></button>
  </form>
</div>
<?php layout_end(); ?>
