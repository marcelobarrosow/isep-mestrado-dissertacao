<?php
declare(strict_types=1);

require_once __DIR__ . '/security.php';
apply_security_bootstrap();

function app_config(): array
{
    static $cfg = null;
    if ($cfg !== null) {
        return $cfg;
    }
    $local = dirname(__DIR__) . '/config.local.php';
    $example = dirname(__DIR__) . '/config.example.php';
    if (is_file($local)) {
        $cfg = require $local;
    } elseif (is_file($example)) {
        $cfg = require $example;
    } else {
        http_response_code(500);
        exit('Missing config.local.php');
    }
    if (!is_array($cfg)) {
        http_response_code(500);
        exit('Invalid config.local.php');
    }
    return $cfg;
}

require_once __DIR__ . '/db.php';
require_once __DIR__ . '/i18n.php';
require_once __DIR__ . '/assign.php';
require_once __DIR__ . '/participant.php';

ensure_resume_schema();
