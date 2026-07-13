#!/usr/bin/env python3
# NSK_IN_rename_5001.py
# Дава на production файла (5001) ясно име: webtool_original_5001.py
# и обновява systemd unit-а да го стартира. Никакво объркване в бъдеще.
#
# Стъпки: backup на unit + стария файл → копира под новото име →
#         обновява ExecStart → daemon-reload → restart → verify.
# НЕ трие стария webtool3.py (остава като резервно).

import shutil, sys, time, os, re, subprocess, ast
from datetime import datetime

R="\033[0m"; B="\033[1m"; RED="\033[31m"; GRN="\033[32m"; YEL="\033[33m"; CYN="\033[36m"; MAG="\033[35m"
def step(m): print(f"{CYN}{B}[..]{R} {m}", flush=True)
def ok(m):   print(f"{GRN}{B}[OK]{R} {m}", flush=True)
def warn(m): print(f"{YEL}{B}[!!]{R} {m}", flush=True)
def err(m):  print(f"{RED}{B}[ERR]{R} {m}", flush=True)

DIR      = "/root/nsk-console"
OLD_FILE = f"{DIR}/webtool3.py"
NEW_FILE = f"{DIR}/webtool_original_5001.py"
UNIT     = "/etc/systemd/system/nsk-webtool2.service"

print(f"{MAG}{B}=== NSK: преименуване на production (5001) ==={R}", flush=True)
print(f"{YEL}webtool3.py → webtool_original_5001.py (+ systemd update){R}", flush=True)
time.sleep(0.3)

# ---------- ПРОВЕРКИ ----------
step("Проверявам файловете ...")
if not os.path.isfile(OLD_FILE):
    err(f"Липсва: {OLD_FILE}. Спирам."); sys.exit(1)
if not os.path.isfile(UNIT):
    err(f"Липсва systemd unit: {UNIT}. Спирам."); sys.exit(1)
ok("Файлът и unit-ът са налице")
time.sleep(0.2)

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

# ---------- BACKUP на unit ----------
step("Backup на systemd unit ...")
try:
    unit_bak = f"{UNIT}.bak-{stamp}"
    shutil.copy2(UNIT, unit_bak)
    ok(f"Unit backup: {unit_bak}")
except Exception as e:
    err(f"Unit backup се провали: {e}"); sys.exit(1)
time.sleep(0.2)

# ---------- КОПИРАЙ файла под новото име ----------
# (copy, не move — старият остава като резервно)
step("Копирам webtool3.py → webtool_original_5001.py ...")
try:
    if os.path.isfile(NEW_FILE):
        # ако вече съществува, backup-ни го преди презапис
        shutil.copy2(NEW_FILE, f"{NEW_FILE}.bak-{stamp}")
        warn(f"{NEW_FILE} вече съществуваше — backup-нат")
    shutil.copy2(OLD_FILE, NEW_FILE)
    ok(f"Създаден: {NEW_FILE}")
except Exception as e:
    err(f"Копирането се провали: {e}"); sys.exit(1)
time.sleep(0.2)

# Провери синтаксиса на новия файл
step("Проверявам синтаксиса на новия файл ...")
try:
    ast.parse(open(NEW_FILE, "r", encoding="utf-8").read())
    ok("Синтаксисът е валиден")
except SyntaxError as e:
    err(f"Синтактична грешка: {e}. Спирам. Unit е непокътнат."); sys.exit(1)
time.sleep(0.2)

# ---------- ОБНОВИ systemd unit ----------
step("Обновявам ExecStart в systemd unit-а ...")
try:
    unit_txt = open(UNIT, "r", encoding="utf-8").read()
    new_unit, n = re.subn(
        re.escape(OLD_FILE),
        NEW_FILE,
        unit_txt
    )
    if n == 0:
        err(f"Не намерих '{OLD_FILE}' в unit-а. Спирам. Нищо не е счупено (unit непроменен).")
        sys.exit(1)
    open(UNIT, "w", encoding="utf-8").write(new_unit)
    ok(f"ExecStart сочи новото име ({n} замяна)")
except Exception as e:
    err(f"Unit update се провали: {e}. Върни: cp {unit_bak} {UNIT}"); sys.exit(1)
time.sleep(0.2)

# ---------- daemon-reload + restart ----------
step("systemctl daemon-reload ...")
r1 = subprocess.run(["systemctl","daemon-reload"], capture_output=True, text=True)
if r1.returncode != 0:
    err(f"daemon-reload се провали: {r1.stderr}. Върни: cp {unit_bak} {UNIT} && systemctl daemon-reload"); sys.exit(1)
ok("daemon-reload OK")
time.sleep(0.2)

step("Рестартирам nsk-webtool2 ...")
r2 = subprocess.run(["systemctl","restart","nsk-webtool2"], capture_output=True, text=True)
if r2.returncode != 0:
    err(f"restart се провали: {r2.stderr}")
    err(f"Върни: cp {unit_bak} {UNIT} && systemctl daemon-reload && systemctl restart nsk-webtool2")
    sys.exit(1)
ok("restart OK")
time.sleep(1.0)  # дай време да стартира

# ---------- VERIFY ----------
step("Проверявам, че услугата върви от новото име ...")
r3 = subprocess.run(["systemctl","is-active","nsk-webtool2"], capture_output=True, text=True)
active = r3.stdout.strip()
r4 = subprocess.run(["bash","-lc","ps -eo args | grep -m1 '[w]ebtool_original_5001.py'"], capture_output=True, text=True)
running_new = "webtool_original_5001.py" in r4.stdout

if active == "active" and running_new:
    ok(f"Услугата е ACTIVE и върви от webtool_original_5001.py ✔")
    print(f"{GRN}{B}=== ГОТОВО. Production вече е webtool_original_5001.py на порт 5001 ==={R}", flush=True)
    print(f"{YEL}Старият webtool3.py остава като резервно (не е изтрит).{R}", flush=True)
    print(f"{YEL}Ако нещо се обърка: cp {unit_bak} {UNIT} && systemctl daemon-reload && systemctl restart nsk-webtool2{R}", flush=True)
else:
    err(f"Verify: active={active}, running_new={running_new}")
    err(f"ВЪРНИ ВЕДНАГА: cp {unit_bak} {UNIT} && systemctl daemon-reload && systemctl restart nsk-webtool2")
    # покажи последните логове за диагностика
    logs = subprocess.run(["bash","-lc","journalctl -u nsk-webtool2 -n 15 --no-pager"], capture_output=True, text=True)
    print(logs.stdout, flush=True)
    sys.exit(1)
