import sys
import json
import random
import os
import shutil
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QMessageBox, QDialog, QFormLayout,
    QDialogButtonBox, QComboBox, QFileDialog
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt

DATA_DIR = "data"
DISHES_FILE = os.path.join(DATA_DIR, "dishes.json")
RECIPES_FILE = os.path.join(DATA_DIR, "recipes.json")
IMAGES_DIR = os.path.join(DATA_DIR, "images")


def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)
    if not os.path.exists(DISHES_FILE):
        default_dishes = [
            {"name": "Spaghetti", "ingredients": ["pasta", "tomato", "garlic", "olive oil"], "image": ""},
            {"name": "Omelette", "ingredients": ["eggs", "milk", "butter", "salt"], "image": ""},
            {"name": "Grilled Cheese", "ingredients": ["bread", "cheese", "butter"], "image": ""},
            {"name": "Salad", "ingredients": ["lettuce", "tomato", "cucumber", "olive oil"], "image": ""},
            {"name": "Pancakes", "ingredients": ["flour", "milk", "egg", "butter"], "image": ""},
            {"name": "Chicken Stir Fry", "ingredients": ["chicken", "soy sauce", "garlic", "vegetables"], "image": ""},
        ]
        with open(DISHES_FILE, "w", encoding="utf-8") as f:
            json.dump(default_dishes, f, indent=2, ensure_ascii=False)
    if not os.path.exists(RECIPES_FILE):
        default_recipes = {
            "Spaghetti": "Cook pasta. Prepare tomato sauce with garlic and olive oil. Mix and serve.",
            "Omelette": "Beat eggs with milk. Cook in buttered pan. Fold and serve.",
            "Grilled Cheese": "Butter bread, add cheese, grill until golden brown.",
        }
        with open(RECIPES_FILE, "w", encoding="utf-8") as f:
            json.dump(default_recipes, f, indent=2, ensure_ascii=False)


def load_dishes():
    with open(DISHES_FILE, "r", encoding="utf-8") as f:
        dishes = json.load(f)
    # Ensure every dish has an image key
    for d in dishes:
        if "image" not in d:
            d["image"] = ""
    return dishes


def save_dishes(dishes):
    with open(DISHES_FILE, "w", encoding="utf-8") as f:
        json.dump(dishes, f, indent=2, ensure_ascii=False)


