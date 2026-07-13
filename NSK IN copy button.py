#!/usr/bin/env python3
# NSK_IN_copy_button.py
# Добавя "Copy" бутон в Files action меню (#actSheet) на webtool3.py.
# Бутонът копира СЪДЪРЖАНИЕТО на файла в clipboard (работи на HTTP).
#
# Ключово: сам намира файла, който услугата nsk-webtool2 РЕАЛНО чете
# (от systemctl), за да няма объркване между стара/нова структура.
#
# Правила: backup първо, само вмъква (никога не трие), verify накрая.

import re, shutil, sys, time, subprocess, os
from datetime import datetime

# ---- ANSI цветове ----
R="\033[0m"; B="\033[1m"; RED="\033[31m"; GRN="\033[32m"; YEL="\033[33m"; CYN="\033[36m"; MAG="\033[35m"
def step(m): print(f"{CYN}{B}[..]{R} {m}", flush=True)
def ok(m):   print(f"{GRN}{B}[OK]{R} {m}", flush=True)
def warn(m): print(f"{YEL}{B}[!!]{R} {m}", flush=True)
def err(m):  print(f"{RED}{B}[ERR]{R} {m}", flush=True)

print(f"{MAG}{B}=== NSK Copy button installer ==={R}", flush=True)
time.sleep(0.2)

# ---------- STATE 1: НАМЕРИ ПРАВИЛНИЯ ФАЙЛ ----------
step("Намирам файла, който услугата nsk-webtool2 реално чете ...")
PATH = None
try:
    out = subprocess.run(["systemctl", "show", "nsk-webtool2", "--property=ExecStart"],
                         capture_output=True, text=True).stdout
    # ExecStart={ ... argv[]=/usr/bin/python3 /root/xxx/webtool3.py ; ... }
    m = re.search(r"(/[^\s;]*webtool3\.py)", out)
    if m:
        PATH = m.group(1)
except Exception as e:
    warn(f"systemctl четенето се провали: {e}")

# fallback: активния процес
if not PATH:
    try:
        ps = subprocess.run(["bash","-lc","ps -eo args | grep -m1 '[w]ebtool3.py'"],
                           capture_output=True, text=True).stdout
        m = re.search(r"(/[^\s]*webtool3\.py)", ps)
        if m: PATH = m.group(1)
    except Exception:
        pass

if not PATH or not os.path.isfile(PATH):
    err(f"Не намерих активния webtool3.py (открих: {PATH}). Спирам.")
    sys.exit(1)
ok(f"Активният файл е: {PATH}")
time.sleep(0.2)

# ---------- BACKUP ----------
step("Правя backup ...")
try:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = f"{PATH}.bak-{stamp}"
    shutil.copy2(PATH, bak)
    ok(f"Backup: {bak}")
except Exception as e:
    err(f"Backup се провали: {e}"); sys.exit(1)
time.sleep(0.2)

# ---------- READ ----------
step("Чета файла ...")
src = open(PATH, "r", encoding="utf-8").read()
ok(f"Прочетени {len(src)} байта")

# ---------- IDEMPOTENCY ----------
if "actCopyContent" in src:
    warn("Copy бутонът вече е инсталиран (actCopyContent намерен). Нищо не се променя.")
    sys.exit(0)

# ---------- STATE 2: ВМЪКНИ HTML БУТОНА ----------
# Котва: точния Delete ред в #actSheet (уникален с този SVG path).
step("Вмъквам HTML бутона преди Delete в #actSheet ...")

COPY_BTN = (
    '<div class="act" onclick="actCopyContent()">'
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>'
    '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>'
    '<div class="at">Copy</div></div>'
)

# Уникалната Delete-котва от реалния файл:
delete_anchor = '<div class="act danger" onclick="actDelete()">'
if delete_anchor not in src:
    err("Не намерих Delete бутона (котвата) в #actSheet. Спирам — backup е налице.")
    sys.exit(1)
src = src.replace(delete_anchor, COPY_BTN + delete_anchor, 1)
ok("HTML бутонът е вмъкнат преди Delete")
time.sleep(0.2)

# ---------- STATE 2b: ВМЪКНИ JS ФУНКЦИЯТА ----------
# Котва: съществуващата actDownload() дефиниция (уникална).
step("Вмъквам JS функцията actCopyContent() ...")

COPY_FN = (
    "\nfunction actCopyContent(){"
    "var rel=actTarget.rel;var nm=actTarget.name;"
    "api('/api/read?rel='+encodeURIComponent(rel)).then(function(d){"
    "if(!d||d.ok===false){toast(d&&d.error?d.error:'Read failed');return;}"
    "var body=(d.content!==undefined)?d.content:'';"
    "function done(okFlag){toast(okFlag?('Copied '+nm+' — paste in Claude'):'Copy failed');}"
    "if(navigator.clipboard&&navigator.clipboard.writeText&&window.isSecureContext){"
    "navigator.clipboard.writeText(body).then(function(){done(true);},function(){fb();});"
    "}else{fb();}"
    "function fb(){"
    "var ta=document.createElement('textarea');ta.value=body;ta.setAttribute('readonly','');"
    "ta.style.position='fixed';ta.style.left='-9999px';ta.style.top='0';"
    "document.body.appendChild(ta);ta.focus();ta.select();"
    "try{ta.setSelectionRange(0,body.length);}catch(e){}"
    "var okc=false;try{okc=document.execCommand('copy');}catch(e){okc=false;}"
    "document.body.removeChild(ta);done(okc);}"
    "closeAll();"
    "});}"
    "\n"
)

fn_anchor = "function actDownload()"
if fn_anchor not in src:
    err("Не намерих 'function actDownload()' за котва. Спирам — backup е налице.")
    sys.exit(1)
src = src.replace(fn_anchor, COPY_FN + fn_anchor, 1)
ok("JS функцията е вмъкната преди actDownload()")
time.sleep(0.2)

# ---------- WRITE ----------
step("Записвам промените ...")
try:
    open(PATH, "w", encoding="utf-8").write(src)
    ok(f"Записани {len(src)} байта")
except Exception as e:
    err(f"Записът се провали: {e} — възстанови: cp {bak} {PATH}"); sys.exit(1)
time.sleep(0.2)

# ---------- STATE 3: VERIFY ----------
step("Проверявам резултата ...")
chk = open(PATH, "r", encoding="utf-8").read()
btn_ok = ">Copy</div></div>" in chk or 'onclick="actCopyContent()"' in chk
fn_ok  = "function actCopyContent()" in chk
if btn_ok and fn_ok:
    ok("Бутонът И функцията са налице ✔")
    print(f"{GRN}{B}=== ГОТОВО. Рестартирай: systemctl restart nsk-webtool2 ==={R}", flush=True)
    print(f"{YEL}Файл: {PATH}{R}", flush=True)
    print(f"{YEL}Ако нещо се обърка: cp {bak} {PATH} && systemctl restart nsk-webtool2{R}", flush=True)
else:
    err(f"Verify FAILED (btn={btn_ok}, fn={fn_ok}). Възстанови: cp {bak} {PATH}")
    sys.exit(1)
