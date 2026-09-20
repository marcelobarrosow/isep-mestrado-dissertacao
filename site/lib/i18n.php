<?php
declare(strict_types=1);

function lang_code(): string
{
    $lang = $_SESSION['lang'] ?? null;
    return ($lang === 'pt' || $lang === 'en') ? $lang : 'en';
}

function t(string $key): string
{
    static $dict = null;
    if ($dict === null) {
        $code = lang_code();
        $path = dirname(__DIR__) . '/lang/' . $code . '.php';
        $dict = is_file($path) ? require $path : [];
    }
    return $dict[$key] ?? $key;
}

function set_lang(string $lang): void
{
    if ($lang !== 'pt' && $lang !== 'en') {
        throw new InvalidArgumentException('Invalid lang');
    }
    $_SESSION['lang'] = $lang;
}
