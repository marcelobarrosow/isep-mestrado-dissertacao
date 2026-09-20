<?php
declare(strict_types=1);

/**
 * Security helpers: cookies, headers, CSRF, admin IP allowlist, login rate-limit.
 */

function apply_security_bootstrap(): void
{
    @ini_set('expose_php', '0');
    @ini_set('session.use_strict_mode', '1');
    @ini_set('session.use_only_cookies', '1');
    @ini_set('session.cookie_httponly', '1');
    @ini_set('session.cookie_secure', '1');
    @ini_set('session.cookie_samesite', 'Lax');

    if (PHP_VERSION_ID >= 70300) {
        session_set_cookie_params([
            'lifetime' => 0,
            'path' => '/',
            'secure' => true,
            'httponly' => true,
            'samesite' => 'Lax',
        ]);
    } else {
        session_set_cookie_params(0, '/; samesite=Lax', '', true, true);
    }

    if (session_status() !== PHP_SESSION_ACTIVE) {
        session_start();
    }

    if (!headers_sent()) {
        header_remove('X-Powered-By');
        header('X-Frame-Options: DENY');
        header('X-Content-Type-Options: nosniff');
        header('Referrer-Policy: strict-origin-when-cross-origin');
        header('Permissions-Policy: geolocation=(), microphone=(), camera=()');
        header('Strict-Transport-Security: max-age=31536000; includeSubDomains');
        header(
            "Content-Security-Policy: default-src 'self'; style-src 'self'; script-src 'self'; "
            . "img-src 'self' data:; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        );
    }
}

function client_ip(): string
{
    $ip = $_SERVER['REMOTE_ADDR'] ?? '';
    return is_string($ip) ? $ip : '';
}

function admin_ip_allowed(array $cfg): bool
{
    $list = $cfg['admin_allowed_ips'] ?? [];
    if (!is_array($list) || $list === []) {
        return true;
    }
    $ip = client_ip();
    foreach ($list as $allowed) {
        if (is_string($allowed) && $allowed !== '' && hash_equals($allowed, $ip)) {
            return true;
        }
    }
    return false;
}

function require_admin_ip(array $cfg): void
{
    if (admin_ip_allowed($cfg)) {
        return;
    }
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    exit('Forbidden');
}

function csrf_token(): string
{
    if (empty($_SESSION['_csrf']) || !is_string($_SESSION['_csrf'])) {
        $_SESSION['_csrf'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['_csrf'];
}

function csrf_field(): string
{
    $t = htmlspecialchars(csrf_token(), ENT_QUOTES, 'UTF-8');
    return '<input type="hidden" name="_csrf" value="' . $t . '">';
}

function csrf_verify(?string $token): bool
{
    $expected = $_SESSION['_csrf'] ?? '';
    if (!is_string($expected) || $expected === '' || !is_string($token) || $token === '') {
        return false;
    }
    return hash_equals($expected, $token);
}

function admin_login_rate_limited(): bool
{
    $ip = client_ip();
    $key = 'admin_login_fail_' . hash('sha256', $ip);
    $bucket = $_SESSION[$key] ?? null;
    if (!is_array($bucket)) {
        return false;
    }
    $count = (int)($bucket['count'] ?? 0);
    $until = (int)($bucket['until'] ?? 0);
    if ($until > time()) {
        return true;
    }
    if ($until > 0 && $until <= time()) {
        unset($_SESSION[$key]);
        return false;
    }
    return $count >= 8;
}

function admin_login_fail_register(): void
{
    $ip = client_ip();
    $key = 'admin_login_fail_' . hash('sha256', $ip);
    $bucket = $_SESSION[$key] ?? ['count' => 0, 'until' => 0];
    $count = (int)($bucket['count'] ?? 0) + 1;
    $until = (int)($bucket['until'] ?? 0);
    if ($count >= 8) {
        $until = time() + 900; // 15 minutes
        $count = 0;
    }
    $_SESSION[$key] = ['count' => $count, 'until' => $until];
}

function admin_login_fail_clear(): void
{
    $ip = client_ip();
    $key = 'admin_login_fail_' . hash('sha256', $ip);
    unset($_SESSION[$key]);
}

function require_admin_session(): void
{
    if (empty($_SESSION['admin_ok'])) {
        header('Location: /admin/index.php');
        exit;
    }
}
