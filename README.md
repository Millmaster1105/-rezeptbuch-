# Unser Rezeptbuch

Gemeinsames Rezeptbuch als Web-App auf GitHub Pages: Rezepte mit Fotos und YouTube-Links, Filter nach Landesküche, Meal-Prep und Gerät, Kühlschrank-Suche, Wochenplaner, Einkaufsliste mit Bring!-Export, Timer, geschätzte Nährwerte und Varianten.

Alle Daten liegen in diesem Repository:

| Datei | Inhalt |
|---|---|
| `data/recipes.json` | alle Rezepte |
| `data/plan.json` | Wochenplan |
| `data/fridge.json` | Kühlschrank und Vorrat |
| `data/shopping.json` | Einkaufsliste |
| `images/` | Fotos |

`build.py` erzeugt bei jedem Push über GitHub Actions die öffentliche Seite samt Rezeptseiten (`r/<id>.html`) und Einkaufsliste (`einkauf.html`) mit schema.org-Daten für Bring!.

Einrichtung: siehe [ANLEITUNG.md](ANLEITUNG.md).
