#!/usr/bin/env python3
# NSK_IN_share_button.py
# Добавя "Share to Claude" бутон в Files action меню на webtool3.py
# Прави: (1) backup, (2) вмъква бутон между Duplicate и Delete,
#        (3) вмъква функцията actShareClaude(), (4) verify.
# Правило: НЕ трие нищо — само вмъква. Backup преди всичко.

import re, shutil, sys, time
from datetime import datetime

# ---- ANSI цветове (progress display rule) ----
R="\033[0m"; B="\033[1m"; RED="\033[31m"; GRN="\033[32m"; YEL="\033[33m"; CYN="\033[36m"; MAG="\033[35m"
def step(msg): print(f"{CYN}{B}[..]{R} {msg}", flush=True)
def ok(msg):   print(f"{GRN}{B}[OK]{R} {msg}", flush=True)
def warn(msg): print(f"{YEL}{B}[!!]{R} {msg}", flush=True)
def err(msg):  print(f"{RED}{B}[ERR]{R} {msg}", flush=True)

PATH = "/root/nsk/webtool3.py"

print(f"{MAG}{B}=== NSK Share-to-Claude button installer ==={R}", flush=True)
time.sleep(0.2)

# ---------- STATE 1: BACKUP ----------
step("Правя backup на webtool3.py ...")
try:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = f"{PATH}.bak-{stamp}"
    shutil.copy2(PATH, bak)
    ok(f"Backup създаден: {bak}")
except Exception as e:
    err(f"Backup се провали: {e}"); sys.exit(1)
time.sleep(0.2)

# ---------- READ ----------
step("Чета webtool3.py ...")
try:
    src = open(PATH, "r", encoding="utf-8").read()
    ok(f"Прочетени {len(src)} байта")
except Exception as e:
    err(f"Четенето се провали: {e}"); sys.exit(1)
time.sleep(0.2)

# ---------- IDEMPOTENCY CHECK ----------
if "actShareClaude" in src:
    warn("Бутонът вече е инсталиран (actShareClaude намерен). Нищо не се променя.")
    sys.exit(0)

# ---------- STATE 2: INSERT BUTTON (HTML) ----------
# Вмъкваме бутона ПРЕДИ Delete бутона. Котвата е точният Delete div.
step("Вмъквам HTML бутона между Duplicate и Delete ...")

SHARE_BTN = (
    '<div class="act" onclick="actShareClaude()">'
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/>'
    '<path d="M16 6l-4-4-4 4"/><path d="M12 2v13"/></svg>'
    '<div class="at">Share to Claude</div></div>'
)

# Котва: началото на Delete бутона (стабилен уникален маркер)
delete_anchor = '<div class="act danger" onclick="actDelete()">'
if delete_anchor not in src:
    err("Не намерих Delete бутона (котвата). Спирам — нищо не е счупено, backup е налице.")
    sys.exit(1)

src = src.replace(delete_anchor, SHARE_BTN + delete_anchor, 1)
ok("HTML бутонът е вмъкнат преди Delete")
time.sleep(0.2)

# ---------- STATE 2b: INSERT FUNCTION (JS) ----------
# Вмъкваме JS функцията веднага след actDelete() дефиницията, или преди actDownload ако не намерим.
step("Вмъквам JS функцията actShareClaude() ...")

SHARE_FN = (
    "\nfunction actShareClaude(){"
    "var rel=actTarget.rel;var nm=actTarget.name;"
    "api('/api/read?rel='+encodeURIComponent(rel)).then(function(d){"
    "if(!d||d.ok===false){toast(d&&d.error?d.error:'Read failed');return;}"
    "var body=(d.content!==undefined)?d.content:(d.data!==undefined?d.data:'');"
    "var payload='=== '+nm+' ===\\n'+body;"
    "function copyThenShare(){"
    "var shared=false;"
    "if(navigator.share){try{navigator.share({title:nm,text:payload});shared=true;}catch(e){}}"
    "if(navigator.clipboard&&navigator.clipboard.writeText){"
    "navigator.clipboard.writeText(payload).then(function(){"
    "toast(shared?'Shared + copied':'Copied — paste in Claude');},"
    "function(){toast(shared?'Shared':'Copy failed');});"
    "}else{"
    "var ta=document.createElement('textarea');ta.value=payload;"
    "document.body.appendChild(ta);ta.select();"
    "try{document.execCommand('copy');toast(shared?'Shared + copied':'Copied — paste in Claude');}"
    "catch(e){toast('Copy failed');}"
    "document.body.removeChild(ta);}"
    "}"
    "copyThenShare();closeAll();"
    "});}"
    "\n"
)

# Котва: края на actDelete функцията е трудна за regex; вместо това вмъкваме
# преди дефиницията на actDownload (стабилен уникален маркер, съществува със сигурност).
fn_anchor = "function actDownload()"
if fn_anchor not in src:
    err("Не намерих 'function actDownload()' за котва на JS. Спирам — backup е налице.")
    sys.exit(1)

src = src.replace(fn_anchor, SHARE_FN + fn_anchor, 1)
ok("JS функцията е вмъкната преди actDownload()")
time.sleep(0.2)

# ---------- WRITE ----------
step("Записвам промените ...")
try:
    open(PATH, "w", encoding="utf-8").write(src)
    ok(f"Записани {len(src)} байта")
except Exception as e:
    err(f"Записът се провали: {e} — възстанови от {bak}"); sys.exit(1)
time.sleep(0.2)

# ---------- STATE 3: VERIFY ----------
step("Проверявам резултата ...")
check = open(PATH, "r", encoding="utf-8").read()
btn_ok = "Share to Claude" in check
fn_ok  = "function actShareClaude()" in check
if btn_ok and fn_ok:
    ok("Бутонът И функцията са налице ✔")
    print(f"{GRN}{B}=== ГОТОВО. Рестартирай услугата: systemctl restart nsk-webtool2 ==={R}", flush=True)
    print(f"{YEL}Ако нещо не е наред: cp {bak} {PATH} && systemctl restart nsk-webtool2{R}", flush=True)
else:
    err(f"Verify FAILED (btn={btn_ok}, fn={fn_ok}). Възстанови: cp {bak} {PATH}")
    sys.exit(1)
