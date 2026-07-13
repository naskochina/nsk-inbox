#!/usr/bin/env python3
# NSK_IN_buttons_test5055_v2.py  (ПОПРАВЕНА ВЕРСИЯ)
# Инжектира "Copy" + "Share to Claude" в TEST (5055).
# Fix: избягва проблемния \n escape като строи newline чрез String.fromCharCode(10).
#
# Таргетира dev услугата (nsk-webtool3-dev). НЕ пипа production (5001).

import re, shutil, sys, time, subprocess, os, ast
from datetime import datetime

R="\033[0m"; B="\033[1m"; RED="\033[31m"; GRN="\033[32m"; YEL="\033[33m"; CYN="\033[36m"; MAG="\033[35m"
def step(m): print(f"{CYN}{B}[..]{R} {m}", flush=True)
def ok(m):   print(f"{GRN}{B}[OK]{R} {m}", flush=True)
def warn(m): print(f"{YEL}{B}[!!]{R} {m}", flush=True)
def err(m):  print(f"{RED}{B}[ERR]{R} {m}", flush=True)

SERVICE = "nsk-webtool3-dev"

print(f"{MAG}{B}=== NSK: Copy + Share бутони в TEST (5055) v2 ==={R}", flush=True)
print(f"{YEL}Production (5001) НЕ се пипа.{R}", flush=True)
time.sleep(0.3)

# намери файла
step(f"Намирам файла на {SERVICE} ...")
PATH=None
try:
    out=subprocess.run(["systemctl","show",SERVICE,"--property=ExecStart"],capture_output=True,text=True).stdout
    m=re.search(r"(/[^\s;]*\.py)",out)
    if m: PATH=m.group(1)
except Exception as e:
    warn(f"systemctl: {e}")
if not PATH or not os.path.isfile(PATH):
    err(f"Не намерих dev файла (открих: {PATH})."); sys.exit(1)
ok(f"Dev файл: {PATH}")
time.sleep(0.2)

# backup
step("Backup ...")
stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
bak=f"{PATH}.bak-{stamp}"
try:
    shutil.copy2(PATH,bak); ok(f"Backup: {bak}")
except Exception as e:
    err(f"Backup fail: {e}"); sys.exit(1)
time.sleep(0.2)

# read
src=open(PATH,"r",encoding="utf-8").read()
ok(f"Прочетени {len(src)} байта")

# котви
delete_anchor='<div class="act danger" onclick="actDelete()">'
if delete_anchor not in src:
    err("Няма Delete котва в #actSheet."); sys.exit(1)
fn_anchor="function actDownload()"
if fn_anchor not in src:
    err("Няма 'function actDownload()' котва."); sys.exit(1)

# HTML бутони
COPY_BTN=('<div class="act" onclick="actCopyContent()">'
 '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
 'stroke-linecap="round" stroke-linejoin="round">'
 '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>'
 '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>'
 '<div class="at">Copy</div></div>')
SHARE_BTN=('<div class="act" onclick="actShareClaude()">'
 '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
 'stroke-linecap="round" stroke-linejoin="round">'
 '<path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/>'
 '<path d="M16 6l-4-4-4 4"/><path d="M12 2v13"/></svg>'
 '<div class="at">Share to Claude</div></div>')

html_add=""
if "actCopyContent" not in src: html_add+=COPY_BTN
if "actShareClaude" not in src: html_add+=SHARE_BTN
if html_add:
    step("Вмъквам HTML бутони преди Delete ...")
    src=src.replace(delete_anchor, html_add+delete_anchor, 1)
    ok("HTML вмъкнат")
    time.sleep(0.2)

