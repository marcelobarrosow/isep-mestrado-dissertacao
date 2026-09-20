<?php
declare(strict_types=1);
require_once __DIR__ . '/lib/bootstrap.php';
$p = require_participant();
set_lang($p['lang']);

$ratedCount = count(rated_item_ids((int)$p['id']));

layout_start(t('thanks_title'));
?>
<div class="card">
  <h1><?= htmlspecialchars(t('thanks_title'), ENT_QUOTES, 'UTF-8') ?></h1>
  <p><?= htmlspecialchars(t('thanks_body'), ENT_QUOTES, 'UTF-8') ?></p>
  <p class="note"><?= htmlspecialchars(sprintf(t('thanks_stats'), $ratedCount), ENT_QUOTES, 'UTF-8') ?></p>
  <p class="note new-session-note">
    <a href="index.php?novo=1"><?= htmlspecialchars(t('new_participation'), ENT_QUOTES, 'UTF-8') ?></a>
  </p>
</div>
<?php layout_end(); ?>
