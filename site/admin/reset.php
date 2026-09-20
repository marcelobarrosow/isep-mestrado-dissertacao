<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/lib/bootstrap.php';

$cfg = app_config();
require_admin_ip($cfg);
require_admin_session();

$error = '';
$parts = (int)db_value('SELECT COUNT(*) AS c FROM participants');
$ratings = (int)db_value('SELECT COUNT(*) AS c FROM ratings');
$items = (int)db_value('SELECT COUNT(*) AS c FROM items');

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!csrf_verify($_POST['_csrf'] ?? null)) {
        $error = 'Sessão inválida. Recarregue a página e tente de novo.';
    } else {
        $pass = (string)($_POST['password'] ?? '');
        $confirm = strtoupper(trim((string)($_POST['confirm_text'] ?? '')));
        if (!hash_equals((string)$cfg['admin_password'], $pass)) {
            $error = 'Palavra-passe de administração incorrecta.';
        } elseif ($confirm !== 'APAGAR') {
            $error = 'Para confirmar, escreva exactamente APAGAR na caixa de confirmação.';
        } else {
            try {
                db_exec('DELETE FROM ratings');
                db_exec('DELETE FROM participants');
                try {
                    db()->query('ALTER TABLE participants AUTO_INCREMENT = 1');
                } catch (Throwable $ignored) {
                    // Optional: some hosts restrict ALTER; deletes already succeeded.
                }
                header('Location: index.php?zerado=1');
                exit;
            } catch (Throwable $e) {
                $error = 'Não foi possível apagar os dados. Tente novamente.';
            }
        }
    }
}

layout_start('Zerar dados da recolha', 'pt', 'wrap wrap-admin');
?>
<header class="admin-hero">
  <p class="admin-kicker">Zona perigosa</p>
  <h1>Zerar dados da recolha</h1>
  <p class="admin-lead">Apaga participantes e classificações para recomeçar os testes. O catálogo de itens mantém-se.</p>
</header>

<section class="admin-stats" aria-label="O que será apagado">
  <div class="admin-stat">
    <span class="admin-stat-value"><?= $parts ?></span>
    <span class="admin-stat-label">Participantes</span>
    <span class="admin-stat-hint">serão apagados</span>
  </div>
  <div class="admin-stat">
    <span class="admin-stat-value"><?= $ratings ?></span>
    <span class="admin-stat-label">Classificações</span>
    <span class="admin-stat-hint">serão apagadas</span>
  </div>
  <div class="admin-stat">
    <span class="admin-stat-value"><?= $items ?></span>
    <span class="admin-stat-label">Itens no catálogo</span>
    <span class="admin-stat-hint">mantêm-se intactos</span>
  </div>
</section>

<div class="card admin-danger">
  <p><strong>Esta acção não pode ser desfeita.</strong> Exporte o CSV antes, se ainda precisar dos dados de teste.</p>
  <?php if ($error): ?><p class="error"><?= htmlspecialchars($error, ENT_QUOTES, 'UTF-8') ?></p><?php endif; ?>
  <form method="post">
    <?= csrf_field() ?>
    <label for="password">Palavra-passe de administração</label>
    <input class="field" type="password" name="password" id="password" required autocomplete="current-password">
    <label for="confirm_text">Escreva <strong>APAGAR</strong> para confirmar</label>
    <input class="field" type="text" name="confirm_text" id="confirm_text" required autocomplete="off" placeholder="APAGAR">
    <div class="actions">
      <button type="submit" class="btn-danger">Apagar participantes e classificações</button>
      <a class="btn secondary" href="index.php">Cancelar</a>
    </div>
  </form>
</div>
<?php layout_end(); ?>