# JS функции — FIX: newline чрез String.fromCharCode(10), без \n escape
NL="String.fromCharCode(10)"
COPY_FN=(
 "\nfunction actCopyContent(){"
 "var rel=actTarget.rel;var nm=actTarget.name;"
 "api('/api/read?rel='+encodeURIComponent(rel)).then(function(d){"
 "if(!d||d.ok===false){toast(d&&d.error?d.error:'Read failed');return;}"
 "var body=(d.content!==undefined)?d.content:'';"
 "function done(f){toast(f?('Copied '+nm+' - paste in Claude'):'Copy failed');}"
 "if(navigator.clipboard&&navigator.clipboard.writeText&&window.isSecureContext){"
 "navigator.clipboard.writeText(body).then(function(){done(true);},function(){fb();});"
 "}else{fb();}"
 "function fb(){var ta=document.createElement('textarea');ta.value=body;"
 "ta.setAttribute('readonly','');ta.style.position='fixed';ta.style.left='-9999px';"
 "document.body.appendChild(ta);ta.focus();ta.select();"
 "try{ta.setSelectionRange(0,body.length);}catch(e){}"
 "var okc=false;try{okc=document.execCommand('copy');}catch(e){okc=false;}"
 "document.body.removeChild(ta);done(okc);}closeAll();});}\n"
)
SHARE_FN=(
 "\nfunction actShareClaude(){"
 "var rel=actTarget.rel;var nm=actTarget.name;"
 "api('/api/read?rel='+encodeURIComponent(rel)).then(function(d){"
 "if(!d||d.ok===false){toast(d&&d.error?d.error:'Read failed');return;}"
 "var body=(d.content!==undefined)?d.content:'';"
 "var payload='=== '+nm+' ==='+" + NL + "+body;var shared=false;"
 "if(navigator.share){try{navigator.share({title:nm,text:payload});shared=true;}catch(e){}}"
 "if(navigator.clipboard&&navigator.clipboard.writeText&&window.isSecureContext){"
 "navigator.clipboard.writeText(payload).then(function(){"
 "toast(shared?'Shared + copied':'Copied - paste in Claude');},function(){"
 "toast(shared?'Shared':'Copy failed');});}else{"
 "var ta=document.createElement('textarea');ta.value=payload;"
 "ta.style.position='fixed';ta.style.left='-9999px';document.body.appendChild(ta);ta.select();"
 "try{document.execCommand('copy');toast(shared?'Shared + copied':'Copied - paste in Claude');}"
 "catch(e){toast('Copy failed');}document.body.removeChild(ta);}closeAll();});}\n"
)

js_add=""
if "function actCopyContent()" not in src: js_add+=COPY_FN
if "function actShareClaude()" not in src: js_add+=SHARE_FN
if js_add:
    step("Вмъквам JS функции преди actDownload() ...")
    src=src.replace(fn_anchor, js_add+fn_anchor, 1)
    ok("JS вмъкнат")
    time.sleep(0.2)

if not html_add and not js_add:
    warn("Нищо за добавяне — вече са налице."); sys.exit(0)

# синтаксис
step("Проверявам Python синтаксиса ...")
try:
    ast.parse(src); ok("Синтаксисът е валиден")
except SyntaxError as e:
    err(f"Синтактична грешка: {e}. НЕ записвам. Backup: {bak}"); sys.exit(1)
time.sleep(0.2)

# write
step("Записвам ...")
try:
    open(PATH,"w",encoding="utf-8").write(src); ok(f"Записани {len(src)} байта")
except Exception as e:
    err(f"Запис fail: {e}. Върни: cp {bak} {PATH}"); sys.exit(1)
time.sleep(0.2)

# restart
step(f"Рестартирам {SERVICE} ...")
r=subprocess.run(["systemctl","restart",SERVICE],capture_output=True,text=True)
if r.returncode!=0:
    err(f"restart fail: {r.stderr}. Върни: cp {bak} {PATH} && systemctl restart {SERVICE}"); sys.exit(1)
ok("restart OK")
time.sleep(1.0)

# verify
step("Проверявам резултата ...")
chk=open(PATH,"r",encoding="utf-8").read()
copy_ok="function actCopyContent()" in chk and ">Copy</div></div>" in chk
share_ok="function actShareClaude()" in chk and ">Share to Claude</div></div>" in chk
active=subprocess.run(["systemctl","is-active",SERVICE],capture_output=True,text=True).stdout.strip()
if copy_ok and share_ok and active=="active":
    ok("Copy + Share налице, услугата ACTIVE ✔")
    print(f"{GRN}{B}=== ГОТОВО. Отвори 5055 в Private tab и тествай ==={R}",flush=True)
    print(f"{YEL}Ако нещо се обърка: cp {bak} {PATH} && systemctl restart {SERVICE}{R}",flush=True)
else:
    err(f"Verify: copy={copy_ok}, share={share_ok}, active={active}")
    err(f"Върни: cp {bak} {PATH} && systemctl restart {SERVICE}")
    sys.exit(1)
