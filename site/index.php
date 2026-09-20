<?php
declare(strict_types=1);
require_once __DIR__ . '/lib/bootstrap.php';

$error = '';

if (isset($_GET['novo'])) {
    clear_resume_cookie();
    clear_study_session();
    header('Location: index.php');
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    $existing = hydrate_participant_from_cookie();
    if ($existing) {
        header('Location: ' . resume_destination($existing));
        exit;
    }
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $lang = $_POST['lang'] ?? '';
    try {
        set_lang($lang);
        $existing = hydrate_participant_from_cookie();
        if ($existing) {
            touch_participant((int)$existing['id'], (string)($existing['last_step'] ?? 'lang'), [
                'lang' => $lang,
            ]);
            $existing['lang'] = $lang;
            bind_participant_session($existing);
            header('Location: ' . resume_destination($existing));
            exit;
        }
        $row = create_participant($lang);
        touch_participant((int)$row['id'], 'consent');
        header('Location: consent.php');
        exit;
    } catch (Throwable $e) {
        $error = 'Base de dados indisponível. (' . $e->getMessage() . ')';
    }
}

layout_start('Idioma / Language');
?>
<h1>Idioma / Language</h1>
<p class="note">Escolha o idioma · Choose your language<br>
As respostas são guardadas automaticamente · Answers are saved as you go</p>
<?php if ($error): ?><p class="error"><?= htmlspecialchars($error, ENT_QUOTES, 'UTF-8') ?></p><?php endif; ?>
<form method="post" class="lang-grid">
  <button type="submit" name="lang" value="pt">Português</button>
  <button type="submit" name="lang" value="en">English</button>
</form>
<?php layout_end(); ?>
