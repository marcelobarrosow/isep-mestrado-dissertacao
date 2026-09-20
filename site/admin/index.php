<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/lib/bootstrap.php';

$cfg = app_config();
require_admin_ip($cfg);

$error = '';
$ok = !empty($_SESSION['admin_ok']);
$flash = '';

if (isset($_GET['logout'])) {
    unset($_SESSION['admin_ok']);
    header('Location: index.php');
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!csrf_verify($_POST['_csrf'] ?? null)) {
        $error = 'Sessão inválida. Recarregue a página e tente de novo.';
    } elseif (admin_login_rate_limited()) {
        $error = 'Demasiadas tentativas. Aguarde 15 minutos e tente de novo.';
    } else {
        $pass = (string)($_POST['password'] ?? '');
        if (hash_equals((string)$cfg['admin_password'], $pass)) {
            admin_login_fail_clear();
            session_regenerate_id(true);
            $_SESSION['admin_ok'] = 1;
            $ok = true;
        } else {
            admin_login_fail_register();
            $error = 'Palavra-passe incorrecta.';
        }
    }
}

if ($ok && isset($_GET['importado'])) {
    $n = (int)$_GET['importado'];
    $flash = $n > 0
        ? "Catálogo actualizado: {$n} itens importados ou actualizados."
        : 'Reimportação concluída.';
}
if ($ok && isset($_GET['zerado'])) {
    $flash = 'Dados da recolha apagados. Participantes e classificações estão a zero; o catálogo mantém-se.';
}

layout_start('Administração do estudo', 'pt', 'wrap wrap-admin');
?>
<?php if (!$ok): ?>
  <header class="admin-hero">
    <p class="admin-kicker">ISEP · TMDEI</p>
    <h1>Administração do estudo</h1>
    <p class="admin-lead">Acesso reservado à equipa de investigação.</p>
  </header>
  <div class="card admin-login">
    <?php if ($error): ?><p class="error"><?= htmlspecialchars($error, ENT_QUOTES, 'UTF-8') ?></p><?php endif; ?>
    <form method="post">
      <?= csrf_field() ?>
      <label for="password">Palavra-passe</label>
      <input class="field" type="password" name="password" id="password" required autocomplete="current-password">
      <div class="actions">
        <button type="submit">Entrar</button>
      </div>
    </form>
  </div>
<?php else: ?>
  <?php
    $parts = (int)db_value('SELECT COUNT(*) AS c FROM participants');
    $done = (int)db_value("SELECT COUNT(*) AS c FROM participants WHERE status='completed'");
    $inProgress = (int)db_value("SELECT COUNT(*) AS c FROM participants WHERE status='in_progress'");
    $ratings = (int)db_value('SELECT COUNT(*) AS c FROM ratings');
    $items = (int)db_value('SELECT COUNT(*) AS c FROM items');
  ?>
  <header class="admin-hero">
    <div class="admin-hero-row">
      <div>
        <p class="admin-kicker">ISEP · TMDEI</p>
        <h1>Painel do estudo</h1>
        <p class="admin-lead">Estado da recolha e ferramentas de gestão.</p>
      </div>
      <a class="btn secondary admin-logout" href="?logout=1">Sair</a>
    </div>
  </header>

  <?php if ($flash): ?>
    <p class="admin-flash"><?= htmlspecialchars($flash, ENT_QUOTES, 'UTF-8') ?></p>
  <?php endif; ?>

  <section class="admin-stats" aria-label="Indicadores">
    <div class="admin-stat">
      <span class="admin-stat-value"><?= $items ?></span>
      <span class="admin-stat-label">Itens no catálogo</span>
      <span class="admin-stat-hint">células do questionário</span>
    </div>
    <div class="admin-stat">
      <span class="admin-stat-value"><?= $parts ?></span>
      <span class="admin-stat-label">Participantes</span>
      <span class="admin-stat-hint"><?= $done ?> concluídos · <?= $inProgress ?> em curso</span>
    </div>
    <div class="admin-stat">
      <span class="admin-stat-value"><?= $ratings ?></span>
      <span class="admin-stat-label">Classificações</span>
      <span class="admin-stat-hint">respostas Likert gravadas</span>
    </div>
  </section>

  <section class="card admin-panel">
    <h2>Acções</h2>
    <div class="admin-actions">
      <a class="admin-action" href="export.php">
        <strong>Exportar CSV</strong>
        <span>Descarrega o questionário em português, com o ritmo demasiado rápido calculado nesta exportação (mediana por item), para análise.</span>
      </a>
      <form method="post" action="import.php" class="admin-action-form">
        <?= csrf_field() ?>
        <button type="submit" class="admin-action admin-action-button">
          <strong>Reimportar itens</strong>
          <span>Actualiza o catálogo a partir do CSV no servidor, sem apagar participantes nem respostas.</span>
        </button>
      </form>
      <a class="admin-action admin-action-danger" href="reset.php">
        <strong>Zerar dados da recolha</strong>
        <span>Apaga participantes e classificações (útil após testes). O catálogo de 96 itens não é removido. Pede a palavra-passe de novo.</span>
      </a>
    </div>
  </section>

  <section class="card admin-help">
    <h2>Quando regenerar respostas da pipeline</h2>
    <ol class="admin-steps">
      <li>Correr <code>sync_study_artifacts.py</code> no Mac (gera o CSV bilingue).</li>
      <li>Fazer <code>git push</code> para o Plesk (actualiza o ficheiro em <code>data/</code>).</li>
      <li>Clicar em <strong>Reimportar itens</strong> neste painel.</li>
    </ol>
  </section>
<?php endif; ?>
<?php layout_end(); ?>
