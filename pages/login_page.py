import customtkinter as ctk
from tkinter import messagebox
from db_manager import check_user_credentials

class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent,fg_color="gray10")
        self.controller = controller
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # CARD LOGIN
        card_login = ctk.CTkFrame(self, width=400, height=450, corner_radius=15, fg_color="gray15")
        card_login.grid(row=0, column=0, padx=20, pady=20)
        card_login.grid_columnconfigure(0, weight=1)
        
        # Judul
        ctk.CTkLabel(card_login, text="Sistem Ekstraksi Minutiae", font=controller.FONT_JUDUL, text_color="#1f6aa5").pack(pady=(40, 5))
        ctk.CTkLabel(card_login, text="Find Minutiae", font=controller.FONT_SUBJUDUL).pack(pady=(0, 30))

        # Username
        ctk.CTkLabel(card_login, text="Username:", font=controller.FONT_UTAMA, anchor="w").pack(fill="x", padx=40, pady=(10, 0))
        self.username_entry = ctk.CTkEntry(card_login, width=300, corner_radius=8, placeholder_text="Masukkan username", font=controller.FONT_UTAMA)
        self.username_entry.pack(padx=40)

        # Password
        ctk.CTkLabel(card_login, text="Password:", font=controller.FONT_UTAMA, anchor="w").pack(fill="x", padx=40, pady=(10, 0))
        self.password_entry = ctk.CTkEntry(card_login, width=300, corner_radius=8, show="*", placeholder_text="Masukkan password", font=controller.FONT_UTAMA)
        self.password_entry.pack(padx=40)

        # Tombol Login
        login_button = ctk.CTkButton(card_login, text="Login", command=self.attempt_login, width=300, height=40, corner_radius=8, font=controller.FONT_UTAMA, fg_color="#1f6aa5", hover_color="#18537a")
        login_button.pack(pady=(40, 20), padx=40)

       #TOMBOL DAFTAR DIKOMENTRKAN, TIDAK DIPAKAI LAGI, jika ingin mengaktifkan kembali, hapus tanda pagar (#) di awal baris berikut
       
        # daftar_button = ctk.CTkButton(card_login, text="DAFTAR AKUN", command=lambda: controller.show_frame("Register"), width=300, height=40, corner_radius=8, font=controller.FONT_UTAMA, fg_color="#3a3f47", hover_color="#4a4f57")
        # daftar_button.pack(pady=(0, 20), padx=40)

        self.login_message = ctk.CTkLabel(card_login, text="", text_color="red")
        self.login_message.pack(pady=(0, 20))

    def attempt_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        # check_user_credentials kini mengembalikan INTEGER (user_id) atau None
        # Jadi, variabel 'user' SUDAH berisi ID user jika login sukses.
        user_id = check_user_credentials(username, password) # <-- Variabel diganti namanya dari 'user' menjadi 'user_id' untuk kejelasan.

        if user_id:
            # user_id sudah berupa integer, TIDAK PERLU lagi user[0]
            self.login_message.configure(text="")
            
            # Panggil fungsi login_success di controller untuk menyimpan ID user dan pindah halaman
            self.controller.login_success(user_id) # Pastikan controller Anda memiliki method login_success()
            
            # Bersihkan entry setelah login
            self.username_entry.delete(0, ctk.END)
            self.password_entry.delete(0, ctk.END)
        else:
            self.login_message.configure(text="Username atau Password salah!")