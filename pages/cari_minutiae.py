import threading
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
        self.entry.bind("<Key>", lambda e: "break")
        self.entry.pack(side="left", fill="x", padx=(0, 5))

        self.btn = ctk.CTkButton(
            container,
            width=35,
            text="▼",
            command=self.open_calendar
        )
        self.btn.pack(side="left")
        
    def reset_state(self):
        """Bersihkan semua state pencarian saat user logout / mulai baru."""
        self.filepath = None

        # status
        if hasattr(self, "label_status"):
            self.label_status.configure(text="", text_color="white")

        # preview gambar mentah
        if hasattr(self, "label_mentah"):
            self.label_mentah.configure(text="Belum ada gambar", image=None)
            self.label_mentah.image = None  # penting: buang referensi CTkImage

        # preview gambar ekstraksi
        if hasattr(self, "label_ekstraksi"):
            self.label_ekstraksi.configure(text="Belum ada hasil ekstraksi", image=None)
            self.label_ekstraksi.image = None

        # kalau ada entry judul / nomor LP / tanggal, bersihkan juga
        if hasattr(self, "entry_judul"):
            self.entry_judul.delete(0, "end")
        if hasattr(self, "entry_nomor_lp"):
            self.entry_nomor_lp.delete(0, "end")
        if hasattr(self, "entry_tanggal"):
            self.entry_tanggal.delete(0, "end")

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
    def clear(self):
        """Kosongkan tanggal yang dipilih"""
        self.entry.delete(0, "end")
        self.selected_date = None
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



def _prepare_image_for_model(path, target_max_side=384):
    """
    Menyiapkan gambar khusus untuk input model FingerFlow:
    - Membuka gambar asli
    - Mengecilkan sehingga sisi terpanjang <= target_max_side (dengan menjaga aspek rasio)
    - Menyimpan sebagai file JPEG baru dengan suffix "_model.jpg" di folder images_for_models
    - Mengembalikan path file baru tersebut
    """
    try:
        img = Image.open(path).convert("RGB")
    except Exception as e:
        print("Prepare image: gagal membuka:", e)
        return path

    w, h = img.size
    max_dim = max(w, h)
    if max_dim > target_max_side:
        scale = target_max_side / float(max_dim)
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.LANCZOS)

    # Tentukan root project = folder di atas "pages"
    # __file__ = .../minutiae_ekstraksi/pages/cari_minutiae.py
    # os.path.dirname(__file__)            -> .../minutiae_ekstraksi/pages
    # os.path.dirname(os.path.dirname())   -> .../minutiae_ekstraksi  (root project)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Pastikan folder images_for_models ada di root project
    images_dir = os.path.join(project_root, "images_for_models")
    os.makedirs(images_dir, exist_ok=True)

    # Nama file dasar diambil dari nama file asli
    base = os.path.splitext(os.path.basename(path))[0]
    out_path = os.path.join(images_dir, f"{base}_model.jpg")

    try:
        img.save(out_path, format="JPEG", quality=80, optimize=True)
    except Exception:
        img.save(out_path, format="JPEG", quality=80)

    try:
        size_bytes = os.path.getsize(out_path)
    except Exception:
        size_bytes = None

    print(f"[MODEL PREP] path={out_path}, size={size_bytes}, dims={img.size}")
    return out_path


