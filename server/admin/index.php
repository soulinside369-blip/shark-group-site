<?php
/* Shark Group — админка заявок. Вход по паролю ADMIN_PASSWORD из sg-private/sg.env. */
declare(strict_types=1);
require __DIR__ . '/../api/lib.php';

header('X-Robots-Tag: noindex, nofollow');
header('X-Frame-Options: DENY');
header('Cache-Control: no-store');
session_set_cookie_params(['lifetime' => 0, 'path' => '/admin/', 'secure' => true, 'httponly' => true, 'samesite' => 'Strict']);
session_name('sgadm');
session_start();

$env = sg_env();
$pass = $env['ADMIN_PASSWORD'] ?? '';
if (empty($_SESSION['csrf'])) $_SESSION['csrf'] = bin2hex(random_bytes(16));
$csrf = $_SESSION['csrf'];
$act = (string)($_POST['act'] ?? $_GET['act'] ?? '');

function csrf_ok(): bool { return hash_equals($_SESSION['csrf'] ?? '', (string)($_POST['csrf'] ?? '')); }
function back(string $q = ''): void { header('Location: /admin/' . ($q ? '?' . $q : '')); exit; }

/* ---------- вход / выход ---------- */
$err = '';
if ($act === 'login') {
    $db = sg_db();
    $q = $db->prepare('SELECT COUNT(*) FROM hits WHERE ip = ? AND ts > ?');
    $q->execute(['adm:' . sg_ip(), time() - 900]);
    if ((int)$q->fetchColumn() >= 8) $err = 'Слишком много попыток. Подождите 15 минут.';
    elseif (strlen($pass) < 10) $err = 'Пароль не задан: впишите ADMIN_PASSWORD (не короче 10 символов) в sg-private/sg.env.';
    elseif (csrf_ok() && hash_equals($pass, (string)($_POST['password'] ?? ''))) { session_regenerate_id(true); $_SESSION['ok'] = 1; back(); }
    else { $db->prepare('INSERT INTO hits(ip, ts) VALUES(?, ?)')->execute(['adm:' . sg_ip(), time()]); $err = 'Неверный пароль.'; }
}
if ($act === 'logout' && csrf_ok()) { $_SESSION = []; session_destroy(); back(); }

if (empty($_SESSION['ok'])) { page_head('Вход'); ?>
  <form class="login" method="post">
    <h1>Shark Group · заявки</h1>
    <?php if ($err) echo '<p class="err">' . h($err) . '</p>'; ?>
    <input type="hidden" name="act" value="login"><input type="hidden" name="csrf" value="<?= h($csrf) ?>">
    <label>Пароль<input type="password" name="password" autocomplete="current-password" autofocus required></label>
    <button>Войти</button>
  </form>
<?php page_foot(); exit; }

$db = sg_db();

/* ---------- действия ---------- */
if ($act === 'status' && csrf_ok()) {
    $st = (string)($_POST['status'] ?? '');
    if (isset(SG_STATUSES[$st])) $db->prepare('UPDATE leads SET status = ?, note = ?, updated = ? WHERE id = ?')
        ->execute([$st, mb_substr(trim((string)($_POST['note'] ?? '')), 0, 2000), date('Y-m-d H:i:s'), (int)$_POST['id']]);
    back('id=' . (int)$_POST['id']);
}
if ($act === 'tgtest' && csrf_ok()) {
    $ok = sg_tg_send("<b>Проверка связи</b>\nАдминка sharkgroup.pro отправляет заявки в этот чат.");
    back('tg=' . ($ok ? 'ok' : 'fail'));
}
if ($act === 'file') {
    $l = $db->prepare('SELECT files FROM leads WHERE id = ?');
    $l->execute([(int)($_GET['id'] ?? 0)]);
    $files = json_decode((string)$l->fetchColumn(), true) ?: [];
    $f = $files[(int)($_GET['n'] ?? -1)] ?? null;
    if (!$f || !is_file($f['path']) || strpos(realpath($f['path']) ?: '', realpath(sg_private()) ?: '#') !== 0) { http_response_code(404); exit('Файл не найден'); }
    header('Content-Type: ' . $f['mime']);
    header('Content-Disposition: inline; filename*=UTF-8\'\'' . rawurlencode($f['name']));
    readfile($f['path']);
    exit;
}
if ($act === 'csv') {
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="sharkgroup-leads-' . date('Y-m-d') . '.csv"');
    $o = fopen('php://output', 'w');
    fwrite($o, "\xEF\xBB\xBF");
    fputcsv($o, ['№', 'Дата', 'Статус', 'Имя', 'Связь', 'Город', 'Задача', 'Выбрано', 'utm_source', 'utm_campaign', 'utm_term', 'yclid', 'Заметка'], ';');
    foreach ($db->query('SELECT * FROM leads ORDER BY id DESC') as $r) {
        $u = json_decode((string)$r['utm'], true) ?: [];
        fputcsv($o, [$r['id'], $r['created'], SG_STATUSES[$r['status']] ?? $r['status'], $r['name'], $r['contact'], $r['city'], $r['dirs'], $r['picks'],
            $u['utm_source'] ?? '', $u['utm_campaign'] ?? '', $u['utm_term'] ?? '', $u['yclid'] ?? '', $r['note']], ';');
    }
    exit;
}

