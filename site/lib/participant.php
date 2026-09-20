<?php
declare(strict_types=1);

const RESUME_COOKIE = 'prepd_resume';
const RESUME_COOKIE_DAYS = 30;

function ensure_resume_schema(): void
{
    static $done = false;
    if ($done) {
        return;
    }
    $done = true;
    try {
        $db = db();
        if (!db_one("SHOW COLUMNS FROM participants LIKE 'resume_token'")) {
            $db->query('ALTER TABLE participants ADD COLUMN resume_token CHAR(64) NULL DEFAULT NULL AFTER id');
        }
        if (!db_one("SHOW COLUMNS FROM participants LIKE 'item_index'")) {
            $db->query('ALTER TABLE participants ADD COLUMN item_index INT UNSIGNED NOT NULL DEFAULT 0 AFTER item_order_json');
        }
        if (!db_one("SHOW COLUMNS FROM participants LIKE 'phase'")) {
            $db->query("ALTER TABLE participants ADD COLUMN phase VARCHAR(16) NOT NULL DEFAULT 'practice' AFTER item_index");
        }
        try {
            $db->query('ALTER TABLE participants ADD UNIQUE KEY uq_participants_resume_token (resume_token)');
        } catch (Throwable $e) {
            // index may already exist
        }
    } catch (Throwable $e) {
        // Table may not exist yet (pre-install); ignore.
    }
}

function generate_resume_token(): string
{
    return bin2hex(random_bytes(32));
}

function read_resume_cookie(): ?string
{
    $t = $_COOKIE[RESUME_COOKIE] ?? '';
    if (!is_string($t) || !preg_match('/^[a-f0-9]{64}$/', $t)) {
        return null;
    }
    return $t;
}

