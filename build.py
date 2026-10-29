#!/usr/bin/env python3
"""Baut die GitHub-Pages-Seite des Rezeptbuchs.

Kopiert die App nach _site/ und erzeugt zusätzlich:
  - r/<id>.html   eine öffentliche Seite pro Rezept
  - einkauf.html  die aktuelle Einkaufsliste
Beide enthalten maschinenlesbare Rezeptdaten (schema.org, JSON-LD) und den
offiziellen Bring!-Import-Knopf, damit Bring die Zutaten übernehmen kann.
"""
import html
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
REPO = os.environ.get("GITHUB_REPOSITORY", "")  # owner/repo

COPY = ["index.html", "manifest.webmanifest", "icon.svg", "icon-180.png", "icon-512.png", "data", "images"]


def load(name, default):
    p = ROOT / "data" / name
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def fmt_num(n):
    if n is None:
        return ""
    r = round(float(n), 2)
    if r == int(r):
        return str(int(r))
    return str(r).replace(".", ",")


def ing_line(i):
    parts = [fmt_num(i.get("amount")), i.get("unit") or "", i.get("name") or ""]
    return " ".join(p for p in parts if p).strip()


def img_url(path):
    if not path:
        return None
    if path.startswith("http"):
        return path
    if SITE_URL:
        return f"{SITE_URL}/{path}"
    if REPO:
        return f"https://raw.githubusercontent.com/{REPO}/main/{path}"
    return path


BRING = """
<div class="bring">
  <div data-bring-import style="display:none"></div>
  <script async src="https://platform.getbring.com/widgets/import.js"></script>
  <p class="small"><a href="https://www.getbring.com" rel="noopener">Bring! Einkaufsliste App für iPhone und Android</a></p>
</div>"""

CSS = """
:root{--bg:#f6f7f2;--fg:#1d231b;--muted:#5d6858;--line:#d9ded0;--basil:#2f6b3a;--surface:#fff;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#141812;--fg:#e9eee5;--muted:#a2ad9c;--line:#323b2e;--basil:#7dc28a;--surface:#1c2119;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 "Atkinson Hyperlegible",system-ui,-apple-system,sans-serif;
padding:max(16px,env(safe-area-inset-top)) max(16px,env(safe-area-inset-right)) 48px max(16px,env(safe-area-inset-left))}
main{max-width:720px;margin:0 auto;display:grid;gap:18px}h1{font-family:"Bricolage Grotesque",system-ui,sans-serif;font-size:2rem;line-height:1.15;margin:0}
h2{font-size:1.1rem;margin:0 0 8px}img.hero{width:100%;border-radius:14px;aspect-ratio:16/10;object-fit:cover}
.box{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px}ul,ol{margin:0;padding-left:1.2em}li{margin:4px 0}
.small{font-size:.86rem;color:var(--muted)}a{color:var(--basil)}.back{font-weight:700;text-decoration:none}
.bring{background:var(--surface);border:2px solid var(--basil);border-radius:14px;padding:16px;display:grid;gap:8px}
"""

FONTS = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,800&family=Atkinson+Hyperlegible:wght@400;700&display=swap">'


def page(title, ld, body):
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{html.escape(title)}</title>
{FONTS}
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")}</script>
</head><body><main>
<a class="back" href="../index.html">← Zum Rezeptbuch</a>
{body}
</main></body></html>
"""


def recipe_ld(r):
    ld = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": r.get("title", "Rezept"),
        "author": {"@type": "Person", "name": r.get("author") or "Unser Rezeptbuch"},
        "recipeIngredient": [ing_line(i) for i in r.get("ingredients", []) if i.get("name")],
        "recipeInstructions": [{"@type": "HowToStep", "text": s} for s in r.get("steps", [])],
        "recipeYield": f"{fmt_num(r.get('servings') or 2)} Portionen",
    }
    if r.get("time"):
        ld["totalTime"] = f"PT{int(r['time'])}M"
    if r.get("cuisine"):
        ld["recipeCuisine"] = r["cuisine"]
    if r.get("meal"):
        ld["recipeCategory"] = r["meal"]
    if r.get("photo"):
        ld["image"] = [img_url(r["photo"])]
    if r.get("source"):
        ld["isBasedOn"] = r["source"]
    return ld


def recipe_page(r):
    e = html.escape
    img = f'<img class="hero" src="{e(img_url(r["photo"]))}" alt="{e(r["title"])}">' if r.get("photo") else ""
    ings = "".join(f"<li>{e(ing_line(i))}</li>" for i in r.get("ingredients", []) if i.get("name"))
    steps = "".join(f"<li>{e(s)}</li>" for s in r.get("steps", []))
    meta = " · ".join(x for x in [r.get("cuisine"), r.get("meal"), f"{r['time']} Min." if r.get("time") else None,
                                   f"{fmt_num(r.get('servings') or 2)} Portionen"] if x)
    body = f"""{img}<h1>{e(r['title'])}</h1><p class="small">{e(meta)}</p>
{BRING}
<div class="box"><h2>Zutaten</h2><ul>{ings}</ul></div>
<div class="box"><h2>Zubereitung</h2><ol>{steps}</ol></div>"""
    return page(r["title"], recipe_ld(r), body)


def shopping_page(shop, recipes):
    e = html.escape
    items = [i for i in shop.get("items", []) if not i.get("checked") and i.get("name")]
    lines = [ing_line(i) for i in items]
    ts = shop.get("updatedAt")
    when = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).astimezone().strftime("%d.%m.%Y, %H:%M") if ts else "–"
    photo = next((r.get("photo") for r in recipes if r.get("photo")), None)
    ld = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": "Einkaufsliste aus unserem Rezeptbuch",
        "author": {"@type": "Person", "name": "Unser Rezeptbuch"},
        "recipeIngredient": lines,
        "recipeYield": "1",
        "recipeInstructions": [{"@type": "HowToStep", "text": "Einkaufen gehen."}],
    }
    if photo:
        ld["image"] = [img_url(photo)]
    lis = "".join(f"<li>{e(l)}</li>" for l in lines) or "<li>Die Liste ist leer.</li>"
    body = f"""<h1>Einkaufsliste</h1><p class="small">{len(lines)} Einträge · Stand {e(when)}</p>
{BRING}
<div class="box"><ul>{lis}</ul></div>
<p class="small">Tippe oben auf den Bring!-Knopf, um alles in deine Bring!-Liste zu übernehmen.</p>"""
    return page("Einkaufsliste", ld, body)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for name in COPY:
        src = ROOT / name
        if src.is_dir():
            shutil.copytree(src, OUT / name)
        elif src.exists():
            shutil.copy2(src, OUT / name)
    (OUT / "images").mkdir(exist_ok=True)
    (OUT / ".nojekyll").write_text("")

    recipes = load("recipes.json", {"recipes": []}).get("recipes", [])
    shop = load("shopping.json", {"items": []})

    rdir = OUT / "r"
    rdir.mkdir()
    for r in recipes:
        if r.get("id") and r.get("title"):
            (rdir / f"{r['id']}.html").write_text(recipe_page(r), encoding="utf-8")
    # Rezeptseiten liegen eine Ebene tiefer; die Einkaufsseite liegt oben und braucht einen anderen Zurück-Link
    shop_html = shopping_page(shop, recipes).replace('href="../index.html"', 'href="index.html"')
    (OUT / "einkauf.html").write_text(shop_html, encoding="utf-8")
    print(f"{len(recipes)} Rezeptseiten und die Einkaufsliste gebaut")


if __name__ == "__main__":
    main()