/* ---------- данные ---------- */
$f = (string)($_GET['f'] ?? 'open');
$where = ['open' => "status IN ('new','work','measure')", 'all' => "status != 'spam'"][$f] ?? (isset(SG_STATUSES[$f]) ? 'status = ' . $db->quote($f) : '1');
$rows = $db->query("SELECT * FROM leads WHERE $where ORDER BY id DESC LIMIT 500")->fetchAll();
$cnt = [];
foreach ($db->query('SELECT status, COUNT(*) c FROM leads GROUP BY status') as $r) $cnt[$r['status']] = (int)$r['c'];
$month = (int)$db->query("SELECT COUNT(*) FROM leads WHERE status != 'spam' AND created >= '" . date('Y-m-01') . "'")->fetchColumn();
$src = [];
foreach ($db->query("SELECT utm FROM leads WHERE status != 'spam' AND created >= '" . date('Y-m-d', strtotime('-30 days')) . "'") as $r) {
    $u = json_decode((string)$r['utm'], true) ?: [];
    $k = !empty($u['yclid']) || ($u['utm_source'] ?? '') === 'yandex' ? 'Яндекс Директ' : (!empty($u['utm_source']) ? $u['utm_source'] : 'Без меток');
    $src[$k] = ($src[$k] ?? 0) + 1;
}
arsort($src);
$open = isset($_GET['id']) ? (int)$_GET['id'] : 0;

page_head('Заявки'); ?>
<header class="bar">
  <b>Shark Group · заявки</b>
  <nav>
    <?php foreach (['open' => 'Открытые', 'all' => 'Все'] + SG_STATUSES as $k => $t): ?>
      <a href="?f=<?= $k ?>" class="<?= $f === $k ? 'on' : '' ?>"><?= h($t) ?><?php if (isset(SG_STATUSES[$k])) echo ' <i>' . ($cnt[$k] ?? 0) . '</i>'; ?></a>
    <?php endforeach; ?>
  </nav>
  <span class="r">
    <a href="?act=csv">Выгрузить CSV</a>
    <form method="post"><input type="hidden" name="csrf" value="<?= h($csrf) ?>"><button name="act" value="tgtest">Проверить Telegram</button><button name="act" value="logout">Выйти</button></form>
  </span>
</header>
<?php if (isset($_GET['tg'])) echo $_GET['tg'] === 'ok' ? '<p class="ok">Telegram: тестовое сообщение отправлено.</p>' : '<p class="err">Telegram не ответил. Проверьте TG_BOT_TOKEN и TG_CHAT_ID в sg.env и что бот добавлен в чат.</p>'; ?>
<section class="kpi">
  <div><small>Заявок за месяц</small><b><?= $month ?></b></div>
  <div><small>Новых</small><b><?= $cnt['new'] ?? 0 ?></b></div>
  <div><small>Договоров всего</small><b><?= $cnt['deal'] ?? 0 ?></b></div>
  <div><small>Источники за 30 дней</small><span><?php foreach ($src as $k => $v) echo h($k) . ': ' . $v . '<br>'; if (!$src) echo '—'; ?></span></div>
</section>
<table>
  <thead><tr><th>№</th><th>Дата</th><th>Статус</th><th>Имя</th><th>Связь</th><th>Задача</th><th>Источник</th><th>TG</th></tr></thead>
  <tbody>
  <?php foreach ($rows as $r): $u = json_decode((string)$r['utm'], true) ?: []; $files = json_decode((string)$r['files'], true) ?: []; ?>
    <tr class="<?= $open === (int)$r['id'] ? 'sel' : '' ?>" onclick="location='?f=<?= h($f) ?>&id=<?= (int)$r['id'] ?>#l<?= (int)$r['id'] ?>'" id="l<?= (int)$r['id'] ?>">
      <td><?= (int)$r['id'] ?></td><td><?= h(substr($r['created'], 0, 16)) ?></td>
      <td><span class="st st-<?= h($r['status']) ?>"><?= h(SG_STATUSES[$r['status']] ?? $r['status']) ?></span></td>
      <td><?= h($r['name']) ?></td><td><?= h($r['contact']) ?></td><td><?= h(mb_strimwidth((string)$r['dirs'], 0, 60, '…')) ?></td>
      <td><?= h(!empty($u['yclid']) ? 'Директ' : ($u['utm_source'] ?? '—')) ?><?= !empty($u['utm_campaign']) ? '<br><small>' . h($u['utm_campaign']) . '</small>' : '' ?></td>
      <td><?= $r['tg_ok'] ? '✓' : '—' ?></td>
    </tr>
    <?php if ($open === (int)$r['id']): ?>
    <tr class="det"><td colspan="8">
      <div class="dg">
        <div>
          <p><b>Задача:</b> <?= h($r['dirs']) ?></p>
          <?php if ($r['picks'] !== '') echo '<p><b>Выбрано на сайте:</b><br>' . nl2br(h($r['picks'])) . '</p>'; ?>
          <p><b>Город:</b> <?= h($r['city'] ?: '—') ?></p>
          <?php if ($files): ?><p><b>Файлы:</b> <?php foreach ($files as $n => $fl) echo '<a target="_blank" href="?act=file&id=' . (int)$r['id'] . '&n=' . $n . '">' . h($fl['name']) . '</a> '; ?></p><?php endif; ?>
          <p class="mut">Метки: <?= h($u ? http_build_query($u, '', ', ') : 'нет') ?><br>Страница: <?= h($r['page']) ?><br>Откуда пришёл: <?= h($r['referrer'] ?: '—') ?><br>ClientID Метрики: <?= h($r['ym_uid'] ?: '—') ?></p>
        </div>
        <form method="post">
          <input type="hidden" name="act" value="status"><input type="hidden" name="csrf" value="<?= h($csrf) ?>"><input type="hidden" name="id" value="<?= (int)$r['id'] ?>">
          <label>Статус<select name="status"><?php foreach (SG_STATUSES as $k => $t) echo '<option value="' . $k . '"' . ($k === $r['status'] ? ' selected' : '') . '>' . h($t) . '</option>'; ?></select></label>
          <label>Заметка<textarea name="note" rows="4"><?= h($r['note']) ?></textarea></label>
          <button>Сохранить</button>
        </form>
      </div>
    </td></tr>
    <?php endif; ?>
  <?php endforeach; if (!$rows) echo '<tr><td colspan="8" class="mut">Заявок нет.</td></tr>'; ?>
  </tbody>