function issue_resume_cookie(string $token): void
{
    $secure = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
        || ((int)($_SERVER['SERVER_PORT'] ?? 0) === 443);
    setcookie(RESUME_COOKIE, $token, [
        'expires' => time() + RESUME_COOKIE_DAYS * 86400,
        'path' => '/',
        'secure' => $secure,
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
    $_COOKIE[RESUME_COOKIE] = $token;
}

function clear_resume_cookie(): void
{
    $secure = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
        || ((int)($_SERVER['SERVER_PORT'] ?? 0) === 443);
    setcookie(RESUME_COOKIE, '', [
        'expires' => time() - 3600,
        'path' => '/',
        'secure' => $secure,
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
    unset($_COOKIE[RESUME_COOKIE]);
}

function find_participant_by_token(string $token): ?array
{
    return db_one('SELECT * FROM participants WHERE resume_token = ?', [$token]);
}

function clear_study_session(): void
{
    unset($_SESSION['participant_id'], $_SESSION['item_index'], $_SESSION['phase'], $_SESSION['lang']);
}

function bind_participant_session(array $row): void
{
    $_SESSION['participant_id'] = (int)$row['id'];
    $_SESSION['item_index'] = (int)($row['item_index'] ?? 0);
    $_SESSION['phase'] = (string)($row['phase'] ?? 'practice');
    if (!empty($row['lang'])) {
        set_lang((string)$row['lang']);
    }
}

function current_participant_id(): ?int
{
    return isset($_SESSION['participant_id']) ? (int)$_SESSION['participant_id'] : null;
}

function hydrate_participant_from_cookie(): ?array
{
    $id = current_participant_id();
    if ($id) {
        $row = db_one('SELECT * FROM participants WHERE id = ?', [$id]);
        if ($row) {
            if (empty($row['resume_token'])) {
                $token = generate_resume_token();
                touch_participant((int)$row['id'], (string)($row['last_step'] ?? 'lang'), [
                    'resume_token' => $token,
                ]);
                $row['resume_token'] = $token;
                issue_resume_cookie($token);
            } elseif (read_resume_cookie() !== $row['resume_token']) {
                issue_resume_cookie((string)$row['resume_token']);
            }
            bind_participant_session($row);
            return $row;
        }
        unset($_SESSION['participant_id']);
    }
    $token = read_resume_cookie();
    if (!$token) {
        return null;
    }
    $row = find_participant_by_token($token);
    if (!$row) {
        clear_resume_cookie();
        return null;
    }
    bind_participant_session($row);
    return $row;
}

function require_participant(): array
{
    $row = hydrate_participant_from_cookie();
    if (!$row) {
        header('Location: index.php');
        exit;
    }
    return $row;
}

function touch_participant(int $id, string $lastStep, ?array $extra = null): void
{
    $fields = ['last_step = ?', 'updated_at = CURRENT_TIMESTAMP'];
    $params = [$lastStep];
    if ($extra) {
        foreach ($extra as $col => $val) {
            $fields[] = "$col = ?";
            $params[] = $val;
        }
    }
    $params[] = $id;
    db_exec('UPDATE participants SET ' . implode(', ', $fields) . ' WHERE id = ?', $params);
}

function save_rating(int $participantId, string $itemId, int $score, int $position): void
{
    if ($score < 1 || $score > 7) {
        throw new InvalidArgumentException('score');
    }
    db_exec(
        'INSERT INTO ratings (participant_id, item_id, score, position)
         VALUES (?, ?, ?, ?)
         ON DUPLICATE KEY UPDATE score = VALUES(score), answered_at = CURRENT_TIMESTAMP',
        [$participantId, $itemId, $score, $position]
    );
}

function rated_item_ids(int $participantId): array
{
    $rows = db_all('SELECT item_id FROM ratings WHERE participant_id = ?', [$participantId]);
    return array_map(static fn($r) => (string)$r['item_id'], $rows);
}

function participant_remaining_count(array $row): int
{
    $rated = rated_item_ids((int)$row['id']);
    $all = all_item_ids();
    return count(array_diff($all, $rated));
}

/**
 * Align session + DB progress with ratings / last_step.
 * @return array{item_index:int,phase:string}
 */
function sync_progress_from_db(array $row): array
{
    $pid = (int)$row['id'];
    $assignment = parse_assignment((string)($row['item_order_json'] ?? ''));
    $order = assignment_order($assignment);
    $rated = rated_item_ids($pid);
    $ratedSet = array_fill_keys($rated, true);

    $idx = 0;
    foreach ($order as $i => $itemId) {
        if (!isset($ratedSet[$itemId])) {
            $idx = $i;
            break;
        }
        $idx = $i + 1;
    }

    $last = (string)($row['last_step'] ?? '');
    $phase = (string)($row['phase'] ?? 'practice');
    if ($last === 'practice' && count($rated) === 0) {
        $phase = 'practice';
        $idx = 0;
    } elseif ($phase !== 'practice' || count($rated) > 0 || in_array($last, ['survey', 'survey_bonus', 'continue_offer', 'attention', 'thanks'], true)) {
        if ($phase === 'practice' && (count($rated) > 0 || $last !== 'practice')) {
            $phase = 'main';
        }
    }

    touch_participant($pid, $last !== '' ? $last : 'survey', [
        'item_index' => $idx,
        'phase' => $phase,
    ]);
    $_SESSION['item_index'] = $idx;
    $_SESSION['phase'] = $phase;

    return ['item_index' => $idx, 'phase' => $phase];
}

function resume_destination(array $row): string
{
    $status = (string)($row['status'] ?? 'in_progress');
    $last = (string)($row['last_step'] ?? 'lang');
    $consent = (int)($row['consent'] ?? 0);

    if ($status === 'abandoned' || ($consent === 0 && $last === 'declined')) {
        return 'declined.php';
    }
    if ($status === 'completed') {
        return 'thanks.php';
    }
    if ($consent !== 1 || empty($row['item_order_json'])) {
        return 'consent.php';
    }
    if ($last === 'continue_offer') {
        return 'continue_offer.php';
    }
    if ($last === 'attention') {
        return 'attention.php';
    }
    if ($last === 'thanks') {
        return 'thanks.php';
    }

    $progress = sync_progress_from_db($row);
    $assignment = parse_assignment((string)$row['item_order_json']);
    $order = assignment_order($assignment);
    if ($progress['phase'] === 'practice') {
        return 'survey.php';
    }
    if ($progress['item_index'] >= count($order)) {
        if (!empty($assignment['unlocked'])) {
            return 'attention.php';
        }
        return 'continue_offer.php';
    }
    return 'survey.php';
}

function create_participant(string $lang): array
{
    $token = generate_resume_token();
    db_exec(
        'INSERT INTO participants (resume_token, lang, status, last_step, item_index, phase)
         VALUES (?, ?, ?, ?, 0, ?)',
        [$token, $lang, 'in_progress', 'lang', 'practice']
    );
    $id = db_insert_id();
    issue_resume_cookie($token);
    $row = db_one('SELECT * FROM participants WHERE id = ?', [$id]);
    if (!$row) {
        throw new RuntimeException('Failed to create participant');
    }
    bind_participant_session($row);
    return $row;
}

function layout_start(string $title, ?string $langOverride = null, string $wrapClass = 'wrap'): void
{
    $lang = htmlspecialchars($langOverride ?? lang_code(), ENT_QUOTES, 'UTF-8');
    $wrap = htmlspecialchars($wrapClass, ENT_QUOTES, 'UTF-8');
    echo '<!DOCTYPE html><html lang="' . $lang . '"><head><meta charset="utf-8">';
    echo '<meta name="viewport" content="width=device-width, initial-scale=1">';
    echo '<title>' . htmlspecialchars($title, ENT_QUOTES, 'UTF-8') . '</title>';
    echo '<link rel="stylesheet" href="/assets/style.css">';
    echo '</head><body><main class="' . $wrap . '">';
}

function layout_end(): void
{
    echo '</main></body></html>';
}
