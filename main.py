import sqlite3
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget, QApplication, QMessageBox, QListWidgetItem, QDialog, QInputDialog)

from tasks import Ui_Form as tasksForm
from categories import Ui_Form as categoriesForm

DATABASE_NAME = 'tasks_db.db'


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


def createTables(con):
    try:
        with con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE
                );
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                description TEXT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                category_id INTEGER NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories (id) 
                ON DELETE CASCADE
                );
            """)
    except sqlite3.DatabaseError as e:
        print(f'{e.__class__.__name__}: {e}')
        sys.exit(-1)


class Categories(QDialog, categoriesForm):
    def __init__(self, con):
        super().__init__()
        self.setupUi(self)
        self.con = con
        self.loadCategories()
        self.addCategoryButton.clicked.connect(self.addCategory)
        self.deleteCategoryButton.clicked.connect(self.deleteCategory)

    def loadCategories(self):
        """Загрузка и вывод категорий в categoriesList."""
        self.categoriesList.clear()
        cursor = self.con.cursor()
        cursor.execute("SELECT title FROM categories")
        categories = cursor.fetchall()
        for category in categories:
            self.categoriesList.addItem(category[0])

    def addCategory(self):
        """Добавление категории с помощью ввода
        имени категории в QInputDialog.
        """
        name, ok = QInputDialog.getText(self, "Добавить категорию", "Название:")
        if ok and name:
            cursor = self.con.cursor()
            cursor.execute("INSERT INTO categories (title) VALUES (?)", (name,))
            self.con.commit()
            self.loadCategories()

    def deleteCategory(self):
        """Удаление категории с подтверждением через QMessageBox."""
        item = self.categoriesList.currentItem()
        if item:
            reply = QMessageBox.question(self, "Удалить категорию", f"Вы точно хотите удалить '{item.text()}'?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                cursor = self.con.cursor()
                cursor.execute("DELETE FROM categories WHERE title=?", (item.text(),))
                self.con.commit()
                self.loadCategories()


class Tasks(QWidget, tasksForm):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.con = sqlite3.connect(DATABASE_NAME)
        createTables(self.con)
        self.con.execute("PRAGMA foreign_keys = 1")
        self.loadTasks()
        self.loadCategories()
        self.tasksList.itemClicked.connect(self.taskDetail)
        self.addTaskButton.clicked.connect(self.addTask)
        self.deleteTaskButton.clicked.connect(self.deleteTask)
        self.filterCategory.currentIndexChanged.connect(self.loadTasks)
        self.categoriesButton.clicked.connect(self.showCategories)

    def loadTasks(self):
        """Загрузка и вывод задач в tasksList.
        Выполненные задачи выводятся со статусом CheckState.Checked.
        Если в filterCategory установлено значение категории, то выводятся
        только задачи выбранной категории.
        """
        self.tasksList.clear()
        cursor = self.con.cursor()
        filter_category = self.filterCategory.currentText()
        if filter_category:
            cursor.execute("""
                SELECT tasks.title, tasks.description, tasks.done 
                FROM tasks 
                JOIN categories ON tasks.category_id = categories.id 
                WHERE categories.title = ?
            """, (filter_category,))
        else:
            cursor.execute("SELECT title, description, done FROM tasks")
        tasks = cursor.fetchall()
        for title, description, done in tasks:
            item = QListWidgetItem(title)
            item.setCheckState(Qt.CheckState.Checked if done else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, description)
            self.tasksList.addItem(item)

    def loadCategories(self):
        """Загрузка и вывод задач в виджеты
        selectCategory и filterCategory.
        """
        self.selectCategory.clear()
        self.filterCategory.clear()
        cursor = self.con.cursor()
        cursor.execute("SELECT title FROM categories")
        categories = cursor.fetchall()
        for category in categories:
            self.selectCategory.addItem(category[0])
            self.filterCategory.addItem(category[0])
        self.filterCategory.addItem("")

    def taskDetail(self, item):
        """Вывод подробностей задачи в
        taskTitle, taskDescription, selectCategory
        при выделении задачи в tasksList и
        изменение поля done задачи в базе данных.
        """
        title = item.text()
        description = item.data(Qt.ItemDataRole.UserRole)
        self.taskTitle.setText(title)
        self.taskDescription.setText(description)
        cursor = self.con.cursor()
        cursor.execute("""
            SELECT categories.title 
            FROM tasks 
            JOIN categories ON tasks.category_id = categories.id 
            WHERE tasks.title = ?
        """, (title,))
        category = cursor.fetchone()
        if category:
            self.selectCategory.setCurrentText(category[0])
        done = item.checkState() == Qt.CheckState.Checked
        cursor.execute("UPDATE tasks SET done=? WHERE title=?", (done, title))
        self.con.commit()

    def addTask(self):
        """Добавление задачи в базу данных со значениями полей
        taskTitle, taskDescription, selectCategory.
        """
        title = self.taskTitle.text()
        description = self.taskDescription.toPlainText()
        category = self.selectCategory.currentText()
        cursor = self.con.cursor()
        cursor.execute("SELECT id FROM categories WHERE title=?", (category,))
        category_id = cursor.fetchone()
        if category_id:
            category_id = category_id[0]
            cursor.execute("INSERT INTO tasks (title, description, category_id) VALUES (?, ?, ?)",
                           (title, description, category_id))
            self.con.commit()
            self.loadTasks()

    def deleteTask(self):
        """Удаление задачи с подтверждением через QMessageBox."""
        item = self.tasksList.currentItem()
        if item:
            reply = QMessageBox.question(self, "Удалить задание", f"Вы точно хотите удалить '{item.text()}'?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                cursor = self.con.cursor()
                cursor.execute("DELETE FROM tasks WHERE title=?", (item.text(),))
                self.con.commit()
                self.loadTasks()

    def showCategories(self):
        """Открытие модального окна Categories."""
        self.categoriesWindow = Categories(self.con)
        self.categoriesWindow.exec()
        self.loadTasks()
        self.loadCategories()


if __name__ == '__main__':
    sys.excepthook = except_hook
    app = QApplication(sys.argv)
    window = Tasks()
    window.show()
    sys.exit(app.exec())
