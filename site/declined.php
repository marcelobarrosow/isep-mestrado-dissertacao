<?php
declare(strict_types=1);
require_once __DIR__ . '/lib/bootstrap.php';
if (!empty($_SESSION['lang'])) {
    set_lang($_SESSION['lang']);
}
layout_start(t('declined_title'));
?>
<div class="card">
  <h1><?= htmlspecialchars(t('declined_title'), ENT_QUOTES, 'UTF-8') ?></h1>
  <p><?= htmlspecialchars(t('declined_body'), ENT_QUOTES, 'UTF-8') ?></p>
</div>
<?php layout_end(); ?>
