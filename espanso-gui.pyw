"""Mini gestionnaire Espanso : un fichier .yml (JSON, donc YAML valide) par raccourci.
Désactivé = nom préfixé par "_" (Espanso ignore ces fichiers).
Interface : page locale ouverte dans une fenêtre "app" de Chrome/Edge."""
import json, os, re, secrets, subprocess, threading, winreg
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(os.environ["APPDATA"]) / "espanso"
M = ROOT / "match"
EXE = Path(os.environ["LOCALAPPDATA"]) / "Programs/Espanso/espansod.exe"
LOGO = Path(__file__).with_name("espanso-logo.png")
TOKEN = secrets.token_urlsafe(16)  # empêche un site web d'appeler l'API locale
CFG = ROOT / "config/default.yml"
STARTUP = Path(os.environ["APPDATA"]) / r"Microsoft\Windows\Start Menu\Programs\Startup\espanso.lnk"
DEFAULTS = {"search_shortcut": "ALT+SPACE", "toggle_key": "OFF", "show_notifications": True,
            "show_icon": True, "undo_backspace": True}


def esp(*args):  # sortie ignorée : start/restart gardent les pipes ouverts et bloqueraient
    subprocess.Popen([EXE, *args], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=subprocess.CREATE_NO_WINDOW).wait(20)


def running():
    return "is running" in subprocess.run([EXE, "status"], capture_output=True, text=True, timeout=10,
                                          creationflags=subprocess.CREATE_NO_WINDOW).stdout


def read_cfg():
    s = CFG.read_text(encoding="utf-8") if CFG.exists() else ""
    if all(not l.strip() or l.lstrip().startswith("#") for l in s.splitlines()):
        return {}
    try:
        return json.loads(s)
    except ValueError:
        raise ValueError("Réglages modifiés à la main : utilise « Réglages avancés ».")


def settings():
    return {**DEFAULTS, **read_cfg(), "running": running(), "startup": STARTUP.exists()}


def read(f):
    return json.loads(f.read_text(encoding="utf-8"))["matches"][0]


def items():
    out = []
    for f in sorted(M.glob("*.yml"), key=lambda f: f.name.lstrip("_").lower()):
        try:
            m = read(f)
        except Exception:  # YAML écrit à la main : ignoré
            continue
        out.append({"id": f.name, "on": not f.name.startswith("_"), "trigger": m.get("trigger", ""),
                    "replace": m.get("replace", ""), "word": bool(m.get("word"))})
    return out


def file(id):
    f = M / Path(id).name
    if not f.is_file():
        raise ValueError("Raccourci introuvable, recharge la page.")
    return f


