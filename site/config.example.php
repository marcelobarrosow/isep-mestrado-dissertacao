<?php
/**
 * Copy to config.local.php on the server (never commit secrets).
 * Keep a private copy in ../site-arquivos-protegidos/ on your Mac.
 */
if (PHP_SAPI !== 'cli') {
    $script = $_SERVER['SCRIPT_FILENAME'] ?? '';
    if (is_string($script) && $script !== '' && realpath($script) === realpath(__FILE__)) {
        http_response_code(403);
        header('Content-Type: text/plain; charset=utf-8');
        exit('Forbidden');
    }
}
return [
    'db_host' => 'localhost',
    'db_name' => 'sunpryn1_survey',
    'db_user' => 'sunpryn1_survey',
    'db_pass' => 'CHANGE_ME',
    'db_charset' => 'utf8mb4',
    'admin_password' => 'CHANGE_ADMIN',
    // Optional: only these IPs may open /admin/ (empty = no IP filter).
    'admin_allowed_ips' => [
        // '203.0.113.10',
    ],
    'practice_item_id' => null, // auto: first item if null
];
