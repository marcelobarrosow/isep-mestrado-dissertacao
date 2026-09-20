<?php
declare(strict_types=1);

function db(): mysqli
{
    static $db = null;
    if ($db instanceof mysqli) {
        return $db;
    }
    $c = app_config();
    mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
    $db = new mysqli(
        $c['db_host'],
        $c['db_user'],
        $c['db_pass'],
        $c['db_name']
    );
    $db->set_charset($c['db_charset'] ?? 'utf8mb4');
    return $db;
}

/** @return list<array<string,mixed>> */
function db_all(string $sql, array $params = []): array
{
    $stmt = db_stmt($sql, $params);
    $res = $stmt->get_result();
    $rows = [];
    while ($row = $res->fetch_assoc()) {
        $rows[] = $row;
    }
    $stmt->close();
    return $rows;
}

/** @return array<string,mixed>|null */
function db_one(string $sql, array $params = []): ?array
{
    $rows = db_all($sql, $params);
    return $rows[0] ?? null;
}

function db_exec(string $sql, array $params = []): void
{
    $stmt = db_stmt($sql, $params);
    $stmt->close();
}

function db_stmt(string $sql, array $params = []): mysqli_stmt
{
    $db = db();
    $stmt = $db->prepare($sql);
    if ($params) {
        $types = '';
        $bind = [];
        foreach ($params as $p) {
            if (is_int($p)) {
                $types .= 'i';
            } elseif (is_float($p)) {
                $types .= 'd';
            } else {
                $types .= 's';
            }
            $bind[] = $p;
        }
        $stmt->bind_param($types, ...$bind);
    }
    $stmt->execute();
    return $stmt;
}

function db_insert_id(): int
{
    return (int)db()->insert_id;
}

function db_value(string $sql, array $params = []): mixed
{
    $row = db_one($sql, $params);
    if (!$row) {
        return null;
    }
    return array_values($row)[0];
}
