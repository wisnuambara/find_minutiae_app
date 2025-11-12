import customtkinter as ctk
import os
from tkinter import messagebox
from PIL import Image
from db_manager import get_history_data, fetch_history_by_id, update_history_data, delete_history

# --- HALAMAN 4A: RIWAYAT PENCARIAN (Tabel Daftar) ---
class RiwayatPencarianPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="gray17")
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Row 0: Judul, Row 1: Filter, Row 2: Tabel
        
        # Frame Judul dan Filter
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(header_frame, text="Riwayat Pencarian Kasus", font=controller.FONT_JUDUL).grid(row=0, column=0, sticky="w")
        
        # Kontrol Filter (Riwayat Umum vs Lokal)
        control_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        control_frame.grid(row=0, column=1, sticky="e")
        
        ctk.CTkLabel(control_frame, text="Tampilkan:", font=controller.FONT_UTAMA).pack(side="left", padx=5)
        self.riwayat_mode = ctk.StringVar(value="Umum") # State mode riwayat default Umum
        
        ctk.CTkSegmentedButton(control_frame, 
                                variable=self.riwayat_mode,
                                values=["Umum", "Lokal"],
                                command=self.refresh_data, # Memanggil refresh_data setiap kali ganti mode
                                font=controller.FONT_UTAMA).pack(side="left")
        
        
        self.table_frame = ctk.CTkScrollableFrame(self, fg_color="gray15", label_text="Daftar Kasus Tersimpan", label_font=controller.FONT_SUBJUDUL, label_text_color="#1f6aa5")
        self.table_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.table_frame.grid_columnconfigure(0, weight=1) 
        
        self.data_rows = []
        self._setup_table_headers()
        # Data akan di-load saat show_frame dipanggil (refresh_data)

    def _setup_table_headers(self):
        # Header Table
        header_frame = ctk.CTkFrame(self.table_frame, fg_color="gray20")
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
        
        headers = ["ID", "Judul Kasus", "Nomor LP", "Tanggal", "Tipe", "Aksi"]
        for i, text in enumerate(headers):
            ctk.CTkLabel(header_frame, text=text, font=self.controller.FONT_SUBJUDUL, padx=5, pady=10).grid(row=0, column=i, sticky="ew")

    def refresh_data(self, *args):
        # Hapus baris data lama
        for row in self.data_rows:
            row.destroy()
        self.data_rows = []

        is_local = self.riwayat_mode.get() == "Lokal"
        user_id = self.controller.logged_in_user_id
        
        # Fetch data berdasarkan mode yang dipilih
        data = get_history_data(user_id=user_id)
        
        for i, row_data in enumerate(data):
            # row_id, judul, nomor_lp, tanggal, tipe (dari DB)
            row_id, judul, nomor_lp, tanggal, timestamp, username = row_data
            
            row_frame = ctk.CTkFrame(self.table_frame, fg_color="gray17" if i % 2 == 0 else "gray15")
            row_frame.grid(row=i + 1, column=0, sticky="ew", pady=(1, 0))
            row_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
            self.data_rows.append(row_frame)
            
            # Kolom Data
            ctk.CTkLabel(row_frame, text=row_id, font=self.controller.FONT_UTAMA).grid(row=0, column=0, padx=5, pady=5)
            ctk.CTkLabel(row_frame, text=judul, font=self.controller.FONT_UTAMA).grid(row=0, column=1, padx=5, pady=5, sticky="w")
            ctk.CTkLabel(row_frame, text=nomor_lp if nomor_lp else "-", font=self.controller.FONT_UTAMA).grid(row=0, column=2, padx=5, pady=5)
            ctk.CTkLabel(row_frame, text=tanggal if tanggal else "-", font=self.controller.FONT_UTAMA).grid(row=0, column=3, padx=5, pady=5)
            ctk.CTkLabel(row_frame, text=username, font=self.controller.FONT_UTAMA).grid(row=0, column=4, padx=5, pady=5)
            
            # Kolom Aksi
            action_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            action_frame.grid(row=0, column=5, padx=5, pady=5)
            
            # Menggunakan lambda untuk menunda eksekusi show_detail dengan ID yang benar
            detail_btn = ctk.CTkButton(action_frame, text="Detail", width=60, height=25, command=lambda rid=row_id: self.show_detail(rid))
            detail_btn.pack(side="left", padx=2)

    def show_detail(self, row_id):
        self.controller.show_frame("DetailPage", data={'id': row_id})