# =========================================================================
# --- HALAMAN 3A: CARI MINUTIAE (FORM) ---
# =========================================================================
class CariMinutiaePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
                # state overlay loading
        self.loading_overlay = None
        self.loading_frames = []
        self.loading_frame_index = 0
        self.loading_anim_after_id = None
        self.loading_image_label = None
        self.loading_text_label = None

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
        lanjut_button = ctk.CTkButton(self.input_frame, text="Ekstrak Minutiae", command=self.process_and_save, height=40, font=self.controller.FONT_SUBJUDUL, fg_color="#0d8427", hover_color="#18537a")
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
        """Inisialisasi overlay loading (GIF + teks) sekali saja."""
        if self.loading_overlay is not None:
            return  # sudah dibuat

        # Parent = App utama, supaya nutup sidebar juga
        parent = self.controller

        # Frame full-window hitam transparan
        self.loading_overlay = ctk.CTkFrame(parent, fg_color="gray15")

        # --- load GIF ---
        base_dir = os.path.dirname(os.path.dirname(__file__))  # root project
        gif_path = os.path.join(base_dir, "assets", "loading.gif")

        self.loading_frames = []
        self.loading_frame_index = 0
        self.loading_anim_after_id = None

        try:
            from PIL import ImageSequence

            gif = Image.open(gif_path)

            for frame in ImageSequence.Iterator(gif):
                frame = frame.convert("RGBA")
                frame = frame.resize((128, 128), Image.LANCZOS)
                self.loading_frames.append(ImageTk.PhotoImage(frame))

        except Exception as e:
            print(f"WARNING: Gagal memuat loading.gif: {e}")
            self.loading_frames = []

        # --- kontainer tengah ---
        center = ctk.CTkFrame(self.loading_overlay, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        # label GIF
        self.loading_image_label = ctk.CTkLabel(center, text="")
        self.loading_image_label.pack(pady=(0, 10))

        # label teks status
        self.loading_text_label = ctk.CTkLabel(
            center,
            text="Sedang memproses...",
            font=self.controller.FONT_UTAMA
        )
        self.loading_text_label.pack()

        # set frame awal kalau ada
        if self.loading_frames:
            self.loading_image_label.configure(image=self.loading_frames[0])
            self.loading_image_label.image = self.loading_frames[0]



    def _animate_loading(self):
        """Animasi GIF loading."""
        if not self.loading_frames or self.loading_overlay is None:
            return

        self.loading_frame_index = (self.loading_frame_index + 1) % len(self.loading_frames)
        frame = self.loading_frames[self.loading_frame_index]

        # update gambar
        self.loading_image_label.configure(image=frame)
        self.loading_image_label.image = frame

        # jadwalkan frame berikut
        self.loading_anim_after_id = self.after(20, self._animate_loading)

    def _show_loading_overlay(self):
        """Tampilkan overlay loading di atas seluruh aplikasi."""
        self._init_loading_overlay()

        # tutup full window
        self.loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.loading_overlay.lift()

        # reset teks default
        if self.loading_text_label is not None:
            self.loading_text_label.configure(text="Sedang memproses...")

        # mulai animasi
        if self.loading_frames:
            self.loading_frame_index = 0
            frame = self.loading_frames[0]
            self.loading_image_label.configure(image=frame)
            self.loading_image_label.image = frame

            # pastikan tidak ada animasi lama
            if self.loading_anim_after_id is not None:
                try:
                    self.after_cancel(self.loading_anim_after_id)
                except Exception:
                    pass
            self.loading_anim_after_id = self.after(100, self._animate_loading)

        self.update_idletasks()

  

    def _hide_loading_overlay(self):
        """Sembunyikan overlay dan hentikan animasi."""
        # stop animasi
        if self.loading_anim_after_id is not None:
            try:
                self.after_cancel(self.loading_anim_after_id)
            except Exception:
                pass
            self.loading_anim_after_id = None

        if self.loading_overlay is not None:
            self.loading_overlay.place_forget()

        self.update_idletasks()

    def _set_loading_text(self, text: str):
        """Update teks di bawah GIF loading."""
        if self.loading_text_label is not None:
            self.loading_text_label.configure(text=text)
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
        
        # Update status & tampilkan overlay loading
        self.upload_label.configure(text="Memproses...", text_color="orange")
        self._show_loading_overlay()
        self.update_idletasks()

        # ---- KERJA BERAT DIPINDAH KE THREAD TERPISAH ----
        def worker():
            error = None
            result = None

            try:
                # --- 1. PREPROSES GAMBAR UNTUK MODEL FINGERFLOW ---
                # Update status: menyiapkan gambar
                self.after(0, lambda: self._set_loading_text(
                    "Sedang memproses: menyiapkan gambar untuk model..."
                ))

                try:
                    model_input_path = _prepare_image_for_model(self.filepath, target_max_side=512)
                except Exception as e:
                    print("Gagal menyiapkan gambar untuk model, gunakan gambar asli:", e)
                    model_input_path = self.filepath

                # --- 2. SIAPKAN CALLBACK UNTUK PROGRESS DARI FINGERFLOW ---
                def progress_to_ui(msg: str):
                    # dipanggil di thread worker → lempar ke main thread
                    def _update():
                        short = msg.replace("\n", " ").strip()
                        if len(short) > 30:
                            short = short[:30] + "..."
                        self._set_loading_text(f"Sedang memproses: {short}")
                    self.after(0, _update)

                # --- 3. JALANKAN EKSTRAKSI MINUTIAE (FINGERFLOW) ---
                # (run_minutiae_extraction di db_manager.py sudah dimodif dengan progress_callback)
                try:
                    path_mentah, path_ekstraksi = run_minutiae_extraction(
                        model_input_path,
                        judul,
                        progress_callback=progress_to_ui
                    )
                except Exception as e:
                    error = ("Error Ekstraksi", f"Gagal Ekstraksi! Cek konsol. Error: {e}")
                    path_mentah, path_ekstraksi = None, None

                # --- 4. SIMPAN KE DATABASE JIKA BERHASIL ---
                if not error and path_mentah and path_ekstraksi:
                    # update status: simpan ke DB
                    self.after(0, lambda: self._set_loading_text(
                        "Sedang memproses: menyimpan hasil ke database..."
                    ))

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

                    # Data untuk halaman hasil
                    result = {
                        "success": True,
                        "last_id": last_id,
                        "judul": judul,
                        "nomor_lp": nomor_lp,
                        "tanggal": tanggal,
                        "path_mentah": path_mentah,
                        "path_ekstraksi": path_ekstraksi,
                    }

                elif not error:
                    # path_mentah atau path_ekstraksi kosong tapi nggak ada exception
                    error = ("Error", "Gagal menyimpan file hasil ekstraksi.")

            except Exception as e:
                # fallback error tak terduga
                error = ("Error Tak Terduga", str(e))

            # --- 5. BALIK KE MAIN THREAD UNTUK UPDATE UI & PINDAH HALAMAN ---
            self.after(0, lambda: self._on_process_finished(result, error))


        # Start thread worker (daemon supaya ikut mati kalau app ditutup)
        threading.Thread(target=worker, daemon=True).start()

    def _on_process_finished(self, result, error):
        """Dipanggil di MAIN THREAD setelah thread worker selesai."""

        # 1) Kalau ada error → langsung hide overlay & tampilkan pesan
        if error is not None:
            try:
                self._hide_loading_overlay()
            except Exception as e:
                print("WARNING: gagal menyembunyikan overlay loading:", e)

            title, msg = error
            from tkinter import messagebox
            messagebox.showerror(title, msg)
            self.upload_label.configure(text="Ekstraksi Gagal!", text_color="red")
            return

        # 2) Kalau result tidak valid
        if result is None or not result.get("success"):
            try:
                self._hide_loading_overlay()
            except Exception as e:
                print("WARNING: gagal menyembunyikan overlay loading:", e)

            from tkinter import messagebox
            messagebox.showerror("Error", "Terjadi kesalahan, data tidak lengkap.")
            self.upload_label.configure(text="Ekstraksi Gagal!", text_color="red")
            return

        # 3) Kasus sukses → tampilkan dulu teks selesai
        try:
            self._set_loading_text("Selesai: memuat tampilan hasil...")
        except Exception:
            pass

        # Bungkus sisa logic di fungsi kecil supaya bisa di-delay
        def finalize():
            # Sembunyikan overlay
            try:
                self._hide_loading_overlay()
            except Exception as e:
                print("WARNING: gagal menyembunyikan overlay loading:", e)

            # Ambil data dari result
            path_ekstraksi = result["path_ekstraksi"]
            path_mentah = result["path_mentah"]
            last_id = result["last_id"]
            judul = result["judul"]
            nomor_lp = result["nomor_lp"]
            tanggal = result["tanggal"]

            # 1. Tampilkan gambar hasil ekstraksi di panel kanan
            _display_image(self.extracted_image_holder, path_ekstraksi)

            # 2. Update label upload (file yang dipilih)
            if self.filepath:
                import os
                self.upload_label.configure(
                    text=os.path.basename(self.filepath),
                    text_color="green"
                )

            # 3. Siapkan data untuk halaman hasil
            data = {
                'id': last_id,
                'judul': judul,
                'nomor_lp': nomor_lp,
                'tanggal': tanggal,
                'path_ekstraksi': path_ekstraksi
            }

            # 4. Bersihkan form input
            self.entry_judul.delete(0, ctk.END)
            self.entry_lp.delete(0, ctk.END)
            self.entry_tanggal.clear()
            self.filepath = None

            # 5. Pindah ke halaman hasil
            self.controller.show_frame("HasilEkstraksiPage", data=data)

        # 4) Delay sedikit supaya tulisan "Selesai: ..." sempat kelihatan
        self.after(1000, finalize)   # 700 ms, bisa diatur 500–1000 ms sesuai selera





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