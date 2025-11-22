import customtkinter as ctk
import os
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk 
from datetime import datetime
import calendar
from db_manager import get_db_connection, run_minutiae_extraction 
class CTkDatePicker(ctk.CTkFrame):
    def __init__(self, master, width=180, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.selected_date = None
        self.width = width
        self.calendar_window = None

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="x")

        self.entry = ctk.CTkEntry(
            container,
            width=self.width - 40,
            placeholder_text="YYYY-MM-DD"
        )
        self.entry.pack(side="left", fill="x", padx=(0, 5))

        self.btn = ctk.CTkButton(
            container,
            width=35,
            text="▼",
            command=self.open_calendar
        )
        self.btn.pack(side="left")

    def open_calendar(self):
        if self.calendar_window:
            return

        self.calendar_window = ctk.CTkToplevel(self)
        self.calendar_window.title("Pilih Tanggal")
        self.calendar_window.geometry("320x360")
        self.calendar_window.attributes("-topmost", True)
        self.calendar_window.resizable(False, False)

        today = datetime.today()
        self.current_year = today.year
        self.current_month = today.month

        self.build_calendar()

        self.calendar_window.protocol("WM_DELETE_WINDOW", self.close_calendar)

    def close_calendar(self):
        if self.calendar_window:
            self.calendar_window.destroy()
            self.calendar_window = None

    def build_calendar(self):
        # Clear window
        for widget in self.calendar_window.winfo_children():
            widget.destroy()

        # ===== HEADER FRAME =====
        header = ctk.CTkFrame(self.calendar_window)
        header.pack(fill="x", pady=5)

        # TOMBOL BULAN SEBELUMNYA
        ctk.CTkButton(header, text="<", width=40, command=self.prev_month)\
            .pack(side="left", padx=5)

        # ===== DROPDOWN BULAN =====
        months = list(calendar.month_name)[1:]  # January—December
        self.month_var = ctk.StringVar(
            value=calendar.month_name[self.current_month]
        )

        month_box = ctk.CTkOptionMenu(
            header,
            values=months,
            variable=self.month_var,
            command=self.change_month
        )
        month_box.pack(side="left", padx=5)

        # ===== DROPDOWN TAHUN =====
        years = [str(y) for y in range(1990, 2036)]
        self.year_var = ctk.StringVar(value=str(self.current_year))

        year_box = ctk.CTkOptionMenu(
            header,
            values=years,
            variable=self.year_var,
            command=self.change_year
        )
        year_box.pack(side="left", padx=5)

        # TOMBOL BULAN SELANJUTNYA
        ctk.CTkButton(header, text=">", width=40, command=self.next_month)\
            .pack(side="left", padx=5)

        # ===== KONTEN HARI =====
        days_frame = ctk.CTkFrame(self.calendar_window)
        days_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Hari Senin–Minggu
        days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for idx, d in enumerate(days):
            ctk.CTkLabel(days_frame, text=d).grid(row=0, column=idx, pady=2)

        # ===== GRID TANGGAL =====
        month_calendar = calendar.monthcalendar(self.current_year, self.current_month)

        for r, week in enumerate(month_calendar, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    ctk.CTkLabel(days_frame, text="").grid(
                        row=r, column=c, padx=2, pady=2
                    )
                else:
                    ctk.CTkButton(
                        days_frame,
                        text=str(day),
                        width=35,
                        command=lambda d=day: self.select_date(d)
                    ).grid(row=r, column=c, padx=2, pady=2)

    def change_month(self, selected):
        self.current_month = list(calendar.month_name).index(selected)
        self.build_calendar()

    def change_year(self, selected):
        self.current_year = int(selected)
        self.build_calendar()

    def select_date(self, day):
        date = datetime(self.current_year, self.current_month, day)
        formatted = date.strftime("%Y-%m-%d")
        self.entry.delete(0, "end")
        self.entry.insert(0, formatted)
        self.close_calendar()

    def prev_month(self):
        self.current_month -= 1
        if self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
        self.build_calendar()

    def next_month(self):
        self.current_month += 1
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        self.build_calendar()

    def get(self):
        return self.entry.get()
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
        
        # Nomor LP + Tanggal
        row2 = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        row2.grid(row=2, column=0, sticky="ew", pady=5)
        row2.grid_columnconfigure((0, 1), weight=1)

        lp_frame = ctk.CTkFrame(row2, fg_color="transparent")
        lp_frame.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        ctk.CTkLabel(lp_frame, text="Nomor LP:", font=self.controller.FONT_UTAMA, justify="left").pack(anchor="w",pady=(0, 0))
        self.entry_lp = ctk.CTkEntry(lp_frame, placeholder_text="Contoh: LP/123/IX/2023")
        self.entry_lp.pack(fill="x", pady=(5, 0))
        
        # ======== TANGGAL CUSTOM DATE PICKER ========
        tgl_frame = ctk.CTkFrame(row2, fg_color="transparent")
        tgl_frame.grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(tgl_frame, text="Tanggal Kejadian:", font=self.controller.FONT_UTAMA, justify="left").pack(anchor="w",pady=(0, 0))

        self.entry_tanggal = CTkDatePicker(tgl_frame, width=225)
        self.entry_tanggal.pack(fill="x", pady=(5, 0))
        # =============================================

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

        # ================== LOADING OVERLAY ==================

    def _init_loading_overlay(self):
        """Inisialisasi overlay loading (blur/dim + gif) sekali saja."""
        if hasattr(self, "loading_overlay") and self.loading_overlay is not None:
            return  # sudah pernah dibuat

        # Frame full-screen di atas halaman ini
        self.loading_overlay = ctk.CTkFrame(self, fg_color="black")  # gelap, efek "blur"
        # Belum di-place, nanti di _show_loading_overlay

        # Cari path loading.gif (di folder root/assets/loading.gif)
        base_dir = os.path.dirname(os.path.dirname(__file__))  # .../find_minutiae_apps_forzippedchatgpt
        gif_path = os.path.join(base_dir, "assets", "loading.gif")

        self.loading_frames = []
        self.loading_frame_index = 0
        self.loading_anim_after_id = None

        try:
            from PIL import ImageSequence

            gif = Image.open(gif_path)

            # Ambil semua frame gif dan convert ke PhotoImage
            for frame in ImageSequence.Iterator(gif):
                frame = frame.convert("RGBA")
                frame = frame.resize((128, 128), Image.LANCZOS)
                self.loading_frames.append(ImageTk.PhotoImage(frame))

        except Exception as e:
            print(f"WARNING: Gagal memuat atau memproses loading.gif: {e}")
            self.loading_frames = []

        # Label di tengah untuk menampilkan gif / teks
        self.loading_label = ctk.CTkLabel(
            self.loading_overlay,
            text="Memproses...",
            font=self.controller.FONT_UTAMA
        )
        self.loading_label.place(relx=0.5, rely=0.5, anchor="center")

        # Kalau ada frame gif, pakai frame pertama
        if self.loading_frames:
            self.loading_label.configure(image=self.loading_frames[0], text="")
            self.loading_label.image = self.loading_frames[0]

    def _animate_loading(self):
        """Animasi gif loading (dipanggil berulang via after)."""
        if (
            not hasattr(self, "loading_overlay")
            or self.loading_overlay is None
            or not self.loading_frames
        ):
            return

        self.loading_frame_index = (self.loading_frame_index + 1) % len(self.loading_frames)
        frame = self.loading_frames[self.loading_frame_index]
        self.loading_label.configure(image=frame, text="")
        self.loading_label.image = frame

        # Ulangi tiap 100 ms
        self.loading_anim_after_id = self.after(100, self._animate_loading)

    def _show_loading_overlay(self):
        """Tampilkan overlay loading di atas seluruh halaman."""
        self._init_loading_overlay()

        # Tempatkan overlay menutupi seluruh frame halaman
        self.loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.loading_overlay.lift()  # pastikan di paling atas

        # Mulai animasi kalau ada frame
        if self.loading_frames:
            # reset index
            self.loading_frame_index = 0
            self.loading_label.configure(image=self.loading_frames[0], text="")
            self.loading_label.image = self.loading_frames[0]
            if self.loading_anim_after_id is None:
                self.loading_anim_after_id = self.after(100, self._animate_loading)

        self.update_idletasks()

    def _hide_loading_overlay(self):
        """Sembunyikan overlay loading."""
        if hasattr(self, "loading_anim_after_id") and self.loading_anim_after_id is not None:
            try:
                self.after_cancel(self.loading_anim_after_id)
            except Exception:
                pass
            self.loading_anim_after_id = None

        if hasattr(self, "loading_overlay") and self.loading_overlay is not None:
            self.loading_overlay.place_forget()
            self.update_idletasks()

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