def load_recipes():
    with open(RECIPES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_recipes(recipes):
    with open(RECIPES_FILE, "w", encoding="utf-8") as f:
        json.dump(recipes, f, indent=2, ensure_ascii=False)


class AddDishDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Dish")
        self.setModal(True)
        self.layout = QFormLayout(self)

        self.name_edit = QLineEdit(self)
        self.ingredients_edit = QLineEdit(self)
        self.ingredients_edit.setPlaceholderText("Comma-separated, e.g. tomato, garlic, pasta")

        self.layout.addRow("Dish name:", self.name_edit)
        self.layout.addRow("Ingredients:", self.ingredients_edit)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def get_data(self):
        name = self.name_edit.text().strip()
        ingredients = [s.strip().lower() for s in self.ingredients_edit.text().split(",") if s.strip()]
        return name, ingredients


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cook Picker")
        self.resize(940, 560)

        ensure_data_dir()
        self.dishes = load_dishes()
        self.recipes = load_recipes()

        # session pools
        self.reset_available_pool()

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self.make_cook_tab(), "Cook")
        tabs.addTab(self.make_recipes_tab(), "Recipes")
        tabs.addTab(self.make_settings_tab(), "Settings")

        self.setCentralWidget(tabs)

    def reset_available_pool(self):
        self.available = list(self.dishes)
        self.filtered = list(self.available)
        self.current_choice = None

    # ---------- Helpers ----------
    def dish_by_name(self, name):
        for d in self.dishes:
            if d["name"] == name:
                return d
        return None

    def get_image_abs_path(self, image_rel):
        if not image_rel:
            return ""
        # image_rel is stored relative to DATA_DIR, e.g. "images/my_dish_12345.jpg"
        abs_path = os.path.join(DATA_DIR, image_rel) if not os.path.isabs(image_rel) else image_rel
        return abs_path if os.path.exists(abs_path) else ""

    def show_pixmap_in_label(self, label: QLabel, image_rel):
        abs_path = self.get_image_abs_path(image_rel)
        if abs_path:
            pix = QPixmap(abs_path)
            if not pix.isNull():
                scaled = pix.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label.setPixmap(scaled)
                label.setText("")
                return
        # fallback
        label.setPixmap(QPixmap())
        label.setText("(No image)")

    # ---------- Cook Tab ----------
    def make_cook_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Filter area
        filter_layout = QHBoxLayout()
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Type ingredients (comma-separated) to filter, e.g. tomato, garlic")
        filter_layout.addWidget(QLabel("Filter by ingredients:"))
        filter_layout.addWidget(self.filter_input)
        self.filter_btn = QPushButton("Filter")
        self.filter_btn.clicked.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_btn)
        self.reset_filter_btn = QPushButton("Reset filter")
        self.reset_filter_btn.clicked.connect(self.reset_filter)
        filter_layout.addWidget(self.reset_filter_btn)
        layout.addLayout(filter_layout)

        # Image + chosen display
        choose_layout = QVBoxLayout()

        self.image_label = QLabel("(No image)")
        self.image_label.setFixedSize(420, 260)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #87CEFA; background: #FFFFFF;")
        choose_layout.addWidget(self.image_label, alignment=Qt.AlignCenter)

        self.chosen_label = QLabel("No dish chosen yet.")
        self.chosen_label.setAlignment(Qt.AlignCenter)
        self.chosen_label.setStyleSheet("font-weight: bold;")
        choose_layout.addWidget(self.chosen_label)

        btn_row = QHBoxLayout()
        self.choose_btn = QPushButton("Choose Random")
        self.choose_btn.clicked.connect(self.choose_random)
        btn_row.addWidget(self.choose_btn)

        self.dislike_btn = QPushButton("Don't like — pick again")
        self.dislike_btn.clicked.connect(self.dislike_and_pick_again)
        self.dislike_btn.setEnabled(False)
        btn_row.addWidget(self.dislike_btn)

        self.reset_choices_btn = QPushButton("Reset choices")
        self.reset_choices_btn.clicked.connect(self.reset_choices)
        btn_row.addWidget(self.reset_choices_btn)

        choose_layout.addLayout(btn_row)

        # Remaining counter (no visible list)
        rem_layout = QHBoxLayout()
        rem_layout.addStretch()
        self.remaining_label = QLabel(f"Remaining dishes: {len(self.filtered)}")
        rem_layout.addWidget(self.remaining_label)
        rem_layout.addStretch()
        choose_layout.addLayout(rem_layout)

        layout.addLayout(choose_layout)
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def apply_filter(self):
        text = self.filter_input.text().strip()
        if not text:
            self.filtered = list(self.available)
        else:
            wanted = [t.strip().lower() for t in text.split(",") if t.strip()]
            def matches(dish):
                dish_ing = [i.lower() for i in dish.get("ingredients", [])]
                return all(w in dish_ing for w in wanted)
            self.filtered = [d for d in self.available if matches(d)]
        self.update_remaining_label()

    def reset_filter(self):
        self.filter_input.clear()
        self.filtered = list(self.available)
        self.update_remaining_label()

    def update_remaining_label(self):
        self.remaining_label.setText(f"Remaining dishes: {len(self.filtered)}")
        # enable/disable choose button
        self.choose_btn.setEnabled(bool(self.filtered))
        if not self.filtered:
            self.chosen_label.setText("No dishes available (filter/removed).")
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("(No image)")

    def choose_random(self):
        pool = self.filtered
        if not pool:
            QMessageBox.information(self, "No dishes", "No dishes available to choose from. Reset choices or filters.")
            return
        choice = random.choice(pool)
        self.current_choice = choice
        self.chosen_label.setText(choice["name"])
        # show image
        self.show_pixmap_in_label(self.image_label, choice.get("image", ""))
        self.dislike_btn.setEnabled(True)

    def dislike_and_pick_again(self):
        if not self.current_choice:
            return
        name = self.current_choice["name"]
        # remove from available and filtered pools
        self.available = [d for d in self.available if d["name"] != name]
        self.filtered = [d for d in self.filtered if d["name"] != name]
        self.current_choice = None
        self.chosen_label.setText("Removed. Picked a different one?")
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("(No image)")
        self.dislike_btn.setEnabled(False)
        self.update_remaining_label()
        if self.filtered:
            self.choose_random()
        else:
            QMessageBox.information(self, "No more", "All dishes removed from current pool. Use Reset choices to restore.")

    def reset_choices(self):
        self.reset_available_pool()
        self.update_remaining_label()
        self.chosen_label.setText("Choices reset. Ready to choose.")
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("(No image)")
        self.dislike_btn.setEnabled(False)

    # ---------- Recipes Tab ----------
    def make_recipes_tab(self):
        widget = QWidget()
        layout = QHBoxLayout()

        left = QVBoxLayout()
        left.addWidget(QLabel("Select dish"))
        self.recipes_combo = QComboBox()
        left.addWidget(self.recipes_combo)
        layout.addLayout(left, 1)

        right = QVBoxLayout()
        # Image for selected dish in recipes tab
        self.recipe_image_label = QLabel("(No image)")
        self.recipe_image_label.setFixedSize(320, 200)
        self.recipe_image_label.setAlignment(Qt.AlignCenter)
        self.recipe_image_label.setStyleSheet("border: 1px solid #87CEFA; background: #FFFFFF;")
        right.addWidget(self.recipe_image_label, alignment=Qt.AlignCenter)

        right.addWidget(QLabel("Recipe"))
        self.recipe_text = QTextEdit()
        self.recipe_text.setReadOnly(True)
        right.addWidget(self.recipe_text, 1)

        btn_row = QHBoxLayout()
        self.edit_recipe_btn = QPushButton("Edit / Add recipe")
        self.edit_recipe_btn.clicked.connect(self.toggle_edit_recipe)
        btn_row.addWidget(self.edit_recipe_btn)
        self.save_recipe_btn = QPushButton("Save recipe")
        self.save_recipe_btn.clicked.connect(self.save_current_recipe)
        self.save_recipe_btn.setEnabled(False)
        btn_row.addWidget(self.save_recipe_btn)

        # Add/Change image button
        self.change_image_btn = QPushButton("Add / Change picture")
        self.change_image_btn.clicked.connect(self.add_change_picture_for_selected)
        btn_row.addWidget(self.change_image_btn)

        right.addLayout(btn_row)

        layout.addLayout(right, 2)
        widget.setLayout(layout)

        # Populate combo and connect signal
        self.populate_recipes_combo()
        self.recipes_combo.currentIndexChanged.connect(self.on_recipe_selection_changed)

        return widget

    def populate_recipes_combo(self):
        # Ensure combo exists
        if not hasattr(self, "recipes_combo"):
            return
        self.recipes_combo.clear()
        for d in sorted(self.dishes, key=lambda x: x["name"].lower()):
            self.recipes_combo.addItem(d["name"])
        # Trigger initial update
        if hasattr(self, "recipe_text"):
            self.on_recipe_selection_changed()

    def on_recipe_selection_changed(self):
        # Defensive: ensure recipe_text exists
        if not hasattr(self, "recipe_text"):
            return
        name = self.recipes_combo.currentText()
        if not name:
            self.recipe_text.clear()
            self.recipe_text.setReadOnly(True)
            self.save_recipe_btn.setEnabled(False)
            self.recipe_image_label.setPixmap(QPixmap())
            self.recipe_image_label.setText("(No image)")
            return
        rec = self.recipes.get(name, "")
        if not rec:
            self.recipe_text.setPlainText("(No recipe yet. Click 'Edit / Add recipe' to write one.)")
            self.recipe_text.setReadOnly(True)
            self.save_recipe_btn.setEnabled(False)
        else:
            self.recipe_text.setPlainText(rec)
            self.recipe_text.setReadOnly(True)
            self.save_recipe_btn.setEnabled(False)
        # show image (if any)
        dish = self.dish_by_name(name)
        if dish:
            self.show_pixmap_in_label(self.recipe_image_label, dish.get("image", ""))
        else:
            self.recipe_image_label.setPixmap(QPixmap())
            self.recipe_image_label.setText("(No image)")

    def toggle_edit_recipe(self):
        name = self.recipes_combo.currentText()
        if not name:
            QMessageBox.information(self, "Select dish", "Please select a dish to edit/add a recipe.")
            return
        self.recipe_text.setReadOnly(False)
        self.save_recipe_btn.setEnabled(True)

    def save_current_recipe(self):
        name = self.recipes_combo.currentText()
        if not name:
            return
        content = self.recipe_text.toPlainText().strip()
        if not content:
            if name in self.recipes:
                confirm = QMessageBox.question(self, "Delete recipe?", "Recipe is empty. Remove the saved recipe?")
                if confirm != QMessageBox.Yes:
                    return
                self.recipes.pop(name, None)
        else:
            self.recipes[name] = content
        save_recipes(self.recipes)
        QMessageBox.information(self, "Saved", f"Recipe for '{name}' saved.")
        self.recipe_text.setReadOnly(True)
        self.save_recipe_btn.setEnabled(False)

    def add_change_picture_for_selected(self):
        name = self.recipes_combo.currentText()
        if not name:
            QMessageBox.information(self, "Select dish", "Please select a dish first.")
            return
        # Ask user to pick an image file
        src_path, _ = QFileDialog.getOpenFileName(self, "Select image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if not src_path:
            return
        # copy into data/images with unique name
        _, ext = os.path.splitext(src_path)
        slug = name.lower().replace(" ", "_")
        filename = f"{slug}_{int(time.time())}{ext}"
        dest_rel = os.path.join("images", filename)  # stored relative to DATA_DIR
        dest_abs = os.path.join(DATA_DIR, dest_rel)
        try:
            shutil.copy2(src_path, dest_abs)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not copy image: {e}")
            return
        # update dish record and save
        dish = self.dish_by_name(name)
        if dish is None:
            QMessageBox.critical(self, "Error", "Dish not found in data.")
            return
        dish["image"] = dest_rel
        save_dishes(self.dishes)
        # refresh UI (both recipe image and cook image if that dish is currently selected)
        self.show_pixmap_in_label(self.recipe_image_label, dest_rel)
        if self.current_choice and self.current_choice.get("name") == name:
            self.show_pixmap_in_label(self.image_label, dest_rel)
        QMessageBox.information(self, "Saved", f"Picture saved for '{name}'.")

    # ---------- Settings Tab ----------
    def make_settings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Add new dish"))
        add_btn = QPushButton("Add dish")
        add_btn.clicked.connect(self.open_add_dialog)
        layout.addWidget(add_btn)

        layout.addSpacing(12)
        layout.addWidget(QLabel("Note: dishes and recipes are stored in data/dishes.json and data/recipes.json"))
        layout.addSpacing(8)

        # Exit button
        exit_btn = QPushButton("Exit")
        exit_btn.clicked.connect(self.exit_app)
        layout.addWidget(exit_btn)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def open_add_dialog(self):
        dialog = AddDishDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, ingredients = dialog.get_data()
            if not name:
                QMessageBox.warning(self, "Invalid", "Dish name cannot be empty.")
                return
            if any(d["name"].lower() == name.lower() for d in self.dishes):
                QMessageBox.warning(self, "Duplicate", "A dish with that name already exists.")
                return
            new = {"name": name, "ingredients": ingredients, "image": ""}
            self.dishes.append(new)
            save_dishes(self.dishes)
            # update UI
            self.reset_available_pool()
            self.populate_recipes_combo()
            self.update_remaining_label()
            # Explicit popup feedback (styled by app stylesheet)
            QMessageBox.information(self, "Saved", f"Dish '{name}' saved successfully.")

    def exit_app(self):
        confirm = QMessageBox.question(self, "Exit", "Are you sure you want to exit?")
        if confirm == QMessageBox.Yes:
            QApplication.instance().quit()

    def reload_data(self):
        self.dishes = load_dishes()
        self.recipes = load_recipes()
        self.reset_available_pool()
        self.populate_recipes_combo()
        self.update_remaining_label()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Try to set the requested font (Tagesschrift). If not installed, system will fallback.
    base_font = QFont("Tagesschrift", 16)
    app.setFont(base_font)

    # Global stylesheet using requested color palette:
    stylesheet = """
    QMainWindow {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #F3E8FF, stop:0.5 #FFEFF3, stop:1 #FFFFFF);
    }
    QLabel {
        color: #000000;
        font-family: "Tagesschrift", sans-serif;
        font-size: 16pt;
    }
    QPushButton {
        background-color: #FFC0CB; /* pink */
        color: #000000;
        border: 1px solid #E6E6FA;
        border-radius: 8px;
        padding: 8px;
        font-family: "Tagesschrift", sans-serif;
        font-size: 14pt;
    }
    QPushButton:hover {
        background-color: #FFB6C1; /* lighter pink */
    }
    QPushButton:pressed {
        background-color: #E6E6FA; /* light purple */
    }
    QTabBar::tab {
        background: #E6E6FA; /* light purple */
        color: #000000;
        padding: 8px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        margin-right: 4px;
        font-family: "Tagesschrift", sans-serif;
        font-size: 14pt;
    }
    QTabWidget::pane {
        border: 1px solid #87CEFA; /* blue */
        background: rgba(255,255,255,0.8);
        border-radius: 10px;
        padding: 12px;
    }
    QTextEdit {
        background: #FFFFFF;
        color: #000000;
        border: 1px solid #87CEFA; /* blue */
        border-radius: 6px;
        padding: 8px;
        font-family: "Tagesschrift", sans-serif;
        font-size: 14pt;
    }
    QComboBox, QLineEdit {
        background: #FFFFFF;
        border: 1px solid #87CEFA;
        border-radius: 6px;
        padding: 6px;
        font-family: "Tagesschrift", sans-serif;
        font-size: 14pt;
    }
    QMessageBox QLabel {
        font-family: "Tagesschrift", sans-serif;
        font-size: 14pt;
    }
    """
    app.setStyleSheet(stylesheet)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())