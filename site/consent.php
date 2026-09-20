<?php
declare(strict_types=1);
require_once __DIR__ . '/lib/bootstrap.php';
$p = require_participant();
if (($p['lang'] ?? '') !== '') {
    set_lang($p['lang']);
}

if ((int)$p['consent'] === 1 && !empty($p['item_order_json']) && $_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: ' . resume_destination($p));
    exit;
}

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $choice = $_POST['consent'] ?? '';
    if ($choice === 'no') {
        touch_participant((int)$p['id'], 'declined', [
            'consent' => 0,
            'status' => 'abandoned',
            'excluded_reason' => 'no_consent',
            'finished_at' => date('Y-m-d H:i:s'),
        ]);
        header('Location: declined.php');
        exit;
    }
    if ($choice === 'yes') {
        $pid = (int)$p['id'];
        if (!empty($p['item_order_json'])) {
            header('Location: ' . resume_destination($p));
            exit;
        }
        [$a, $b] = blocks_for_participant_index($pid);
        $assignment = make_core_assignment($pid, $a, $b);
        touch_participant($pid, 'practice', [
            'consent' => 1,
            'block_a' => $a,
            'block_b' => $b,
            'item_order_json' => encode_assignment($assignment),
            'item_index' => 0,
            'phase' => 'practice',
            'status' => 'in_progress',
        ]);
        $_SESSION['item_index'] = 0;
        $_SESSION['phase'] = 'practice';
        header('Location: survey.php');
        exit;
    }
    $error = t('required');
}

layout_start(t('consent_title'));
?>
<p class="note"><?= htmlspecialchars(t('autosave_note'), ENT_QUOTES, 'UTF-8') ?></p>
<div class="card">
  <h1><?= htmlspecialchars(t('consent_title'), ENT_QUOTES, 'UTF-8') ?></h1>
  <p><?= htmlspecialchars(t('consent_body'), ENT_QUOTES, 'UTF-8') ?></p>
  <?php if ($error): ?><p class="error"><?= htmlspecialchars($error, ENT_QUOTES, 'UTF-8') ?></p><?php endif; ?>
  <form method="post" class="actions">
    <button type="submit" name="consent" value="yes"><?= htmlspecialchars(t('consent_yes'), ENT_QUOTES, 'UTF-8') ?></button>
    <button type="submit" name="consent" value="no" class="secondary"><?= htmlspecialchars(t('consent_no'), ENT_QUOTES, 'UTF-8') ?></button>
  </form>
</div>
<?php layout_end(); ?>