# --- HALAMAN 4B: DETAIL RIWAYAT ---
class DetailPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="gray17")
        self.controller = controller
        self.record_id = None
        self.record_paths = {} # Menyimpan path mentah dan ekstraksi

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self._setup_ui()
    
    def _setup_ui(self):
        # Header (Judul dan Tombol Aksi)
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header_frame.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(header_frame, text="Detail Kasus:", font=self.controller.FONT_JUDUL)
        self.title_label.grid(row=0, column=0, sticky="w")
        
        action_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        action_frame.grid(row=0, column=1, sticky="e")
        
        self.btn_edit = ctk.CTkButton(action_frame, text="Edit Data", command=self.go_to_edit, fg_color="gray40", hover_color="gray25", width=80)
        self.btn_edit.pack(side="left", padx=5)
        self.btn_delete = ctk.CTkButton(action_frame, text="Hapus", command=self.delete_record, fg_color="#cc3300", hover_color="#992600", width=80)
        self.btn_delete.pack(side="left", padx=5)
        self.btn_back = ctk.CTkButton(action_frame, text="Kembali", command=lambda: self.controller.show_frame("RiwayatPencarian"), width=80)
        self.btn_back.pack(side="left", padx=5)


        # Konten Utama
        self.content_frame = ctk.CTkFrame(self, fg_color="gray15")
        self.content_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.content_frame.grid_columnconfigure((0, 1), weight=1)
        
        self._setup_info_panel(self.content_frame, 0)
        self._setup_image_panel(self.content_frame, 1)

    def _setup_info_panel(self, parent, col):
        info_panel = ctk.CTkFrame(parent, fg_color="transparent")
        info_panel.grid(row=0, column=col, sticky="nwe", padx=30, pady=20)
        
        # Data Kasus
        ctk.CTkLabel(info_panel, text="Data Kasus:", font=self.controller.FONT_SUBJUDUL, text_color="#1f6aa5").pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(info_panel, text="ID Kasus:", font=self.controller.FONT_UTAMA, anchor="w").pack(fill="x", pady=(5, 0))
        self.lbl_id = ctk.CTkLabel(info_panel, text="", font=self.controller.FONT_UTAMA, anchor="w")
        self.lbl_id.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(info_panel, text="Judul Kasus:", font=self.controller.FONT_UTAMA, anchor="w").pack(fill="x", pady=(5, 0))
        self.lbl_judul = ctk.CTkLabel(info_panel, text="", font=ctk.CTkFont(family="Arial", size=14, weight="bold"), anchor="w", wraplength=400)
        self.lbl_judul.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(info_panel, text="Nomor LP:", font=self.controller.FONT_UTAMA, anchor="w").pack(fill="x", pady=(5, 0))
        self.lbl_lp = ctk.CTkLabel(info_panel, text="", font=self.controller.FONT_UTAMA, anchor="w")
        self.lbl_lp.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(info_panel, text="Tanggal Kejadian:", font=self.controller.FONT_UTAMA, anchor="w").pack(fill="x", pady=(5, 0))
        self.lbl_tanggal = ctk.CTkLabel(info_panel, text="", font=self.controller.FONT_UTAMA, anchor="w")
        self.lbl_tanggal.pack(fill="x", pady=(0, 20))
        
        # Path File
        ctk.CTkLabel(info_panel, text="Path File Mentah:", font=self.controller.FONT_UTAMA, anchor="w").pack(fill="x", pady=(5, 0))
        self.lbl_path_mentah = ctk.CTkLabel(info_panel, text="", font=self.controller.FONT_UTAMA, anchor="w", wraplength=400, text_color="gray")
        self.lbl_path_mentah.pack(fill="x", pady=(0, 10))

    def _setup_image_panel(self, parent, col):
        image_panel = ctk.CTkFrame(parent, fg_color="transparent")
        image_panel.grid(row=0, column=col, sticky="nsew", padx=30, pady=20)
        image_panel.grid_rowconfigure(2, weight=1)
        image_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(image_panel, text="Visualisasi:", font=self.controller.FONT_SUBJUDUL, text_color="#1f6aa5").grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # Image Type Selector
        type_frame = ctk.CTkFrame(image_panel, fg_color="transparent")
        type_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.image_type_var = ctk.StringVar(value="Mentah")
        self.radio_mentah = ctk.CTkRadioButton(type_frame, text="Mentah", variable=self.image_type_var, value="Mentah", command=self.display_image, font=self.controller.FONT_UTAMA)
        self.radio_mentah.pack(side="left", padx=10)
        self.radio_ekstraksi = ctk.CTkRadioButton(type_frame, text="Ekstraksi", variable=self.image_type_var, value="Ekstraksi", command=self.display_image, font=self.controller.FONT_UTAMA)
        self.radio_ekstraksi.pack(side="left", padx=10)

        # Image Holder
        self.image_holder = ctk.CTkLabel(image_panel, text="[Gambar]", corner_radius=10, fg_color="gray25")
        self.image_holder.grid(row=2, column=0, sticky="nsew")

    def load_data(self, data_dict):
        # Fungsi ini dipanggil oleh controller untuk memuat data spesifik
        self.record_id = data_dict['id']
        record = fetch_history_by_id(self.record_id)
        
        if record:
            self.title_label.configure(text=f"Detail Kasus ID: {self.record_id}")
            self.lbl_id.configure(text=self.record_id)
            self.lbl_judul.configure(text=record['judul_kasus'])
            self.lbl_lp.configure(text=record['nomor_lp'] if record['nomor_lp'] else "-")
            self.lbl_tanggal.configure(text=record['tanggal_kejadian'] if record['tanggal_kejadian'] else "-")
            self.lbl_path_mentah.configure(text=record['path_mentah'])
            
            self.record_paths = {
                "Mentah": record['path_mentah'],
                "Ekstraksi": record['path_ekstraksi']
            }
            # Tampilkan gambar awal (Mentah)
            self.image_type_var.set("Mentah")
            self.display_image()
        else:
             messagebox.showerror("Error", "Data kasus tidak ditemukan.")
             self.controller.show_frame("RiwayatPencarian")


    def display_image(self):
        img_type = self.image_type_var.get()
        img_path = self.record_paths.get(img_type)

        if not img_path or not os.path.exists(img_path):
            self.image_holder.configure(text=f"File {img_type} tidak ditemukan!", image=None)
            return

        try:
            original_image = Image.open(img_path)
            # Resize gambar agar sesuai
            original_image.thumbnail((450, 450))
            
            ctk_image = ctk.CTkImage(light_image=original_image, dark_image=original_image, size=original_image.size)
            
            self.image_holder.configure(text="", image=ctk_image)
            self.image_holder.image = ctk_image
        except Exception as e:
            self.image_holder.configure(text=f"Gagal memuat gambar: {e}", image=None)

    def go_to_edit(self):
        if self.record_id:
            self.controller.show_frame("EditPage", data={'id': self.record_id})

    def delete_record(self):
        if not self.record_id:
            return

        confirm = messagebox.askyesno(
            "Konfirmasi Hapus", 
            f"Anda yakin ingin menghapus Kasus ID {self.record_id}? Tindakan ini tidak dapat dibatalkan!"
        )

        if confirm:
            path_mentah = self.record_paths.get("Mentah")
            path_ekstraksi = self.record_paths.get("Ekstraksi")
            
            if delete_history_data(self.record_id, path_mentah, path_ekstraksi):
                messagebox.showinfo("Sukses", "Data dan file kasus berhasil dihapus.")
                self.controller.show_frame("RiwayatPencarian")
            else:
                messagebox.showerror("Error", "Gagal menghapus data.")

