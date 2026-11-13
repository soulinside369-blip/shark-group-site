<?php
/* Приём заявки с формы sharkgroup.pro: POST multipart/form-data → база + Telegram. Ответ — JSON. */
declare(strict_types=1);
require __DIR__ . '/lib.php';

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') sg_json(['ok' => false, 'error' => 'method'], 405);

// заявки принимаем только со своего сайта
$origin = (string)($_SERVER['HTTP_ORIGIN'] ?? '');
if ($origin !== '' && !preg_match('~^https://(www\.)?sharkgroup\.pro$~', $origin)) sg_json(['ok' => false, 'error' => 'origin'], 403);

// ловушка для ботов: скрытое поле должно остаться пустым, а форма — заполняться дольше 3 секунд
if (trim((string)($_POST['website'] ?? '')) !== '') sg_json(['ok' => true, 'id' => 0]);
$elapsed = (int)($_POST['t'] ?? 0);
if ($elapsed > 0 && $elapsed < 3000) sg_json(['ok' => false, 'error' => 'fast'], 429);

function field(string $k, int $max): string {
    $v = trim((string)($_POST[$k] ?? ''));
    $v = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $v) ?? '';
    return mb_substr($v, 0, $max);
}

$name = field('name', 80);
$contact = field('contact', 80);
$city = field('city', 80);
$dirs = field('dirs', 400);
$picks = field('picks', 2000);
$page = field('page', 300);
$ref = field('referrer', 300);
$ym = preg_replace('/\D/', '', field('ym_uid', 40)) ?? '';
$consent = ($_POST['consent'] ?? '') === '1';

$digits = preg_replace('/\D/', '', $contact) ?? '';
if ($name === '' || (strlen($digits) < 10 && !preg_match('/^@\w{4,}$/', $contact)) || !$consent) {
    sg_json(['ok' => false, 'error' => 'fields'], 422);
}

$utm = [];
foreach (['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'yclid'] as $k) {
    $v = field($k, 200);
    if ($v !== '') $utm[$k] = $v;
}

try {
    $db = sg_db();
    // не больше 5 заявок с одного адреса за 10 минут
    $now = time();
    $db->prepare('DELETE FROM hits WHERE ts < ?')->execute([$now - 600]);
    $q = $db->prepare('SELECT COUNT(*) FROM hits WHERE ip = ?');
    $q->execute([sg_ip()]);
    if ((int)$q->fetchColumn() >= 5) sg_json(['ok' => false, 'error' => 'rate'], 429);
    $db->prepare('INSERT INTO hits(ip, ts) VALUES(?, ?)')->execute([sg_ip(), $now]);

    // файлы: до 10 штук, до 10 МБ каждый, только фото и PDF
    $saved = [];
    if (!empty($_FILES['files']) && is_array($_FILES['files']['name'])) {
        $dir = sg_private() . '/uploads/' . date('Y-m');
        if (!is_dir($dir)) @mkdir($dir, 0700, true);
        $allowed = ['image/jpeg' => 'jpg', 'image/png' => 'png', 'image/webp' => 'webp', 'image/heic' => 'heic', 'image/heif' => 'heif', 'application/pdf' => 'pdf'];
        $fi = function_exists('finfo_open') ? finfo_open(FILEINFO_MIME_TYPE) : null;
        $n = min(10, count($_FILES['files']['name']));
        for ($i = 0; $i < $n; $i++) {
            if (($_FILES['files']['error'][$i] ?? 1) !== UPLOAD_ERR_OK) continue;
            $tmp = $_FILES['files']['tmp_name'][$i];
            if (($_FILES['files']['size'][$i] ?? 0) > 10 * 1024 * 1024 || !is_uploaded_file($tmp)) continue;
            $mime = $fi ? (string)finfo_file($fi, $tmp) : (string)($_FILES['files']['type'][$i] ?? '');
            if (!isset($allowed[$mime])) continue;
            $orig = preg_replace('/[^\w.\-а-яА-ЯёЁ ]/u', '_', (string)$_FILES['files']['name'][$i]) ?? 'file';
            $path = $dir . '/' . bin2hex(random_bytes(12)) . '.' . $allowed[$mime];
            if (move_uploaded_file($tmp, $path)) $saved[] = ['path' => $path, 'mime' => $mime, 'name' => mb_substr($orig, 0, 80)];
        }
    }

    $row = [
        'created' => date('Y-m-d H:i:s'), 'name' => $name, 'contact' => $contact, 'city' => $city,
        'dirs' => $dirs, 'picks' => $picks, 'files' => json_encode($saved, JSON_UNESCAPED_UNICODE),
        'utm' => json_encode($utm, JSON_UNESCAPED_UNICODE), 'page' => $page, 'referrer' => $ref, 'ym_uid' => $ym,
        'ip' => sg_ip(), 'ua' => mb_substr((string)($_SERVER['HTTP_USER_AGENT'] ?? ''), 0, 250),
    ];
    $db->prepare('INSERT INTO leads(created,name,contact,city,dirs,picks,files,utm,page,referrer,ym_uid,ip,ua)
                  VALUES(:created,:name,:contact,:city,:dirs,:picks,:files,:utm,:page,:referrer,:ym_uid,:ip,:ua)')->execute($row);
    $row['id'] = (int)$db->lastInsertId();

    $ok = sg_tg_send(sg_lead_text($row), $saved);
    if ($ok) $db->prepare('UPDATE leads SET tg_ok = 1 WHERE id = ?')->execute([$row['id']]);

    sg_json(['ok' => true, 'id' => $row['id']]);
} catch (Throwable $e) {
    error_log('sg lead: ' . $e->getMessage());
    sg_json(['ok' => false, 'error' => 'server'], 500);
}