def act(d):
    op = d.get("op")
    if op == "toggle":
        f = file(d["id"])
        f.rename(f.with_name(f.name[1:] if f.name.startswith("_") else "_" + f.name))
    elif op == "delete":
        file(d["id"]).unlink()
    elif op == "save":
        t, r = d["trigger"].strip(), d["replace"]
        if not t or not r:
            raise ValueError("Remplis le raccourci et le texte.")
        if any(i["trigger"] == t and i["id"] != d.get("id") for i in items()):
            raise ValueError(f"« {t} » existe déjà.")
        if d.get("id"):
            f = file(d["id"]); m = read(f)  # garde les autres options (vars…)
        else:
            base = re.sub(r"\W", "", t) or "raccourci"
            f, n, m = M / f"{base}.yml", 1, {}
            while f.exists() or f.with_name("_" + f.name).exists():
                f, n = M / f"{base}{n}.yml", n + 1
        m.update(trigger=t, replace=r)
        m.pop("word", None)
        if d.get("word"):
            m["word"] = True
        f.write_text(json.dumps({"matches": [m]}, ensure_ascii=False, indent=1), encoding="utf-8")
    elif op == "settings":
        return settings()
    elif op == "set":
        k, v = d["key"], d["value"]
        if k == "running":
            esp("start" if v else "stop")
        elif k == "startup":
            esp("service", "register" if v else "unregister")
        elif k in DEFAULTS and type(v) is type(DEFAULTS[k]):
            c = read_cfg(); c[k] = v
            CFG.write_text(json.dumps(c, indent=1), encoding="utf-8")
            if running():
                esp("restart")
        else:
            raise ValueError("Réglage inconnu.")
        return settings()
    elif op == "advanced":
        subprocess.Popen(["notepad", CFG])
    elif op == "folder":
        os.startfile(ROOT)
    elif op == "restart":
        subprocess.Popen([EXE, "restart"], creationflags=subprocess.CREATE_NO_WINDOW)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send(self, code, body, ctype="application/json; charset=utf-8"):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/logo.png":
            return self.send(200, LOGO.read_bytes(), "image/png")
        self.send(200, PAGE.replace("__TOKEN__", TOKEN), "text/html; charset=utf-8")

    def do_POST(self):
        if self.headers.get("X-Token") != TOKEN:
            return self.send(403, "{}")
        try:
            r = act(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self.send(200, json.dumps(items() if r is None else r))
        except Exception as e:
            self.send(200, json.dumps({"error": str(e)}))


def browser():
    for exe in ("msedge.exe", "chrome.exe"):
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                return winreg.QueryValue(hive, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}")
            except OSError:
                pass


PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Raccourcis</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="/logo.png">
<style>
/* charte espanso : fond anthracite du logo + dégradé sarcelle → vert citron */
:root{--bg:#161618;--card:#212124;--line:#303034;--text:#f2f2f0;--mute:#9b9ba1;--accent:#00b5a4;--soft:#00a59524;--danger:#f2555a;
--grad:linear-gradient(120deg,#00a595,#5cc46a 55%,#d9e84a);color-scheme:dark}
*{box-sizing:border-box;margin:0}
body{font:14px/1.45 "Segoe UI Variable Text","Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--text);height:100vh;display:flex;flex-direction:column}
header{display:flex;align-items:center;gap:8px;padding:20px 24px}
h1{font:600 21px "Segoe UI Variable Display","Segoe UI",sans-serif;letter-spacing:-.01em;margin-right:auto}
h1 small{font-weight:400;font-size:13px;color:var(--mute);margin-left:8px}
input,textarea{font:inherit;color:inherit;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:9px 12px;outline:none;transition:border-color .15s,box-shadow .15s}
input:focus,textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--soft)}
#q{width:230px;margin-right:6px}
button{font:inherit;border:0;border-radius:10px;padding:9px 14px;cursor:pointer;background:none;color:var(--text);display:inline-flex;align-items:center;gap:6px;transition:background .15s,filter .15s}
.icon{padding:9px;color:var(--mute)}.icon:hover{background:var(--line);color:var(--text)}
.primary{background:var(--grad);color:#0d1f1b;font-weight:600}.primary:hover{filter:brightness(1.1)}
.logo{width:34px;height:34px;margin-right:4px}
h1 b{font-weight:600;background:var(--grad);-webkit-background-clip:text;color:transparent}
.danger{color:var(--danger)}.danger:hover{background:#e5484d14}
svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
main{flex:1;display:grid;grid-template-columns:1fr 380px;gap:16px;padding:0 24px 24px;min-height:0}
#list{overflow:auto;display:flex;flex-direction:column;gap:6px;padding:3px}
.row{display:flex;align-items:center;gap:14px;padding:13px 16px;background:var(--card);border:1px solid var(--line);border-radius:14px;cursor:pointer;transition:border-color .15s,box-shadow .15s}
.row:hover{border-color:color-mix(in srgb,var(--accent) 45%,var(--line))}
.row.sel{border-color:var(--accent);box-shadow:0 0 0 3px var(--soft)}
.row.off kbd,.row.off p{opacity:.4}
kbd{font:600 12.5px "Cascadia Code",Consolas,monospace;background:var(--soft);color:var(--accent);padding:4px 9px;border-radius:7px;white-space:nowrap}
.row p{flex:1;color:var(--mute);font-size:13px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.sw{appearance:none;width:36px;height:20px;padding:0;border:0;border-radius:99px;background:var(--line);position:relative;cursor:pointer;flex:none;transition:background .2s}
.sw::after{content:"";position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;background:#fff;box-shadow:0 1px 3px #0003;transition:transform .2s}
.sw:checked{background:var(--grad)}.sw:checked::after{transform:translateX(16px)}
aside{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px;display:flex;flex-direction:column;gap:16px}
aside h2{font-size:15px;font-weight:600}
.field{display:flex;flex-direction:column;gap:6px}.field>span{font-size:12px;font-weight:500;color:var(--mute)}
.grow{flex:1;min-height:0}textarea{flex:1;resize:none;min-height:150px}
.opt{display:flex;align-items:center;justify-content:space-between;font-size:13px;color:var(--mute);cursor:pointer}
.actions{display:flex;justify-content:space-between}
.hint{font-size:11px;opacity:.7;font-weight:400}
.empty{color:var(--mute);text-align:center;padding:48px 0}
#toast{position:fixed;bottom:22px;left:50%;transform:translate(-50%,16px);opacity:0;background:var(--text);color:var(--bg);padding:10px 16px;border-radius:10px;font-size:13px;transition:.25s;pointer-events:none}
#toast.show{opacity:1;transform:translate(-50%,0)}#toast.err{background:var(--danger);color:#fff}
.pill{font-size:12px;font-weight:600;padding:4px 11px;border-radius:99px;background:var(--soft);color:var(--accent);margin-right:auto;cursor:pointer}
.pill.off{background:#f2555a22;color:var(--danger)}
h1{margin-right:0}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
dialog{margin:auto;border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:18px;padding:0;width:min(540px,calc(100vw - 32px))}
dialog::backdrop{background:#000a;backdrop-filter:blur(4px)}
.dh{display:flex;align-items:center;justify-content:space-between;padding:18px 22px}
.dh h2{font-size:17px;font-weight:600}
.set{display:flex;align-items:center;gap:16px;padding:14px 22px;border-top:1px solid var(--line);cursor:pointer}
.set div{flex:1}.set b{display:block;font-weight:500}.set small{color:var(--mute);font-size:12.5px}
select{font:inherit;color:inherit;background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:7px 10px;outline:none;cursor:pointer}
select:focus{border-color:var(--accent)}
.df{display:flex;gap:4px;padding:12px 16px;border-top:1px solid var(--line)}
.df button{color:var(--mute);font-size:13px}.df button:hover{background:var(--line);color:var(--text)}
::-webkit-scrollbar{width:8px}::-webkit-scrollbar-thumb{background:var(--line);border-radius:9px}
@media(max-width:760px){main{grid-template-columns:1fr;overflow:auto}#q{width:140px}}
</style></head><body>
<header>
 <img class="logo" src="/logo.png" alt="">
 <h1><b>espanso</b> · Raccourcis<small id="count"></small></h1>
 <span class="pill" id="pill" title="Ouvrir les réglages" onclick="openSettings()">…</span>
 <input id="q" placeholder="Rechercher…" oninput="render()">
 <button class="icon" title="Réglages" onclick="openSettings()"><svg viewBox="0 0 24 24"><path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/></svg></button>
 <button class="primary" onclick="newOne()"><svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>Nouveau</button>
</header>
<main>
 <div id="list"></div>
 <aside>
  <h2 id="title">Nouveau raccourci</h2>
  <label class="field"><span>Raccourci</span><input id="t" placeholder="ex : -sig"></label>
  <label class="field grow"><span>Texte</span><textarea id="r" placeholder="Le texte qui sera écrit…"></textarea></label>
  <label class="opt">Mot entier uniquement<input type="checkbox" class="sw" id="w"></label>
  <div class="actions"><button class="danger" id="del" onclick="del()">Supprimer</button><button class="primary" onclick="save()">Enregistrer <span class="hint">Ctrl S</span></button></div>
 </aside>
</main>
<dialog id="dlg">
 <div class="dh"><h2>Réglages</h2><button class="icon" title="Fermer" onclick="dlg.close()"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button></div>
 <div id="sets"></div>
 <div class="df">
  <button onclick="api({op:'restart'}).then(ok=>ok&&toast('Espanso redémarré'))">↻ Redémarrer Espanso</button>
  <button onclick="api({op:'folder'})">📁 Dossier</button>
  <button onclick="api({op:'advanced'})" style="margin-left:auto">Réglages avancés</button>
 </div>
</dialog>
<div id="toast"></div>
<script>
const $ = s => document.querySelector(s); let list = [], cur = null, tid, cfg = {};
const post = async d => (await fetch("/api", {method: "POST", headers: {"X-Token": "__TOKEN__"}, body: JSON.stringify(d)})).json();
async function api(d) {
  const j = await post(d);
  if (j.error) { toast(j.error, true); return false }
  list = j; render(); return true;
}
const SETTINGS = [
  ["running", "Espanso activé", "Désactive pour mettre tous tes raccourcis en pause"],
  ["startup", "Lancer au démarrage de l'ordinateur", "Espanso s'allume tout seul quand tu allumes ton PC"],
  ["undo_backspace", "Annuler avec la touche ⌫", "Appuie sur Retour arrière juste après pour retrouver ce que tu avais tapé"],
  ["show_notifications", "Notifications", "Petits messages en bas de l'écran (démarrage, erreurs…)"],
  ["show_icon", "Icône près de l'horloge", "Affiche le logo Espanso en bas à droite de l'écran"],
  ["search_shortcut", "Recherche rapide", "Touches pour ouvrir une barre et chercher parmi tes textes",
    {"ALT+SPACE": "Alt + Espace", "CTRL+SHIFT+SPACE": "Ctrl + Maj + Espace", "off": "Désactivée"}],
  ["toggle_key", "Pause express", "Appuie 2 fois vite sur cette touche pour mettre Espanso en pause ou le relancer",
    {"OFF": "Désactivée", "ALT": "Alt", "CTRL": "Ctrl", "SHIFT": "Maj"}],
];
async function sapi(d) {
  document.body.style.cursor = "progress";
  const j = await post(d); document.body.style.cursor = "";
  if (j.error) return toast(j.error, true);
  cfg = j; renderSettings();
  if (d.op === "set") toast("C'est enregistré ✓");
}
function renderSettings() {
  $("#pill").textContent = cfg.running ? "● Actif" : "❚❚ En pause";
  $("#pill").className = "pill" + (cfg.running ? "" : " off");
  $("#sets").replaceChildren(...SETTINGS.map(([k, label, desc, opts]) => {
    const el = document.createElement("label"); el.className = "set";
    el.innerHTML = `<div><b>${label}</b><small>${desc}</small></div>`;
    let c;
    if (opts) {
      c = document.createElement("select");
      for (const [v, t] of Object.entries(opts)) c.add(new Option(t, v));
      c.value = cfg[k]; c.onchange = () => sapi({op: "set", key: k, value: c.value});
    } else {
      c = document.createElement("input"); c.type = "checkbox"; c.className = "sw";
      c.checked = cfg[k]; c.onchange = () => sapi({op: "set", key: k, value: c.checked});
    }
    el.append(c); return el;
  }));
}
function openSettings() { dlg.showModal(); sapi({op: "settings"}) }
function toast(msg, err) {
  const t = $("#toast"); t.textContent = msg; t.className = "show" + (err ? " err" : "");
  clearTimeout(tid); tid = setTimeout(() => t.className = "", 2200);
}
function render() {
  const q = $("#q").value.toLowerCase(), rows = list.filter(i => (i.trigger + i.replace).toLowerCase().includes(q));
  $("#count").textContent = `${list.filter(i => i.on).length} actifs sur ${list.length}`;
  $("#list").replaceChildren(...rows.map(row));
  if (!rows.length) $("#list").innerHTML = '<div class="empty">Aucun raccourci</div>';
}
function row(i) {
  const el = document.createElement("div");
  el.className = "row" + (i.on ? "" : " off") + (i.id === cur ? " sel" : "");
  el.innerHTML = '<kbd></kbd><p></p><input type="checkbox" class="sw" title="Activer / désactiver">';
  el.querySelector("kbd").textContent = i.trigger;
  el.querySelector("p").textContent = i.replace;
  const sw = el.querySelector(".sw"); sw.checked = i.on;
  sw.onclick = e => e.stopPropagation();
  sw.onchange = () => { if (cur === i.id) cur = i.on ? "_" + i.id : i.id.slice(1); api({op: "toggle", id: i.id}) };
  el.onclick = () => edit(i);
  return el;
}
function edit(i) {
  cur = i.id; $("#t").value = i.trigger; $("#r").value = i.replace; $("#w").checked = i.word;
  $("#title").textContent = "Modifier le raccourci"; $("#del").style.visibility = "visible"; render();
}
function newOne() {
  cur = null; $("#t").value = $("#r").value = ""; $("#w").checked = false;
  $("#title").textContent = "Nouveau raccourci"; $("#del").style.visibility = "hidden"; render(); $("#t").focus();
}
async function save() {
  const t = $("#t").value.trim();
  if (await api({op: "save", id: cur, trigger: t, replace: $("#r").value, word: $("#w").checked})) {
    edit(list.find(i => i.trigger === t)); toast("Enregistré");
  }
}
async function del() {
  if (cur && confirm(`Supprimer « ${$("#t").value} » ?`) && await api({op: "delete", id: cur})) { newOne(); toast("Supprimé") }
}
onkeydown = e => { if (e.ctrlKey && e.key === "s") { e.preventDefault(); save() } };
newOne(); api({}); sapi({op: "settings"});
</script></body></html>"""

if __name__ == "__main__":
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}/"
    # ponytail: profil dédié pour que le navigateur bloque jusqu'à la fermeture de la fenêtre ;
    # si l'app est ouverte deux fois, la 2e fenêtre ne fonctionnera pas (ferme la 1re avant).
    subprocess.run([browser(), f"--app={url}", "--window-size=1000,680",
                    f"--user-data-dir={os.environ['LOCALAPPDATA']}\\espanso-gui"])