# --- HALAMAN 4C: EDIT RIWAYAT ---
class EditPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="gray17")
        self.controller = controller
        self.record_id = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self, text="Edit Data Kasus", font=controller.FONT_JUDUL).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.edit_card = ctk.CTkFrame(self, fg_color="gray15", corner_radius=10)
        self.edit_card.grid(row=1, column=0, padx=20, pady=10, sticky="nwe")
        self.edit_card.grid_columnconfigure(0, weight=1)
        
        self._setup_edit_form()

    def _setup_edit_form(self):
        controller = self.controller
        
        # ID Kasus
        ctk.CTkLabel(self.edit_card, text="ID Kasus:", font=controller.FONT_UTAMA, anchor="w").grid(row=0, column=0, padx=30, pady=(20, 0), sticky="ew")
        self.lbl_id = ctk.CTkLabel(self.edit_card, text="", font=controller.FONT_SUBJUDUL, anchor="w")
        self.lbl_id.grid(row=1, column=0, padx=30, pady=(5, 10), sticky="ew")

        # Judul Kasus
        ctk.CTkLabel(self.edit_card, text="Judul Kasus:", font=controller.FONT_UTAMA, anchor="w").grid(row=2, column=0, padx=30, pady=(20, 0), sticky="ew")
        self.entry_judul = ctk.CTkEntry(self.edit_card, font=controller.FONT_UTAMA)
        self.entry_judul.grid(row=3, column=0, padx=30, pady=(5, 10), sticky="ew")
        
        # Nomor LP
        ctk.CTkLabel(self.edit_card, text="Nomor LP:", font=controller.FONT_UTAMA, anchor="w").grid(row=4, column=0, padx=30, pady=(10, 0), sticky="ew")
        self.entry_lp = ctk.CTkEntry(self.edit_card, font=controller.FONT_UTAMA)
        self.entry_lp.grid(row=5, column=0, padx=30, pady=(5, 10), sticky="ew")
        
        # Tanggal Kejadian
        ctk.CTkLabel(self.edit_card, text="Tanggal Kejadian:", font=controller.FONT_UTAMA, anchor="w").grid(row=6, column=0, padx=30, pady=(10, 0), sticky="ew")
        self.entry_tanggal = ctk.CTkEntry(self.edit_card, font=controller.FONT_UTAMA)
        self.entry_tanggal.grid(row=7, column=0, padx=30, pady=(5, 20), sticky="ew")
        
        # Tombol Aksi
        action_frame = ctk.CTkFrame(self.edit_card, fg_color="transparent")
        action_frame.grid(row=8, column=0, padx=30, pady=30, sticky="e")
        
        btn_simpan = ctk.CTkButton(action_frame, text="Simpan Perubahan", command=self.save_changes, height=40, fg_color="#1f6aa5", hover_color="#18537a")
        btn_simpan.pack(side="left", padx=10)
        
        btn_batal = ctk.CTkButton(action_frame, text="Batal", command=lambda: self.controller.show_frame("DetailPage", data={'id': self.record_id}), height=40, fg_color="gray40", hover_color="gray25")
        btn_batal.pack(side="left")


    def load_data(self, data_dict):
        # Fungsi ini dipanggil oleh controller untuk memuat data spesifik ke form edit
        self.record_id = data_dict['id']
        record = fetch_history_by_id(self.record_id)
        
        if record:
            self.lbl_id.configure(text=str(self.record_id))
            
            # Isi form dengan data yang ada
            self.entry_judul.delete(0, ctk.END)
            self.entry_judul.insert(0, record['judul_kasus'])
            
            self.entry_lp.delete(0, ctk.END)
            self.entry_lp.insert(0, record['nomor_lp'] if record['nomor_lp'] else "")
            
            self.entry_tanggal.delete(0, ctk.END)
            self.entry_tanggal.insert(0, record['tanggal_kejadian'] if record['tanggal_kejadian'] else "")
        else:
             messagebox.showerror("Error", "Data kasus tidak ditemukan.")
             self.controller.show_frame("RiwayatPencarian")

    def save_changes(self):
        judul = self.entry_judul.get()
        nomor_lp = self.entry_lp.get()
        tanggal = self.entry_tanggal.get()

        if not judul:
            messagebox.showerror("Validasi", "Judul Kasus tidak boleh kosong!")
            return

        try:
            update_history_data(self.record_id, judul, nomor_lp, tanggal)
            messagebox.showinfo("Sukses", "Data kasus berhasil diperbarui.")
            # Kembali ke halaman detail setelah menyimpan
            self.controller.show_frame("DetailPage", data={'id': self.record_id}) 
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan perubahan: {e}")