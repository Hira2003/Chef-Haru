# Simple Cook Picker (PyQt + JSON)

A small PyQt5 app to randomly choose a dish to cook, keep dishes in JSON, add dishes, edit recipes, and filter by ingredients.

Requirements
- Python 3.8+
- PyQt5

Install:
```
pip install -r requirements.txt
```

Run:
```
python main.py
```

Files
- main.py — the PyQt5 application
- data/dishes.json — sample dishes (name + ingredients)
- data/recipes.json — sample recipes (map dish -> recipe)
- requirements.txt

Usage notes
- "Choose Random" selects a dish randomly from the currently filtered/available list.
- If you dislike a selection, click "Don't like — pick again"; that dish is removed from the current pool (temporarily) so it won't be picked again until you use "Reset choices".
- Add dishes in Settings. Add recipes in the Recipes tab.
- Data is saved to `data/dishes.json` and `data/recipes.json`.
