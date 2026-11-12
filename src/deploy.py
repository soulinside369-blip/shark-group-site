# -*- coding: utf-8 -*-
"""Выкладка сайта на хостинг Reg.ru (sharkgroup.pro) по FTPS.

    python deploy.py            — залить только изменённые файлы
    python deploy.py --all      — залить всё заново
    python deploy.py --dry      — показать, что будет залито, ничего не меняя

Перед первым запуском создайте рядом с репозиторием файл ../.env (он в .gitignore):
    SG_FTP_HOST=server109.hosting.reg.ru
    SG_FTP_USER=u3723546
    SG_FTP_PASS=...          ← пароль FTP/SFTP из личного кабинета Reg.ru:
                               «Хостинг» → «Доступ в панель управления, SSH, SFTP»
Пароль никуда не отправляется, кроме самого хостинга.

Что заливается: index.html, m/*.webp, .htaccess, robots.txt — в /www/sharkgroup.pro.
Однофайловая shark-group.html, исходники и документы на хостинг не попадают.
Какие файлы уже залиты, скрипт помнит в ../.deploy-state.json (по хэшу содержимого).
"""
import ftplib, hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE = '/www/sharkgroup.pro'
STATE = os.path.join(ROOT, '.deploy-state.json')


def env():
    e = dict(os.environ)
    p = os.path.join(ROOT, '.env')
    if os.path.exists(p):
        for line in open(p, encoding='utf-8'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1); e.setdefault(k.strip(), v.strip())
    miss = [k for k in ('SG_FTP_HOST', 'SG_FTP_USER', 'SG_FTP_PASS') if not e.get(k)]
    if miss: sys.exit('Нет настроек в .env: ' + ', '.join(miss) + ' (см. начало deploy.py)')
    return e


def files():
    out = ['index.html', '.htaccess', 'robots.txt']
    out += ['m/' + f for f in sorted(os.listdir(os.path.join(ROOT, 'm'))) if f.endswith('.webp')]
    return [f for f in out if os.path.exists(os.path.join(ROOT, f))]


def h(f): return hashlib.md5(open(os.path.join(ROOT, f), 'rb').read()).hexdigest()


def main():
    dry, full = '--dry' in sys.argv, '--all' in sys.argv
    state = {} if full or not os.path.exists(STATE) else json.load(open(STATE, encoding='utf-8'))
    todo = [f for f in files() if state.get(f) != h(f)]
    # index.html — последним: пока картинки льются, посетители видят прежнюю целую версию
    todo.sort(key=lambda f: f == 'index.html')
    print(f'К заливке: {len(todo)} из {len(files())}')
    if dry or not todo:
        for f in todo: print('  ', f)
        return
    e = env()
    ftp = ftplib.FTP_TLS(e['SG_FTP_HOST'], timeout=60)
    ftp.login(e['SG_FTP_USER'], e['SG_FTP_PASS']); ftp.prot_p()
    ftp.cwd(REMOTE)
    try: ftp.mkd('m')
    except ftplib.error_perm: pass
    for f in todo:
        with open(os.path.join(ROOT, f), 'rb') as fh:
            ftp.storbinary('STOR ' + f, fh)
        state[f] = h(f); print('  ✓', f)
        json.dump(state, open(STATE, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    ftp.quit()
    print('Готово: https://sharkgroup.pro/')


if __name__ == '__main__':
    main()
