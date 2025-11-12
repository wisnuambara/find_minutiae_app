import customtkinter as ctk
import os
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk 
from db_manager import get_db_connection, run_minutiae_extraction 

# --- FUNGSI HELPER DISPLAY GAMBAR ---
def _display_image(label_widget, path, max_size=(250, 180)):
    """Helper function untuk memuat dan menampilkan gambar di CTkLabel"""
    try:
        original_image = Image.open(path)
        original_image.thumbnail(max_size)
        
        # CTkImage dari PIL Image
        ctk_image = ctk.CTkImage(light_image=original_image, dark_image=original_image, size=original_image.size)
        
        label_widget.configure(text="", image=ctk_image)
        # Penting: Simpan referensi objek gambar agar tidak hilang (Garbage Collection)
        label_widget.image = ctk_image
    except Exception as e:
        label_widget.configure(text=f"Gagal memuat gambar:\n{os.path.basename(path)}", image=None)
        print(f"Error display image: {e}")

# =========================================================================
# --- HALAMAN 3A: CARI MINUTIAE (FORM) ---
# =========================================================================
class CariMinutiaePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="gray17")
        self.controller = controller
        self.filepath = None # Menyimpan path gambar yang diupload
        
        # --- Konfigurasi Grid Utama untuk Sidebar dan Main Content ---
        self.grid_columnconfigure(0, weight=0) # Sidebar column
        self.grid_columnconfigure(1, weight=1) # Main Content column
        self.grid_rowconfigure(0, weight=1) 
        
        self._setup_main_content()
        
    def _setup_main_content(self):
        # Frame Konten Utama (Kanan)
        self.content_frame = ctk.CTkFrame(self, fg_color="gray17")
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)

        # PERBAIKAN FONT 2/13
        ctk.CTkLabel(self.content_frame, text="Cari Minutiae Sidik Jari", font=self.controller.FONT_JUDUL).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        self.form_card = ctk.CTkFrame(self.content_frame, fg_color="gray15", corner_radius=10)
        self.form_card.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        # Grid Form Card: Kolom 0 (Input) dan Kolom 1 (Gambar)
        self.form_card.grid_columnconfigure(0, weight=1) 
        self.form_card.grid_columnconfigure(1, weight=1) 
        self.form_card.grid_rowconfigure(0, weight=1) 

        self._setup_form_input()
        self._setup_form_display()

    def _setup_form_input(self):
        # Frame untuk Input (Kolom Kiri dari Card)
        self.input_frame = ctk.CTkScrollableFrame(self.form_card, fg_color="transparent")
        self.input_frame.grid(row=0, column=0, padx=30, pady=20, sticky="nsew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        # Judul Kasus
        # PERBAIKAN FONT 3/13
        ctk.CTkLabel(self.input_frame, text="Judul Kasus:", font=self.controller.FONT_UTAMA, anchor="w").grid(row=0, column=0, pady=(10, 0), sticky="ew")
        self.entry_judul = ctk.CTkEntry(self.input_frame, placeholder_text="Contoh: Kasus Perampokan ATM 2023", font=self.controller.FONT_UTAMA)
        self.entry_judul.grid(row=1, column=0, pady=(5, 10), sticky="ew")
        
        # Nomor LP dan Tanggal Kejadian (Side by Side)
        form_row2 = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        form_row2.grid(row=2, column=0, pady=5, sticky="ew")
        form_row2.grid_columnconfigure((0, 1), weight=1)
        
        lp_frame = ctk.CTkFrame(form_row2, fg_color="transparent")
        lp_frame.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        # PERBAIKAN FONT 4/13
        ctk.CTkLabel(lp_frame, text="Nomor LP:", font=self.controller.FONT_UTAMA, anchor="w").pack(fill="x")
        self.entry_lp = ctk.CTkEntry(lp_frame, placeholder_text="Contoh: LP/123/IX/2023", font=self.controller.FONT_UTAMA)
        self.entry_lp.pack(fill="x", pady=(5, 0))
        
        tgl_frame = ctk.CTkFrame(form_row2, fg_color="transparent")
        tgl_frame.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        # PERBAIKAN FONT 5/13
        ctk.CTkLabel(tgl_frame, text="Tanggal Kejadian:", font=self.controller.FONT_UTAMA, anchor="w").pack(fill="x")
        self.entry_tanggal = ctk.CTkEntry(tgl_frame, placeholder_text="Contoh: YYYY-MM-DD", font=self.controller.FONT_UTAMA)
        self.entry_tanggal.pack(fill="x", pady=(5, 0))

        # Upload Sidik Jari
        # PERBAIKAN FONT 6/13
        ctk.CTkLabel(self.input_frame, text="Upload Sidik Jari (SJ Mentah):", font=self.controller.FONT_UTAMA, anchor="w").grid(row=3, column=0, pady=(10, 0), sticky="ew")
        upload_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        upload_frame.grid(row=4, column=0, pady=(5, 20), sticky="ew")
        upload_frame.grid_columnconfigure(0, weight=1)

        # PERBAIKAN FONT 7/13
        self.upload_label = ctk.CTkLabel(upload_frame, text="Belum ada file dipilih...", anchor="w", font=self.controller.FONT_UTAMA)
        self.upload_label.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        # PERBAIKAN FONT 8/13
        upload_button = ctk.CTkButton(upload_frame, text="Pilih File", command=self.upload_file, width=100, font=self.controller.FONT_UTAMA)
        upload_button.grid(row=0, column=1, sticky="e")
        
        # Tombol Lanjut
        # PERBAIKAN FONT 9/13
        lanjut_button = ctk.CTkButton(self.input_frame, text="LANJUT & PROSES", command=self.process_and_save, height=40, font=self.controller.FONT_SUBJUDUL, fg_color="#1f6aa5", hover_color="#18537a")
        lanjut_button.grid(row=5, column=0, pady=30, sticky="s")


    def _setup_form_display(self):
        # Frame Tampilan Gambar (Kolom Kanan dari Card)
        self.display_frame = ctk.CTkFrame(self.form_card, fg_color="gray15")
        self.display_frame.grid(row=0, column=1, padx=30, pady=20, sticky="nsew")
        self.display_frame.grid_columnconfigure(0, weight=1)
        self.display_frame.grid_rowconfigure(4, weight=1)

        # Tampilan Gambar Mentah
        # PERBAIKAN FONT 10/13
        ctk.CTkLabel(self.display_frame, text="Gambar Sidik Jari Mentah:", font=self.controller.FONT_UTAMA, anchor="w").grid(row=0, column=0, pady=(0, 5), sticky="w")
        self.raw_image_holder = ctk.CTkLabel(self.display_frame, text="[Gambar Mentah]", corner_radius=10, fg_color="gray25", width=250, height=180)
        self.raw_image_holder.grid(row=1, column=0, sticky="nwe", pady=(0, 20))

        # Tampilan Hasil Ekstraksi Minutiae
        # PERBAIKAN FONT 11/13
        ctk.CTkLabel(self.display_frame, text="Hasil Ekstraksi Minutiae Sidik Jari:", font=self.controller.FONT_UTAMA, anchor="w").grid(row=2, column=0, pady=(0, 5), sticky="w")
        self.extracted_image_holder = ctk.CTkLabel(self.display_frame, text="[Hasil Ekstraksi]", corner_radius=10, fg_color="gray25", width=250, height=180)
        self.extracted_image_holder.grid(row=3, column=0, sticky="nwe")


    def upload_file(self):
        self.filepath = filedialog.askopenfilename(
            title="Pilih Gambar Sidik Jari",
            filetypes=(("Image files", "*.bmp *.jpg *.jpeg *.png"), ("All files", "*.*"))
        )
        if self.filepath:
            self.upload_label.configure(text=os.path.basename(self.filepath), text_color="green")
            
            # **Tampilkan Gambar Mentah**
            _display_image(self.raw_image_holder, self.filepath)
            
            # Kosongkan hasil ekstraksi sebelumnya
            self.extracted_image_holder.configure(text="[Hasil Ekstraksi]", image=None)

        else:
            self.upload_label.configure(text="Belum ada file dipilih...", text_color="white")
            self.raw_image_holder.configure(text="[Gambar Mentah]", image=None)


    def process_and_save(self):
        judul = self.entry_judul.get()
        nomor_lp = self.entry_lp.get()
        tanggal = self.entry_tanggal.get()
        
        if not judul or not self.filepath:
            messagebox.showerror("Validasi", "Judul Kasus dan File Sidik Jari harus diisi!")
            return
        
        self.upload_label.configure(text="Memproses...", text_color="orange")
        self.update_idletasks()

        # 1. Jalankan Model Ekstraksi & Simpan File ke Disk
        try:
            path_mentah, path_ekstraksi = run_minutiae_extraction(self.filepath, judul)
        except Exception as e:
            messagebox.showerror("Error Ekstraksi", f"Gagal Ekstraksi! Cek konsol. Error: {e}")
            self.upload_label.configure(text="Ekstraksi Gagal!", text_color="red")
            return

        if path_mentah and path_ekstraksi:
            # **Tampilkan Gambar Hasil Ekstraksi**
            _display_image(self.extracted_image_holder, path_ekstraksi)
            
            # 2. Simpan Data Kasus ke Database
            user_id = self.controller.logged_in_user_id if hasattr(self.controller, 'logged_in_user_id') else 1 
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO history (judul_kasus, nomor_lp, tanggal_kejadian, path_mentah, path_ekstraksi, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (judul, nomor_lp, tanggal, path_mentah, path_ekstraksi, user_id)) 
            
            last_id = cursor.lastrowid
            conn.commit()
            conn.close()

            messagebox.showinfo("Sukses", "Ekstraksi Minutiae berhasil dan data telah disimpan!")
            self.upload_label.configure(text=os.path.basename(self.filepath), text_color="green")
            
            # 3. Pindah ke Halaman Hasil Ekstraksi
            data = {
                'id': last_id,
                'judul': judul, 
                'nomor_lp': nomor_lp, 
                'tanggal': tanggal, 
                'path_ekstraksi': path_ekstraksi
            }
            
            # Bersihkan form
            self.entry_judul.delete(0, ctk.END)
            self.entry_lp.delete(0, ctk.END)
            self.entry_tanggal.delete(0, ctk.END)
            self.filepath = None
            
            self.controller.show_frame("HasilEkstraksiPage", data=data) 
        else:
            messagebox.showerror("Error", "Gagal menyimpan file hasil ekstraksi.")
            self.upload_label.configure(text="Ekstraksi Gagal!", text_color="red")


# =========================================================================
# --- HALAMAN 3B: HASIL EKSTRAKSI ---
# =========================================================================
class HasilEkstraksiPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="gray17")
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # PERBAIKAN FONT 12/13
        ctk.CTkLabel(self, text="Hasil Ekstraksi Minutiae", font=self.controller.FONT_JUDUL).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        self.result_card = ctk.CTkFrame(self, fg_color="gray15", corner_radius=10)
        self.result_card.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.result_card.grid_columnconfigure(0, weight=1)
        self.result_card.grid_columnconfigure(1, weight=1)

        self._setup_result_display()

    def _setup_result_display(self):
        # Frame Informasi Kasus (Kiri)
        info_frame = ctk.CTkFrame(self.result_card, fg_color="transparent")
        info_frame.grid(row=0, column=0, padx=30, pady=20, sticky="nwe")

        # PERBAIKAN FONT 13/13 (Di sini dan semua label di bawahnya)
        ctk.CTkLabel(info_frame, text="Informasi Kasus:", font=self.controller.FONT_SUBJUDUL, text_color="#1f6aa5").pack(fill="x", pady=(0, 10))

        # Judul Kasus
        ctk.CTkLabel(info_frame, text="Judul Kasus:", font=self.controller.FONT_UTAMA, anchor="w").pack(fill="x", pady=(5, 0))
        self.label_judul = ctk.CTkLabel(info_frame, text="", font=ctk.CTkFont(family="Arial", size=14, weight="bold"), anchor="w")
        self.label_judul.pack(fill="x", pady=(0, 10))
        
        # Nomor LP
        ctk.CTkLabel(info_frame, text="Nomor LP:", font=self.controller.FONT_UTAMA, anchor="w").pack(fill="x", pady=(5, 0))
        self.label_lp = ctk.CTkLabel(info_frame, text="", font=self.controller.FONT_UTAMA, anchor="w")
        self.label_lp.pack(fill="x", pady=(0, 10))
        
        # Tanggal Kejadian
        ctk.CTkLabel(info_frame, text="Tanggal Kejadian:", font=self.controller.FONT_UTAMA, anchor="w").pack(fill="x", pady=(5, 0))
        self.label_tanggal = ctk.CTkLabel(info_frame, text="", font=self.controller.FONT_UTAMA, anchor="w")
        self.label_tanggal.pack(fill="x", pady=(0, 20))
        
        # Frame Hasil Gambar (Kanan)
        image_frame = ctk.CTkFrame(self.result_card, fg_color="transparent")
        image_frame.grid(row=0, column=1, padx=30, pady=20, sticky="nsew")
        image_frame.grid_rowconfigure(1, weight=1)
        image_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(image_frame, text="Hasil Ekstraksi Minutiae:", font=self.controller.FONT_SUBJUDUL, text_color="#1f6aa5").grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # Image Holder
        self.image_holder = ctk.CTkLabel(image_frame, text="[Gambar Hasil Ekstraksi]", corner_radius=10, fg_color="gray25")
        self.image_holder.grid(row=1, column=0, sticky="nsew")

    def load_data(self, data):
        # Dipanggil oleh controller saat pindah halaman
        self.label_judul.configure(text=data['judul'])
        self.label_lp.configure(text=data['nomor_lp'] if data['nomor_lp'] else "-")
        self.label_tanggal.configure(text=data['tanggal'] if data['tanggal'] else "-")
        
        # Tampilkan Gambar
        try:
            img_path = data['path_ekstraksi']
            original_image = Image.open(img_path)
            # Resize gambar agar sesuai (maks 400x400)
            original_image.thumbnail((400, 400))
            
            ctk_image = ctk.CTkImage(light_image=original_image, dark_image=original_image, size=original_image.size)
            
            self.image_holder.configure(text="", image=ctk_image)
            self.image_holder.image = ctk_image # Agar gambar tidak hilang
        except Exception as e:
            self.image_holder.configure(text=f"Gagal memuat gambar:\n{e}", image=None)