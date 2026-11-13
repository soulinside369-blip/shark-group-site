<?php
/* Shark Group — общая часть приёма заявок и админки.
 *
 * Секреты и данные лежат ВНЕ папки сайта, в /var/www/u3723546/data/sg-private/:
 *   sg.env        — настройки (см. server/sg-private.example/sg.env), заполняет владелец
 *   leads.sqlite  — база заявок (создаётся сама)
 *   uploads/      — файлы из заявок (создаётся сама)
 * Из браузера эту папку не открыть: она выше корня сайта.
 */
declare(strict_types=1);

if (basename($_SERVER['SCRIPT_FILENAME'] ?? '') === 'lib.php') { http_response_code(404); exit; }
date_default_timezone_set('Europe/Moscow');   // Сочи — московское время

const SG_STATUSES = ['new' => 'Новая', 'work' => 'В работе', 'measure' => 'Замер', 'deal' => 'Договор', 'lost' => 'Отказ', 'spam' => 'Спам'];

function sg_private(): string {
    // api/ или admin/ → корень сайта → www → data
    return dirname(__DIR__, 3) . '/sg-private';
}

function sg_env(): array {
    static $env = null;
    if ($env !== null) return $env;
    $env = [];
    $f = sg_private() . '/sg.env';
    if (is_readable($f)) {
        foreach (file($f, FILE_IGNORE_NEW_LINES) as $line) {
            $line = trim($line);
            if ($line === '' || $line[0] === '#' || strpos($line, '=') === false) continue;
            [$k, $v] = explode('=', $line, 2);
            $env[trim($k)] = trim(trim($v), "\"'");
        }
    }
    return $env;
}

function sg_db(): PDO {
    static $db = null;
    if ($db) return $db;
    $dir = sg_private();
    if (!is_dir($dir)) @mkdir($dir, 0700, true);
    $db = new PDO('sqlite:' . $dir . '/leads.sqlite', null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]);
    $db->exec('PRAGMA journal_mode=WAL');
    $db->exec('CREATE TABLE IF NOT EXISTS leads(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT \'new\',
        name TEXT, contact TEXT, city TEXT,
        dirs TEXT, picks TEXT, files TEXT,
        utm TEXT, page TEXT, referrer TEXT, ym_uid TEXT, ip TEXT, ua TEXT,
        note TEXT, tg_ok INTEGER DEFAULT 0, updated TEXT)');
    $db->exec('CREATE TABLE IF NOT EXISTS hits(ip TEXT, ts INTEGER)');
    return $db;
}

function sg_ip(): string { return substr((string)($_SERVER['REMOTE_ADDR'] ?? ''), 0, 64); }

function h(?string $s): string { return htmlspecialchars((string)$s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }

/* Telegram: текст + до 10 файлов. Возвращает true, если сообщение ушло. */
function sg_tg_send(string $html, array $files = []): bool {
    $env = sg_env();
    $token = $env['TG_BOT_TOKEN'] ?? '';
    $chats = array_filter(array_map('trim', explode(',', $env['TG_CHAT_ID'] ?? '')));
    if ($token === '' || !$chats || !function_exists('curl_init')) return false;
    $ok = false;
    foreach ($chats as $chat) {
        $r = sg_tg_call($token, 'sendMessage', ['chat_id' => $chat, 'text' => $html, 'parse_mode' => 'HTML', 'disable_web_page_preview' => 'true']);
        $ok = $ok || !empty($r['ok']);
        foreach ($files as $f) {
            if (!is_file($f['path'])) continue;
            sg_tg_call($token, 'sendDocument', ['chat_id' => $chat, 'document' => new CURLFile($f['path'], $f['mime'], $f['name'])]);
        }
    }
    return $ok;
}

function sg_tg_call(string $token, string $method, array $data): array {
    $ch = curl_init('https://api.telegram.org/bot' . $token . '/' . $method);
    curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => $data, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 20, CURLOPT_CONNECTTIMEOUT => 8]);
    $out = curl_exec($ch);
    curl_close($ch);
    $j = is_string($out) ? json_decode($out, true) : null;
    return is_array($j) ? $j : [];
}

function sg_lead_text(array $l, bool $admin_link = true): string {
    $utm = json_decode((string)$l['utm'], true) ?: [];
    $src = [];
    foreach (['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'] as $k) if (!empty($utm[$k])) $src[] = $k . '=' . $utm[$k];
    if (!empty($utm['yclid'])) $src[] = 'Директ (yclid)';
    $t = "<b>Заявка №{$l['id']} с sharkgroup.pro</b>\n"
       . "Имя: " . h($l['name']) . "\n"
       . "Связь: " . h($l['contact']) . "\n"
       . ($l['city'] !== '' ? "Город: " . h($l['city']) . "\n" : '')
       . "Задача: " . h($l['dirs']) . "\n"
       . ($l['picks'] !== '' ? "Выбрано на сайте:\n• " . str_replace("\n", "\n• ", h($l['picks'])) . "\n" : '')
       . ($l['files'] !== '[]' ? "Файлов: " . count(json_decode($l['files'], true) ?: []) . "\n" : '')
       . ($src ? "Источник: " . h(implode(', ', $src)) . "\n" : "Источник: прямой заход / поиск\n");
    if ($admin_link) $t .= "\nhttps://sharkgroup.pro/admin/";
    return $t;
}

function sg_json(array $a, int $code = 200): void {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($a, JSON_UNESCAPED_UNICODE);
    exit;
}
