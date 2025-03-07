import tkinter as tk
from tkinter import ttk

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("QuangStation V2 - Hệ thống Lập kế hoạch Xạ trị")
        self.create_widgets()

    def create_widgets(self):
        # Tạo frame chính
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Tạo tiêu đề
        title_label = ttk.Label(main_frame, text="QuangStation V2", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        # Tạo nút bắt đầu
        start_button = ttk.Button(main_frame, text="Bắt đầu", command=self.start_application)
        start_button.pack(pady=5)

        # Tạo nút thoát
        exit_button = ttk.Button(main_frame, text="Thoát", command=self.root.quit)
        exit_button.pack(pady=5)

    def start_application(self):
        # Hàm để bắt đầu ứng dụng
        print("Ứng dụng bắt đầu")

if __name__ == "__main__":
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
