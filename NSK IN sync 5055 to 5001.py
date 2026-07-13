#!/usr/bin/env python3
# NSK_IN_sync_5055_to_5001.py
# Копира НОВИЯ dev файл (5055, webtool3_dev.py) върху production (5001, webtool3.py),
# като сменя само PORT обратно на 5001, за да работи услугата на правилния порт.
#
# КРИТИЧНО: НЕ докосва webtool3_dev.py (5055) — само чете от него.
# Прави backup на webtool3.py (5001) преди презаписване. Никога не трие.

import shutil, sys, time, os, re, ast
from datetime import datetime

R="\033[0m"; B="\033[1m"; RED="\033[31m"; GRN="\033[32m"; YEL="\033[33m"; CYN="\033[36m"; MAG="\033[35m"
def step(m): print(f"{CYN}{B}[..]{R} {m}", flush=True)
def ok(m):   print(f"{GRN}{B}[OK]{R} {m}", flush=True)
def warn(m): print(f"{YEL}{B}[!!]{R} {m}", flush=True)
def err(m):  print(f"{RED}{B}[ERR]{R} {m}", flush=True)

SRC = "/root/nsk-console/webtool3_dev.py"   # 5055 — НОВИЯТ (само четем)
DST = "/root/nsk-console/webtool3.py"        # 5001 — production (презаписваме)

print(f"{MAG}{B}=== NSK sync: 5055 (dev, нов) → 5001 (production) ==={R}", flush=True)
print(f"{YEL}5055 файлът НЕ се докосва. Само се чете.{R}", flush=True)
time.sleep(0.3)

# ---------- ПРОВЕРКИ ПРЕДИ ----------
step("Проверявам, че двата файла съществуват ...")
if not os.path.isfile(SRC):
    err(f"Изворът (dev/5055) липсва: {SRC}. Спирам."); sys.exit(1)
if not os.path.isfile(DST):
    err(f"Целта (production/5001) липсва: {DST}. Спирам."); sys.exit(1)
ok("Двата файла са налице")
time.sleep(0.2)

# Прочети dev (само четене!)
step("Чета dev файла (5055) — само четене ...")
try:
    dev_src = open(SRC, "r", encoding="utf-8").read()
    ok(f"Прочетени {len(dev_src)} байта от dev (5055)")
except Exception as e:
    err(f"Четенето на dev се провали: {e}"); sys.exit(1)
time.sleep(0.2)

# Провери какъв PORT има dev-а
m = re.search(r"PORT\s*=\s*(\d+)", dev_src)
dev_port = m.group(1) if m else "?"
step(f"Dev файлът (5055) декларира PORT = {dev_port}")
time.sleep(0.2)

# ---------- BACKUP на 5001 ----------
step("Правя backup на production (5001) преди презаписване ...")
try:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = f"{DST}.bak-BEFORE-SYNC-{stamp}"
    shutil.copy2(DST, bak)
    ok(f"Backup на стария 5001: {bak}")
except Exception as e:
    err(f"Backup се провали: {e}. Спирам — нищо не е променено."); sys.exit(1)
time.sleep(0.2)

# ---------- ПОДГОТВИ НОВОТО СЪДЪРЖАНИЕ (dev + PORT 5001) ----------
step("Подготвям съдържанието: dev код + PORT сменен на 5001 ...")
new_content = dev_src

# Смени PORT = XXXX на PORT = 5001 (само декларацията)
new_content, n = re.subn(r"(PORT\s*=\s*)\d+", r"\g<1>5001", new_content, count=1)
if n == 1:
    ok("PORT сменен на 5001 в копието")
else:
    warn("Не намерих 'PORT = число' — копието ще запази оригиналния порт на dev")
time.sleep(0.2)

# Провери синтаксиса ПРЕДИ да запишем
step("Проверявам Python синтаксиса на новото съдържание ...")
try:
    ast.parse(new_content)
    ok("Синтаксисът е валиден")
except SyntaxError as e:
    err(f"СИНТАКСИЧНА ГРЕШКА в dev файла: {e}")
    err(f"НЕ презаписвам 5001. Старият 5001 е непокътнат. Backup: {bak}")
    sys.exit(1)
time.sleep(0.2)

# ---------- ЗАПИШИ в 5001 ----------
step("Записвам новото съдържание в production (5001) ...")
try:
    open(DST, "w", encoding="utf-8").write(new_content)
    ok(f"Записани {len(new_content)} байта в 5001")
except Exception as e:
    err(f"Записът се провали: {e}")
    err(f"Възстанови: cp {bak} {DST}")
    sys.exit(1)
time.sleep(0.2)

# ---------- VERIFY ----------
step("Проверявам резултата ...")
chk = open(DST, "r", encoding="utf-8").read()
port_match = re.search(r"PORT\s*=\s*(\d+)", chk)
final_port = port_match.group(1) if port_match else "?"
same_size = (len(chk) == len(new_content))

# Провери, че dev НЕ е променен (сравни размера с това, което прочетохме)
dev_now = open(SRC, "r", encoding="utf-8").read()
dev_untouched = (len(dev_now) == len(dev_src))

if final_port == "5001" and same_size and dev_untouched:
    ok(f"5001 вече е копие на 5055, с PORT = {final_port} ✔")
    ok(f"5055 (dev) е непокътнат ✔")
    print(f"{GRN}{B}=== ГОТОВО. Рестартирай: systemctl restart nsk-webtool2 ==={R}", flush=True)
    print(f"{YEL}Сега 5001 = 5055 (новият дизайн), работи на порт 5001.{R}", flush=True)
    print(f"{YEL}Бутоните ще ги инжектираме наново (следваща стъпка).{R}", flush=True)
    print(f"{YEL}Ако нещо се обърка: cp {bak} {DST} && systemctl restart nsk-webtool2{R}", flush=True)
else:
    err(f"Verify: port={final_port} (искахме 5001), size_ok={same_size}, dev_untouched={dev_untouched}")
    err(f"Ако нещо изглежда грешно, върни: cp {bak} {DST}")
    sys.exit(1)
