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
.pchips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:6px}
.pchip{display:inline-grid;place-items:center;min-width:40px;height:40px;border:1px solid var(--line);border-radius:999px;text-decoration:none;color:var(--fg);font-weight:700;background:var(--surface)}
.pchip.on{background:var(--basil);border-color:var(--basil);color:#fff}
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


MAX_PORTIONS = 12


def scaled(r, n):
    """Zutaten auf n Portionen umgerechnet."""
    base = float(r.get("servings") or 2)
    f = n / base
    out = []
    for i in r.get("ingredients", []):
        if not i.get("name"):
            continue
        j = dict(i)
        if j.get("amount") is not None:
            j["amount"] = round(float(j["amount"]) * f, 2)
        out.append(j)
    return out


def portion_word(n):
    return "Portion" if n == 1 else "Portionen"


def recipe_ld(r, n=None):
    n = n or (r.get("servings") or 2)
    ings = scaled(r, n) if n != (r.get("servings") or 2) else [i for i in r.get("ingredients", []) if i.get("name")]
    ld = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": r.get("title", "Rezept"),
        "author": {"@type": "Person", "name": r.get("author") or "Unser Rezeptbuch"},
        "recipeIngredient": [ing_line(i) for i in ings],
        "recipeInstructions": [{"@type": "HowToStep", "text": s} for s in r.get("steps", [])],
        "recipeYield": f"{fmt_num(n)} {portion_word(n)}",
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


def recipe_page(r, n=None):
    e = html.escape
    base_n = r.get("servings") or 2
    n = n or base_n
    img = f'<img class="hero" src="{e(img_url(r["photo"]))}" alt="{e(r["title"])}">' if r.get("photo") else ""
    ings = "".join(f"<li>{e(ing_line(i))}</li>" for i in scaled(r, n))
    steps = "".join(f"<li>{e(s)}</li>" for s in r.get("steps", []))
    meta = " · ".join(x for x in [r.get("cuisine"), r.get("meal"), f"{r['time']} Min." if r.get("time") else None] if x)
    choices = " ".join(
        f'<a class="pchip{" on" if k == n else ""}" href="{e(r["id"])}-{k}.html">{k}</a>' for k in range(1, MAX_PORTIONS + 1))
    body = f"""{img}<h1>{e(r['title'])}</h1><p class="small">{e(meta)}</p>
<div class="box"><h2>Für {fmt_num(n)} {portion_word(n)}</h2><div class="pchips">{choices}</div>
<p class="small">Portionen wählen, dann unten auf den Bring!-Knopf tippen.</p></div>
{BRING}
<div class="box"><h2>Zutaten für {fmt_num(n)} {portion_word(n)}</h2><ul>{ings}</ul></div>
<div class="box"><h2>Zubereitung</h2><ol>{steps}</ol></div>"""
    return page(r["title"], recipe_ld(r, n), body)


def cookbook_page(recipes):
    """Druckbares Kochbuch mit allen Rezepten (zum Speichern als PDF)."""
    e = html.escape
    order = ["Frühstück", "Hauptgericht", "Suppe", "Salat", "Beilage", "Snack", "Dessert", "Kuchen & Gebäck", "Brot", "Getränk"]
    by_meal = {}
    for r in recipes:
        by_meal.setdefault(r.get("meal") or "Sonstiges", []).append(r)
    meals = sorted(by_meal, key=lambda m: order.index(m) if m in order else 99)
    titles = {r["id"]: r["title"] for r in recipes}
    toc, parts = [], []
    for m in meals:
        rs = sorted(by_meal[m], key=lambda r: r["title"].lower())
        toc.append(f"<h3>{e(m)}</h3><ol class='toc'>" + "".join(f"<li><a href='#{e(r['id'])}'>{e(r['title'])}</a></li>" for r in rs) + "</ol>")
        for r in rs:
            meta = " · ".join(x for x in [r.get("art"), m, r.get("cuisine"), f"{r['time']} Min." if r.get("time") else None,
                                           f"{fmt_num(r.get('servings') or 2)} {portion_word(r.get('servings') or 2)}",
                                           "Meal-Prep" if r.get("mealprep") else None] if x)
            img = f'<img src="{e(img_url(r["photo"]))}" alt="">' if r.get("photo") else ""
            ings = "".join(f"<li>{e(ing_line(i))}</li>" for i in r.get("ingredients", []) if i.get("name"))
            steps = "".join(f"<li>{e(s)}</li>" for s in r.get("steps", []))
            extra = ""
            if r.get("parentId") and r["parentId"] in titles:
                extra += f"<p class='small'>Gehört zu: {e(titles[r['parentId']])}</p>"
            if r.get("notes"):
                extra += f"<div class='notes'><b>Notizen:</b> {e(r['notes'])}</div>"
            if r.get("source"):
                extra += f"<p class='small'>Quelle: {e(r['source'])}</p>"
            tags = ", ".join(r.get("tags") or [])
            parts.append(f"""<article id="{e(r['id'])}">{img}<h2>{e(r['title'])}</h2><p class="small">{e(meta)}{(' · ' + e(tags)) if tags else ''}</p>
<div class="cols"><div><h4>Zutaten</h4><ul>{ings}</ul></div><div><h4>Zubereitung</h4><ol>{steps}</ol></div></div>{extra}</article>""")
    stand = datetime.now(timezone.utc).astimezone().strftime("%d.%m.%Y")
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Unser Rezeptbuch – Kochbuch</title>
{FONTS}
<style>{CSS}
main{{max-width:820px}}
.bar{{display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
.pbtn{{border:0;background:var(--basil);color:#fff;font:inherit;font-weight:700;padding:10px 18px;border-radius:999px;cursor:pointer}}
.cover{{text-align:center;padding:40px 0 10px}}.cover h1{{font-size:2.6rem}}
.toc{{columns:2;column-gap:32px;margin:0 0 12px}}h3{{margin:14px 0 6px}}
article{{border-top:1px solid var(--line);padding-top:20px}}article img{{width:100%;max-height:320px;object-fit:cover;border-radius:12px}}
article h2{{font-family:"Bricolage Grotesque",system-ui,sans-serif;font-size:1.5rem;margin:8px 0 2px}}
.cols{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.6fr);gap:24px}}h4{{margin:10px 0 4px}}
.notes{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-top:10px;white-space:pre-wrap}}
@media (max-width:640px){{.cols{{grid-template-columns:1fr}}.toc{{columns:1}}}}
@media print{{:root{{--bg:#fff;--fg:#000;--muted:#444;--line:#bbb;--surface:#fff;color-scheme:light}}
body{{padding:0;font-size:11pt}}.noprint{{display:none!important}}article{{break-before:page;border:0}}
.cover{{padding-top:30vh}}.tocwrap{{break-before:page}}a{{color:inherit;text-decoration:none}}article img{{max-height:7cm}}}}
</style></head><body><main>
<div class="bar noprint"><a class="back" href="index.html">← Zum Rezeptbuch</a><button class="pbtn" onclick="window.print()">Drucken / als PDF sichern</button>
<span class="small">iPhone: Teilen → Drucken → in der Vorschau „Als PDF sichern“ bzw. Teilen → In Dateien sichern.</span></div>
<div class="cover"><h1>Unser Rezeptbuch</h1><p class="small">{len(recipes)} Rezepte · Stand {stand}</p></div>
<div class="tocwrap"><h2>Inhalt</h2>{''.join(toc)}</div>
{''.join(parts)}
</main></body></html>
"""


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
            for n in range(1, MAX_PORTIONS + 1):
                (rdir / f"{r['id']}-{n}.html").write_text(recipe_page(r, n), encoding="utf-8")
    (OUT / "kochbuch.html").write_text(cookbook_page([r for r in recipes if r.get("id") and r.get("title")]), encoding="utf-8")
    # Rezeptseiten liegen eine Ebene tiefer; die Einkaufsseite liegt oben und braucht einen anderen Zurück-Link
    shop_html = shopping_page(shop, recipes).replace('href="../index.html"', 'href="index.html"')
    (OUT / "einkauf.html").write_text(shop_html, encoding="utf-8")
    print(f"{len(recipes)} Rezeptseiten und die Einkaufsliste gebaut")


if __name__ == "__main__":
    main()
