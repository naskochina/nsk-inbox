#!/usr/bin/env python3
# NSK_IN_rename_5055.py
# Дава на DEV/TEST файла (5055) ясно име: webtool_test_5055.py
# и обновява dev systemd unit-а (nsk-webtool3-dev.service).
#
# Таргетира САМО dev услугата. НЕ пипа production (5001) изобщо.
# Backup на unit + файла. Не трие стария webtool3_dev.py.

import shutil, sys, time, os, re, subprocess, ast
from datetime import datetime

R="\033[0m"; B="\033[1m"; RED="\033[31m"; GRN="\033[32m"; YEL="\033[33m"; CYN="\033[36m"; MAG="\033[35m"
def step(m): print(f"{CYN}{B}[..]{R} {m}", flush=True)
def ok(m):   print(f"{GRN}{B}[OK]{R} {m}", flush=True)
def warn(m): print(f"{YEL}{B}[!!]{R} {m}", flush=True)
def err(m):  print(f"{RED}{B}[ERR]{R} {m}", flush=True)

DIR      = "/root/nsk-console"
OLD_FILE = f"{DIR}/webtool3_dev.py"
NEW_FILE = f"{DIR}/webtool_test_5055.py"
UNIT     = "/etc/systemd/system/nsk-webtool3-dev.service"
SERVICE  = "nsk-webtool3-dev"

print(f"{MAG}{B}=== NSK: преименуване на DEV/TEST (5055) ==={R}", flush=True)
print(f"{YEL}webtool3_dev.py → webtool_test_5055.py (+ dev systemd update){R}", flush=True)
print(f"{YEL}Production (5001) НЕ се докосва.{R}", flush=True)
time.sleep(0.3)

# ---------- ПРОВЕРКИ ----------
step("Проверявам файловете ...")
if not os.path.isfile(OLD_FILE):
    err(f"Липсва: {OLD_FILE}. Спирам."); sys.exit(1)
if not os.path.isfile(UNIT):
    err(f"Липсва dev unit: {UNIT}. Спирам."); sys.exit(1)
ok("Dev файлът и unit-ът са налице")
time.sleep(0.2)

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

# ---------- BACKUP на unit ----------
step("Backup на dev systemd unit ...")
try:
    unit_bak = f"{UNIT}.bak-{stamp}"
    shutil.copy2(UNIT, unit_bak)
    ok(f"Unit backup: {unit_bak}")
except Exception as e:
    err(f"Unit backup се провали: {e}"); sys.exit(1)
time.sleep(0.2)

# ---------- КОПИРАЙ под новото име ----------
step("Копирам webtool3_dev.py → webtool_test_5055.py ...")
try:
    if os.path.isfile(NEW_FILE):
        shutil.copy2(NEW_FILE, f"{NEW_FILE}.bak-{stamp}")
        warn(f"{NEW_FILE} вече съществуваше — backup-нат")
    shutil.copy2(OLD_FILE, NEW_FILE)
    ok(f"Създаден: {NEW_FILE}")
except Exception as e:
    err(f"Копирането се провали: {e}"); sys.exit(1)
time.sleep(0.2)

# Синтаксис проверка
step("Проверявам синтаксиса на новия файл ...")
try:
    ast.parse(open(NEW_FILE, "r", encoding="utf-8").read())
    ok("Синтаксисът е валиден")
except SyntaxError as e:
    err(f"Синтактична грешка: {e}. Спирам. Unit непокътнат."); sys.exit(1)
time.sleep(0.2)

# ---------- ОБНОВИ unit ----------
step("Обновявам ExecStart в dev unit-а ...")
try:
    unit_txt = open(UNIT, "r", encoding="utf-8").read()
    new_unit, n = re.subn(re.escape(OLD_FILE), NEW_FILE, unit_txt)
    if n == 0:
        err(f"Не намерих '{OLD_FILE}' в unit-а. Спирам (unit непроменен).")
        sys.exit(1)
    open(UNIT, "w", encoding="utf-8").write(new_unit)
    ok(f"ExecStart сочи новото име ({n} замяна)")
except Exception as e:
    err(f"Unit update се провали: {e}. Върни: cp {unit_bak} {UNIT}"); sys.exit(1)
time.sleep(0.2)

# ---------- daemon-reload + restart (само dev) ----------
step("systemctl daemon-reload ...")
r1 = subprocess.run(["systemctl","daemon-reload"], capture_output=True, text=True)
if r1.returncode != 0:
    err(f"daemon-reload се провали: {r1.stderr}"); sys.exit(1)
ok("daemon-reload OK")
time.sleep(0.2)

step(f"Рестартирам {SERVICE} (само dev) ...")
r2 = subprocess.run(["systemctl","restart",SERVICE], capture_output=True, text=True)
if r2.returncode != 0:
    err(f"restart се провали: {r2.stderr}")
    err(f"Върни: cp {unit_bak} {UNIT} && systemctl daemon-reload && systemctl restart {SERVICE}")
    sys.exit(1)
ok("restart OK")
time.sleep(1.0)

# ---------- VERIFY ----------
step("Проверявам, че dev услугата върви от новото име ...")
r3 = subprocess.run(["systemctl","is-active",SERVICE], capture_output=True, text=True)
active = r3.stdout.strip()
r4 = subprocess.run(["bash","-lc","ps -eo args | grep -m1 '[w]ebtool_test_5055.py'"], capture_output=True, text=True)
running_new = "webtool_test_5055.py" in r4.stdout

if active == "active" and running_new:
    ok(f"Dev услугата е ACTIVE и върви от webtool_test_5055.py ✔")
    print(f"{GRN}{B}=== ГОТОВО. DEV/TEST вече е webtool_test_5055.py на порт 5055 ==={R}", flush=True)
    print(f"{YEL}Старият webtool3_dev.py остава като резервно (не е изтрит).{R}", flush=True)
    print(f"{YEL}Ако нещо се обърка: cp {unit_bak} {UNIT} && systemctl daemon-reload && systemctl restart {SERVICE}{R}", flush=True)
else:
    err(f"Verify: active={active}, running_new={running_new}")
    err(f"ВЪРНИ: cp {unit_bak} {UNIT} && systemctl daemon-reload && systemctl restart {SERVICE}")
    logs = subprocess.run(["bash","-lc",f"journalctl -u {SERVICE} -n 15 --no-pager"], capture_output=True, text=True)
    print(logs.stdout, flush=True)
    sys.exit(1)
