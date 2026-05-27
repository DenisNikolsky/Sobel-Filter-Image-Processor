import os
import sqlite3
import datetime
from tkinter import *
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np


class SobelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Фильтр Собеля - обработка изображений (made by Viola)")
        self.root.geometry("600x400")

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.processed_dir = os.path.join(self.base_dir, "processed")
        # Гарантия создания папки processed
        os.makedirs(self.processed_dir, exist_ok=True)

        self.db_path = os.path.join(self.base_dir, "library.db")
        self.init_db()
        self.create_menu()

        info_label = Label(
            root,
            text="Используйте меню 'Файл' -> 'Добавить изображение',\n"
                 "чтобы применить фильтр Собеля и сохранить результат.\n"
                 "Меню 'Просмотр' -> 'Показать библиотеку' для просмотра истории.",
            font=("Arial", 12),
            justify=CENTER
        )
        info_label.pack(expand=True)

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT NOT NULL,
                processed_path TEXT NOT NULL,
                modification_time TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def create_menu(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Добавить изображение", command=self.add_image)

        view_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Просмотр", menu=view_menu)
        view_menu.add_command(label="Показать библиотеку", command=self.show_library)

    def add_image(self):
        file_path = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp *.tiff")]
        )
        if not file_path:
            return

        try:
            output_path = self.apply_sobel_filter(file_path)
            self.save_to_library(file_path, output_path)
            messagebox.showinfo("Успех", f"Изображение обработано и сохранено:\n{output_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось обработать изображение:\n{str(e)}")

    def apply_sobel_filter(self, input_path):
        # Чтение через imdecode для поддержки любых путей
        with open(input_path, 'rb') as f:
            img_data = f.read()
        img_array = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Не удалось прочитать файл. Возможно, он повреждён или не является изображением.")

        # Преобразование в оттенки серого
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Оператор Собеля
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
        magnitude = np.uint8(np.clip(magnitude, 0, 255))

        # Формирование имени выходного файла
        base_name = os.path.basename(input_path)
        name, ext = os.path.splitext(base_name)
        if not ext:
            ext = ".png"

        ext_lower = ext.lower()
        output_name = f"{name}_sobel{ext_lower}"
        output_path = os.path.join(self.processed_dir, output_name)
        counter = 1
        while os.path.exists(output_path):
            output_name = f"{name}_sobel_{counter}{ext_lower}"
            output_path = os.path.join(self.processed_dir, output_name)
            counter += 1

        encode_ext = ext_lower[1:]
        success, encoded_img = cv2.imencode('.' + encode_ext, magnitude)
        if not success:
            raise ValueError(f"Не удалось закодировать изображение в формат {encode_ext}")
        with open(output_path, 'wb') as f:
            f.write(encoded_img.tobytes())

        return output_path

    def save_to_library(self, original_path, processed_path):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO images (original_path, processed_path, modification_time) VALUES (?, ?, ?)",
            (original_path, processed_path, now)
        )
        conn.commit()
        conn.close()

    def show_library(self):
        lib_window = Toplevel(self.root)
        lib_window.title("Библиотека обработанных изображений")
        lib_window.geometry("800x400")

        frame = Frame(lib_window)
        frame.pack(fill=BOTH, expand=True)

        columns = ("ID", "Исходный путь", "Обработанный путь", "Дата изменения")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        tree.pack(side=LEFT, fill=BOTH, expand=True)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=180, anchor=W)

        scrollbar = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        tree.configure(yscrollcommand=scrollbar.set)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, original_path, processed_path, modification_time FROM images ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            tree.insert("", END, values=row)

        if not rows:
            label = Label(lib_window, text="Библиотека пуста. Добавьте изображения через меню.", fg="gray")
            label.pack(pady=20)

if __name__ == "__main__":
    root = Tk()
    app = SobelApp(root)
    root.mainloop()