</table>
<details class="diag"><summary>Состояние сервера</summary>
  <ul>
    <li>Настройки sg.env: <?= is_readable(sg_private() . '/sg.env') ? 'найдены' : 'НЕ найдены (' . h(sg_private()) . '/sg.env)' ?></li>
    <li>Telegram: <?= ($env['TG_BOT_TOKEN'] ?? '') !== '' && ($env['TG_CHAT_ID'] ?? '') !== '' ? 'токен и чат указаны' : 'не настроен' ?></li>
    <li>cURL: <?= function_exists('curl_init') ? 'есть' : 'нет — Telegram работать не будет' ?> · SQLite: <?= in_array('sqlite', PDO::getAvailableDrivers(), true) ? 'есть' : 'нет' ?> · PHP <?= PHP_VERSION ?></li>
  </ul>
</details>
<?php page_foot();

function page_head(string $t): void { ?><!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title><?= h($t) ?> · Shark Group</title>
<style>
:root{--n:#0E1726;--n2:#16223A;--b:#C9A46A;--i:#F2EBDD;--m:#B8B0A0;--l:rgba(242,235,221,.14)}
*{box-sizing:border-box}body{margin:0;background:var(--n);color:var(--i);font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
a{color:var(--b)}button{font:inherit;cursor:pointer;border:1px solid var(--b);background:transparent;color:var(--b);border-radius:999px;padding:6px 14px}
.login{max-width:340px;margin:12vh auto;padding:28px;background:var(--n2);border-radius:16px;display:grid;gap:14px}.login h1{font-size:20px;margin:0}
label{display:grid;gap:6px;color:var(--m)}input,select,textarea{font:inherit;color:var(--i);background:var(--n);border:1px solid var(--l);border-radius:10px;padding:9px 11px}
.bar{position:sticky;top:0;z-index:2;display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;padding:12px 16px;background:#0A111D;border-bottom:1px solid var(--l)}
.bar nav{display:flex;flex-wrap:wrap;gap:6px}.bar nav a{padding:4px 10px;border-radius:999px;text-decoration:none;color:var(--m)}.bar nav a.on{background:var(--b);color:var(--n)}.bar nav i{font-style:normal;opacity:.7}
.bar .r{margin-left:auto;display:flex;gap:10px;align-items:center}.bar form{display:flex;gap:6px}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;padding:16px}.kpi div{background:var(--n2);border-radius:12px;padding:12px 14px}.kpi small{display:block;color:var(--m)}.kpi b{font-size:26px}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--l);vertical-align:top}th{color:var(--m);font-weight:500}
tbody tr{cursor:pointer}tbody tr:hover,tr.sel{background:var(--n2)}tr.det{cursor:default;background:var(--n2)}
.dg{display:grid;grid-template-columns:1.4fr 1fr;gap:20px}.dg form{display:grid;gap:10px}.mut{color:var(--m)}
.st{padding:2px 8px;border-radius:999px;background:var(--l);white-space:nowrap}.st-new{background:var(--b);color:var(--n)}.st-deal{background:#3E6B4E}.st-lost,.st-spam{opacity:.6}
.ok,.err{margin:12px 16px;padding:10px 14px;border-radius:10px}.ok{background:#1F3A2B}.err{background:#4A1E1E}
.diag{margin:20px 16px;color:var(--m)}
@media(max-width:760px){.dg{grid-template-columns:1fr}table{font-size:13px}th:nth-child(6),td:nth-child(6),th:nth-child(8),td:nth-child(8){display:none}}
</style></head><body><?php }
function page_foot(): void { echo '</body></html>'; }
