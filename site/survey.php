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
$phase = $progress['phase'];
$idx = $progress['item_index'];

$assignment = parse_assignment((string)$p['item_order_json']);
// Re-read assignment in case sync refreshed row state from last_step only
$p = db_one('SELECT * FROM participants WHERE id = ?', [(int)$p['id']]) ?? $p;
$assignment = parse_assignment((string)$p['item_order_json']);
$order = assignment_order($assignment);
if (!$order) {
    http_response_code(500);
    exit('Invalid assignment');
}

$lang = $p['lang'];
$umCol = $lang === 'pt' ? 'user_message_pt' : 'user_message_en';
$arCol = $lang === 'pt' ? 'assistant_response_pt' : 'assistant_response_en';
$coreLen = count($assignment['core']);
$bonusMode = !empty($assignment['unlocked']) && $phase === 'main' && $idx >= $coreLen;

$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? 'rate';
    if ($action === 'stop' && $bonusMode) {
        touch_participant((int)$p['id'], 'attention', [
            'item_index' => $idx,
            'phase' => 'main',
        ]);
        header('Location: attention.php');
        exit;
    }

    $score = (int)($_POST['score'] ?? 0);
    if ($score < 1 || $score > 7) {
        $error = t('required');
    } elseif ($phase === 'practice') {
        touch_participant((int)$p['id'], 'survey', [
            'phase' => 'main',
            'item_index' => 0,
        ]);
        $_SESSION['phase'] = 'main';
        $_SESSION['item_index'] = 0;
        header('Location: survey.php');
        exit;
    } else {
        $itemId = $order[$idx] ?? null;
        if (!$itemId) {
            header('Location: continue_offer.php');
            exit;
        }
        save_rating((int)$p['id'], (string)$itemId, $score, $idx + 1);
        $idx++;
        $_SESSION['item_index'] = $idx;
        $_SESSION['phase'] = 'main';
        if ($idx >= count($order)) {
            if (!empty($assignment['unlocked'])) {
                touch_participant((int)$p['id'], 'attention', [
                    'item_index' => $idx,
                    'phase' => 'main',
                ]);
                header('Location: attention.php');
            } else {
                touch_participant((int)$p['id'], 'continue_offer', [
                    'item_index' => $idx,
                    'phase' => 'main',
                ]);
                header('Location: continue_offer.php');
            }
            exit;
        }
        touch_participant((int)$p['id'], $bonusMode ? 'survey_bonus' : 'survey', [
            'item_index' => $idx,
            'phase' => 'main',
        ]);
        header('Location: survey.php');
        exit;
    }
}

$cfg = app_config();
$practiceId = $cfg['practice_item_id'] ?? null;
if (!$practiceId) {
    $practiceId = (string)db_value('SELECT item_id FROM items ORDER BY item_id LIMIT 1');
}

if ($phase === 'practice') {
    $item = db_one('SELECT * FROM items WHERE item_id = ?', [(string)$practiceId]);
    $title = t('practice_title');
    $progressLabel = $title;
    $bonusMode = false;
} else {
    if ($idx >= count($order)) {
        header('Location: ' . (!empty($assignment['unlocked']) ? 'attention.php' : 'continue_offer.php'));
        exit;
    }
    $item = db_one('SELECT * FROM items WHERE item_id = ?', [(string)$order[$idx]]);
    $title = t('site_title');
    if ($bonusMode) {
        $extraPos = $idx - $coreLen + 1;
        $extraTotal = max(1, count($assignment['extra']));
        $left = max(0, count($order) - $idx);
        $progressLabel = sprintf(t('progress_bonus'), $extraPos, $extraTotal, $left);
    } else {
        $progressLabel = sprintf(t('progress'), $idx + 1, $coreLen);
    }
}

if (!$item) {
    http_response_code(500);
    exit('Missing item in catalog');
}

$userText = $item[$umCol] ?: $item['user_message_en'];
$asstText = $item[$arCol] ?: $item['assistant_response_en'];

layout_start($title);
?>
<p class="progress"><?= htmlspecialchars($progressLabel, ENT_QUOTES, 'UTF-8') ?></p>
<p class="note"><?= htmlspecialchars(t('autosave_note'), ENT_QUOTES, 'UTF-8') ?></p>
<?php if ($bonusMode): ?>
  <p class="note bonus-note"><?= htmlspecialchars(t('bonus_stop_hint'), ENT_QUOTES, 'UTF-8') ?></p>
<?php endif; ?>
<div class="card">
  <?php if ($phase === 'practice'): ?>
    <h1><?= htmlspecialchars(t('practice_title'), ENT_QUOTES, 'UTF-8') ?></h1>
  <?php endif; ?>
  <p><strong><?= htmlspecialchars(t('survey_instruction'), ENT_QUOTES, 'UTF-8') ?></strong></p>
  <div class="label"><?= htmlspecialchars(t('user_message'), ENT_QUOTES, 'UTF-8') ?></div>
  <div class="bubble"><?= htmlspecialchars($userText, ENT_QUOTES, 'UTF-8') ?></div>
  <div class="label"><?= htmlspecialchars(t('assistant_response'), ENT_QUOTES, 'UTF-8') ?></div>
  <div class="bubble"><?= htmlspecialchars($asstText, ENT_QUOTES, 'UTF-8') ?></div>
  <?php if ($error): ?><p class="error"><?= htmlspecialchars($error, ENT_QUOTES, 'UTF-8') ?></p><?php endif; ?>
  <form method="post">
    <input type="hidden" name="action" value="rate">
    <div class="scale">
      <?php for ($s = 1; $s <= 7; $s++): ?>
        <label>
          <input type="radio" name="score" value="<?= $s ?>" required>
          <span><?= $s ?></span>
        </label>
      <?php endfor; ?>
    </div>
    <div class="anchors">
      <span><?= htmlspecialchars(t('scale_low'), ENT_QUOTES, 'UTF-8') ?></span>
      <span><?= htmlspecialchars(t('scale_high'), ENT_QUOTES, 'UTF-8') ?></span>
    </div>
    <div class="actions">
      <button type="submit"><?= htmlspecialchars(t('continue'), ENT_QUOTES, 'UTF-8') ?></button>
    </div>
  </form>
  <?php if ($bonusMode): ?>
    <form method="post" class="actions stop-actions">
      <button type="submit" name="action" value="stop" class="secondary"><?= htmlspecialchars(t('bonus_stop'), ENT_QUOTES, 'UTF-8') ?></button>
    </form>
  <?php endif; ?>
</div>
<?php layout_end(); ?>
