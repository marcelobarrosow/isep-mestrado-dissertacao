<?php
declare(strict_types=1);
require_once __DIR__ . '/lib/bootstrap.php';
$p = require_participant();
set_lang($p['lang']);

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $score = (int)($_POST['score'] ?? 0);
    if ($score < 1 || $score > 7) {
        $error = t('required');
    } else {
        $ok = ($score === 2) ? 1 : 0;
        $extra = [
            'attention_ok' => $ok,
            'status' => 'completed',
            'finished_at' => gmdate('Y-m-d H:i:s'),
        ];
        if (!$ok) {
            $extra['excluded_reason'] = 'attention_fail';
        }
        $extra['phase'] = 'main';
        touch_participant((int)$p['id'], 'thanks', $extra);
        header('Location: thanks.php');
        exit;
    }
}

layout_start(t('attention_title'));
?>
<p class="note"><?= htmlspecialchars(t('autosave_note'), ENT_QUOTES, 'UTF-8') ?></p>
<div class="card">
  <h1><?= htmlspecialchars(t('attention_title'), ENT_QUOTES, 'UTF-8') ?></h1>
  <p><?= htmlspecialchars(t('attention_body'), ENT_QUOTES, 'UTF-8') ?></p>
  <?php if ($error): ?><p class="error"><?= htmlspecialchars($error, ENT_QUOTES, 'UTF-8') ?></p><?php endif; ?>
  <form method="post">
    <div class="scale">
      <?php for ($s = 1; $s <= 7; $s++): ?>
        <label>
          <input type="radio" name="score" value="<?= $s ?>" required>
          <span><?= $s ?></span>
        </label>
      <?php endfor; ?>
    </div>
    <div class="actions">
      <button type="submit"><?= htmlspecialchars(t('continue'), ENT_QUOTES, 'UTF-8') ?></button>
    </div>
  </form>
</div>
<?php layout_end(); ?>
