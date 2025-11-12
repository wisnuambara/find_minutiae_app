import customtkinter as ctk
from db_manager import fetch_history_counts

class HomePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="gray17")
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        self.create_header()
        self.create_dashboard()
    
    def create_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_frame, text="Dashboard Utama", font=self.controller.FONT_JUDUL).grid(row=0, column=0, sticky="w")
        
        # Tombol Logout di Pojok Kanan Atas
        logout_button = ctk.CTkButton(header_frame, text="Logout", command=self.controller.logout, fg_color="#cc3300", hover_color="#992600", font=self.controller.FONT_UTAMA)
        logout_button.grid(row=0, column=1, sticky="e", padx=10)

    def create_dashboard(self):
        dashboard_frame = ctk.CTkFrame(self, fg_color="transparent")
        dashboard_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        dashboard_frame.grid_columnconfigure((0, 1), weight=1)
        
        # CARD: Jumlah Pencarian Umum
        self.card_umum = ctk.CTkFrame(dashboard_frame, fg_color="gray15", corner_radius=10)
        self.card_umum.grid(row=0, column=0, padx=(0, 10), pady=10, sticky="ew")
        self.umum_label = ctk.CTkLabel(self.card_umum, text="0", font=ctk.CTkFont(family="Arial", size=40, weight="bold"), text_color="#1f6aa5")
        self.umum_label.pack(pady=(20, 0), padx=20)
        ctk.CTkLabel(self.card_umum, text="Jumlah Pencarian Umum", font=self.controller.FONT_UTAMA).pack(pady=(0, 20), padx=20)

        # CARD: Jumlah Pencarian Lokal
        self.card_lokal = ctk.CTkFrame(dashboard_frame, fg_color="gray15", corner_radius=10)
        self.card_lokal.grid(row=0, column=1, padx=(10, 0), pady=10, sticky="ew")
        self.lokal_label = ctk.CTkLabel(self.card_lokal, text="0", font=ctk.CTkFont(family="Arial", size=40, weight="bold"), text_color="#1f6aa5")
        self.lokal_label.pack(pady=(20, 0), padx=20)
        ctk.CTkLabel(self.card_lokal, text="Jumlah Pencarian Lokal", font=self.controller.FONT_UTAMA).pack(pady=(0, 20), padx=20)

        ctk.CTkLabel(self, text="Selamat Datang di Aplikasi Find Minutiae", font=self.controller.FONT_SUBJUDUL).grid(row=2, column=0, sticky="n", pady=50)

    def refresh_data(self):
        """Ambil data dari DB dan update label dashboard."""
        umum, lokal = fetch_history_counts()
        self.umum_label.configure(text=str(umum))
        self.lokal_label.configure(text=str(lokal))