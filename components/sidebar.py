import customtkinter as ctk

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, controller):
        # Frame Sidebar diletakkan di sisi kiri
        super().__init__(parent, width=180, corner_radius=0, fg_color="gray17")
        self.controller = controller
        self.grid_rowconfigure(6, weight=1) # Agar tombol logout bisa diletakkan di bawah
        
        # Judul Aplikasi
        ctk.CTkLabel(self, text="Find Minutiae", font=controller.FONT_JUDUL, text_color="#1f6aa5").grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nw")
        ctk.CTkFrame(self, height=1, fg_color="gray30").grid(row=1, column=0, padx=10, pady=(0, 20), sticky="ew")

        # Menu Navigasi
        self.menus = {
            # Key adalah nama yang ditampilkan, Value adalah objek tombol
            "Home": ctk.CTkButton(self, text="Home", command=lambda: self.controller.show_frame("Home"), corner_radius=0, fg_color="transparent", hover_color="gray25", anchor="w", font=controller.FONT_UTAMA),
            "Cari Minutiae": ctk.CTkButton(self, text="Cari Minutiae", command=lambda: self.controller.show_frame("CariMinutiae"), corner_radius=0, fg_color="transparent", hover_color="gray25", anchor="w", font=controller.FONT_UTAMA),
            "Riwayat Pencarian": ctk.CTkButton(self, text="Riwayat Pencarian", command=lambda: self.controller.show_frame("RiwayatPencarian"), corner_radius=0, fg_color="transparent", hover_color="gray25", anchor="w", font=controller.FONT_UTAMA),
        }
        
        row_counter = 2
        for text, button in self.menus.items():
            button.grid(row=row_counter, column=0, sticky="ew", pady=1)
            row_counter += 1

    def set_active(self, menu_name):
        """Menandai tombol menu mana yang sedang aktif."""
        # Reset semua tombol (transparan)
        for button in self.menus.values():
            button.configure(fg_color="transparent")
        
        # Atur tombol yang aktif (berwarna biru)
        if menu_name in self.menus:
            self.menus[menu_name].configure(fg_color="#1f6aa5")