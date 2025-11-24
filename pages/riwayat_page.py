import customtkinter as ctk
import os
from tkinter import messagebox
from PIL import Image
from db_manager import get_history_data, fetch_history_by_id, update_history_data, delete_history

# ---------------------------
# Helper: potong teks dengan ellipsis
# ---------------------------

def _load_icon( filename, size=(18, 18)):
    """
    Load icon from folder icons/.
    Return None if not found (button still works).
    """
    try:
        path = os.path.join("icons", filename)
        if os.path.exists(path):
            pil = Image.open(path)
            return ctk.CTkImage(light_image=pil, dark_image=pil, size=size)
    except Exception:
        pass
    return None

icons = {
            "detail": _load_icon("eye.png"),
            "edit": _load_icon("edit.png"),
            "hapus": _load_icon("tongsampah.png"),
            "kembali": _load_icon("kembali.png"),
            "tambah": _load_icon("tambah.png"),
            "perbesar": _load_icon("perbesar.png")
        }

def cut_text(text, limit):
    if text is None:
        return "-"
    text = str(text)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."

# ===========================
# HALAMAN 4A: RIWAYAT PENCARIAN
# ===========================
class RiwayatPencarianPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="gray17")
        self.controller = controller

        # Pagination & state
        self.page = 1
        self.page_size = 15
        self.total_items = 0

        # Fixed column widths
        self.COL_WIDTH = {
            "id": 70,
            "judul": 340,
            "lp": 140,
            "tanggal": 140,
            "tipe": 120,
            "aksi": 90,
            "minutiae_count": 120,
        }

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._setup_header()
        self._setup_table_frame()
        self._setup_pagination_controls()

        self.data_rows = []

    # ---------- HEADER ----------
    def _setup_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_frame, text="Riwayat Pencarian Kasus", font=self.controller.FONT_JUDUL).grid(
            row=0, column=0, sticky="w"
        )

        control_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        control_frame.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(control_frame, text="Tampilkan:", font=self.controller.FONT_UTAMA).pack(side="left", padx=(0, 6))

        self.riwayat_mode = ctk.StringVar(value="Umum")
        ctk.CTkSegmentedButton(
            control_frame,
            variable=self.riwayat_mode,
            values=["Umum", "Lokal"],
            command=self._on_mode_change,
            font=self.controller.FONT_UTAMA
        ).pack(side="left")

    def _on_mode_change(self, *args):
        self.page = 1
        self.refresh_data()

    # ---------- TABLE ----------
    def _setup_table_frame(self):
        self.table_outer = ctk.CTkFrame(self, fg_color="gray15")
        self.table_outer.grid(row=1, column=0, sticky="nsew", padx=12, pady=(6, 6))
        self.table_outer.grid_columnconfigure(0, weight=1)
        self.table_outer.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.table_outer, fg_color="gray20", height=36)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        titles = [("No", self.COL_WIDTH["id"]),
                  ("Judul Kasus", self.COL_WIDTH["judul"]),
                  ("Nomor LP", self.COL_WIDTH["lp"]),
                  ("Tanggal", self.COL_WIDTH["tanggal"]),
                  ("Tipe", self.COL_WIDTH["tipe"]),
                  ("Aksi", self.COL_WIDTH["aksi"])]

        for idx, (txt, w) in enumerate(titles):
            lbl = ctk.CTkLabel(header, text=txt, font=self.controller.FONT_SUBJUDUL, anchor="center")
            lbl.grid(row=0, column=idx, padx=4, pady=6, sticky="nsew")
            lbl.configure(width=w)

        self.scroll_area = ctk.CTkScrollableFrame(
            self.table_outer, fg_color="gray15", label_text="", corner_radius=6, height=500
        )
        self.scroll_area.grid(row=1, column=0, sticky="nsew", pady=(6, 6))
        self.scroll_area.grid_columnconfigure(0, weight=1)

        self.rows_container = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        self.rows_container.grid(row=0, column=0, sticky="nsew")
        self.rows_container.grid_columnconfigure(0, weight=1)

    # ---------- PAGINATION ----------
    def _setup_pagination_controls(self):
        pag_frame = ctk.CTkFrame(self, fg_color="transparent")
        pag_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        pag_frame.grid_columnconfigure(1, weight=1)

        self.btn_prev = ctk.CTkButton(pag_frame, text="◀ Sebelumnya", width=90, command=self.prev_page)
        self.btn_prev.grid(row=0, column=0, padx=(0, 8))

        self.page_label = ctk.CTkLabel(pag_frame, text=f"Halaman {self.page}", font=self.controller.FONT_UTAMA)
        self.page_label.grid(row=0, column=1)

        self.btn_next = ctk.CTkButton(pag_frame, text="Selanjutnya ▶", width=90, command=self.next_page)
        self.btn_next.grid(row=0, column=2, padx=(8, 0))

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.refresh_data()

    def next_page(self):
        if self.page * self.page_size < self.total_items:
            self.page += 1
            self.refresh_data()

    # ---------- ROW RENDER ----------
    def _clear_rows(self):
        for r in self.data_rows:
            try:
                r.destroy()
            except:
                pass
        self.data_rows = []

    def refresh_data(self, *args):
        self._clear_rows()

        try:
            mode = (self.riwayat_mode.get() or "Umum").lower()
            if mode == 'lokal' and getattr(self.controller, 'logged_in_user_id', None) is not None:
                raw = get_history_data(user_id=self.controller.logged_in_user_id)
            else:
                raw = get_history_data(user_id=None)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal mengambil data riwayat: {e}")
            raw = []

        self.total_items = len(raw)
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        page_data = raw[start:end]

        self.page_label.configure(text=f"Halaman {self.page}, Total Keseluruhan Data: {self.total_items} Data")
        self.btn_prev.configure(state="normal" if self.page > 1 else "disabled")
        self.btn_next.configure(state="normal" if self.page * self.page_size < self.total_items else "disabled")

        for i, row in enumerate(page_data):
            try:
                row_id, judul, nomor_lp, tanggal, timestamp, minutiae_count, username = row
            except Exception:
                row_id = row[0] if len(row) > 0 else ""
                judul = row[1] if len(row) > 1 else ""
                nomor_lp = row[2] if len(row) > 2 else ""
                tanggal = row[3] if len(row) > 3 else ""
                minutiae_count = row[5] if len(row) > 4 else ""
                username = row[6] if len(row) > 5 else ""
                

            bg_color = "gray18" if (i % 2 == 0) else "gray17"
            row_frame = ctk.CTkFrame(self.rows_container, fg_color=bg_color, height=42, corner_radius=4)
            row_frame.grid(row=i, column=0, sticky="ew", padx=(4, 4), pady=(2, 2))
            row_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

            underline = ctk.CTkFrame(row_frame, fg_color="gray12", height=1)
            underline.grid(row=1, column=0, columnspan=6, sticky="ew", pady=(0, 0))

            def on_enter(e, f=row_frame):
                f.configure(fg_color="gray25")

            def on_leave(e, f=row_frame, orig=bg_color):
                f.configure(fg_color=orig)

            row_frame.bind("<Enter>", on_enter)
            row_frame.bind("<Leave>", on_leave)

            nomor_urut = start + i + 1
            lbl_id = ctk.CTkLabel(row_frame, text=str(nomor_urut), font=self.controller.FONT_UTAMA)
            lbl_id.grid(row=0, column=0, sticky="w", padx=(8, 4))
            lbl_id.configure(width=self.COL_WIDTH["id"])

            cut_judul = cut_text(judul or "-", 60)
            lbl_judul = ctk.CTkLabel(
                row_frame,
                text=cut_judul,
                font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
                anchor="w"
            )
            lbl_judul.grid(row=0, column=1, sticky="w", padx=(6, 4))
            lbl_judul.configure(width=self.COL_WIDTH["judul"], wraplength=self.COL_WIDTH["judul"])

            lbl_lp = ctk.CTkLabel(row_frame, text=cut_text(nomor_lp or "-", 24), font=self.controller.FONT_UTAMA)
            lbl_lp.grid(row=0, column=2, sticky="w", padx=4)
            lbl_lp.configure(width=self.COL_WIDTH["lp"])

            lbl_tanggal = ctk.CTkLabel(row_frame, text=cut_text(tanggal or "-", 20), font=self.controller.FONT_UTAMA)
            lbl_tanggal.grid(row=0, column=3, sticky="w", padx=4)
            lbl_tanggal.configure(width=self.COL_WIDTH["tanggal"])

            lbl_tipe = ctk.CTkLabel(row_frame, text=cut_text(username or "-", 18), font=self.controller.FONT_UTAMA)
            lbl_tipe.grid(row=0, column=4, sticky="w", padx=4)
            lbl_tipe.configure(width=self.COL_WIDTH["tipe"])
            
            lbl_minutiae_count = ctk.CTkLabel(row_frame, text=cut_text(username or "-", 18), font=self.controller.FONT_UTAMA)
            lbl_minutiae_count.grid(row=0, column=4, sticky="w", padx=4)
            lbl_minutiae_count.configure(width=self.COL_WIDTH["minutiae_count"])

            action_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            action_frame.grid(row=0, column=5, sticky="w", padx=(4, 8))


            btn_detail = ctk.CTkButton(
                action_frame,
                text="Detail",
                width=36,
                height=28,
                image=icons.get("detail"),
                fg_color="#1f6aa5",
                hover_color="#18537a",
                command=lambda rid=row_id: self.show_detail(rid)
            )
            btn_detail.pack(side="right")

            self.data_rows.append(row_frame)

    def show_detail(self, row_id):
        self.controller.show_frame("DetailPage", data={'id': row_id})


# ===========================
# HALAMAN 4B: DETAIL RIWAYAT
# ===========================
class DetailPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="gray17")
        self.controller = controller
        self.record_id = None
        self.record_paths = {}

        # fullscreen overlay state
        self.fullscreen_overlay = None
        self._fs_raw_ctk_image = None
        self._fs_ext_ctk_image = None
        self._fs_raw_pil = None
        self._fs_ext_pil = None
        self._fs_box_w = None
        self._fs_box_h = None
        self._fs_zoom_var = None
        self._fs_left_toggle_var = None
        self._fs_right_toggle_var = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._setup_ui()

    def _setup_ui(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(header_frame, text="Detail Kasus:", font=self.controller.FONT_JUDUL)
        self.title_label.grid(row=0, column=0, sticky="w")

        action_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        action_frame.grid(row=0, column=1, sticky="e")

        self.btn_edit = ctk.CTkButton(
            action_frame,
            text="Edit Data",
            image=icons.get("edit"),
            command=self.go_to_edit,
            width=80
        )
        self.btn_edit.pack(side="left", padx=5)

        self.btn_delete = ctk.CTkButton(
            action_frame,
            text="Hapus",
            image=icons.get("hapus"),
            command=self.delete_record,
            fg_color="#cc3300",
            hover_color="#992600",
            width=80
        )
        self.btn_delete.pack(side="left", padx=5)

        self.btn_back = ctk.CTkButton(
            action_frame,
            image=icons.get("kembali"),
            text="Kembali",
            command=lambda: self.controller.show_frame("RiwayatPencarian"),
            width=80
        )
        self.btn_back.pack(side="left", padx=5)

        self.content_frame = ctk.CTkFrame(self, fg_color="gray15")
        self.content_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.content_frame.grid_columnconfigure((0, 1), weight=1)

        self._setup_info_panel(self.content_frame, 0)
        self._setup_image_panel(self.content_frame, 1)

    def _setup_info_panel(self, parent, col):
        info_panel = ctk.CTkFrame(parent, fg_color="transparent")
        info_panel.grid(row=0, column=col, sticky="nwe", padx=30, pady=20)

        ctk.CTkLabel(
            info_panel, text="Data Kasus:", font=self.controller.FONT_SUBJUDUL, text_color="#1f6aa5"
        ).pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(info_panel, text="ID Kasus:", font=self.controller.FONT_UTAMA, anchor="w").pack(
            fill="x", pady=(5, 0)
        )
        self.lbl_id = ctk.CTkLabel(info_panel, text="", font=self.controller.FONT_UTAMA, anchor="w")
        self.lbl_id.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(info_panel, text="Judul Kasus:", font=self.controller.FONT_UTAMA, anchor="w").pack(
            fill="x", pady=(5, 0)
        )
        self.lbl_judul = ctk.CTkLabel(
            info_panel,
            text="",
            font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
            anchor="w",
            wraplength=400
        )
        self.lbl_judul.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(info_panel, text="Nomor LP:", font=self.controller.FONT_UTAMA, anchor="w").pack(
            fill="x", pady=(5, 0)
        )
        self.lbl_lp = ctk.CTkLabel(info_panel, text="", font=self.controller.FONT_UTAMA, anchor="w")
        self.lbl_lp.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(info_panel, text="Tanggal Kejadian:", font=self.controller.FONT_UTAMA, anchor="w").pack(
            fill="x", pady=(5, 0)
        )
        self.lbl_tanggal = ctk.CTkLabel(info_panel, text="", font=self.controller.FONT_UTAMA, anchor="w")
        self.lbl_tanggal.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(info_panel, text="Minutiae Ditemukan:", font=self.controller.FONT_UTAMA, anchor="w").pack(
            fill="x", pady=(5, 0)
        )
        self.lbl_minutiae_count = ctk.CTkLabel(info_panel, text="", font=self.controller.FONT_UTAMA, anchor="w")
        self.lbl_minutiae_count.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(info_panel, text="Path File Mentah:", font=self.controller.FONT_UTAMA, anchor="w").pack(
            fill="x", pady=(5, 0)
        )
        self.lbl_path_mentah = ctk.CTkLabel(
            info_panel,
            text="",
            font=self.controller.FONT_UTAMA,
            anchor="w",
            wraplength=400,
            text_color="gray"
        )
        self.lbl_path_mentah.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(info_panel, text="Path File Ekstraksi:", font=self.controller.FONT_UTAMA, anchor="w").pack(
            fill="x", pady=(5, 0)
        )
        self.lbl_path_ekstraksi = ctk.CTkLabel(
            info_panel,
            text="",
            font=self.controller.FONT_UTAMA,
            anchor="w",
            wraplength=400,
            text_color="gray"
        )
        self.lbl_path_ekstraksi.pack(fill="x", pady=(0, 10))

    def _setup_image_panel(self, parent, col):
        image_panel = ctk.CTkFrame(parent, fg_color="transparent")
        image_panel.grid(row=0, column=col, sticky="nsew", padx=30, pady=20)
        image_panel.grid_rowconfigure(2, weight=1)
        image_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            image_panel,
            text="Visualisasi:",
            font=self.controller.FONT_SUBJUDUL,
            text_color="#1f6aa5"
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        type_frame = ctk.CTkFrame(image_panel, fg_color="transparent")
        type_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.image_type_var = ctk.StringVar(value="Mentah")
        self.radio_mentah = ctk.CTkRadioButton(
            type_frame,
            text="Mentah",
            variable=self.image_type_var,
            value="Mentah",
            command=self.display_image,
            font=self.controller.FONT_UTAMA
        )
        self.radio_mentah.pack(side="left", padx=10)
        self.radio_ekstraksi = ctk.CTkRadioButton(
            type_frame,
            text="Ekstraksi",
            variable=self.image_type_var,
            value="Ekstraksi",
            command=self.display_image,
            font=self.controller.FONT_UTAMA
        )
        self.radio_ekstraksi.pack(side="left", padx=10)

        self.image_holder = ctk.CTkLabel(image_panel, text="[Gambar]", corner_radius=10, fg_color="gray25")
        self.image_holder.grid(row=2, column=0, sticky="nsew")

        self.btn_perbesar = ctk.CTkButton(
            image_panel,
            text="Perbesar",
            image=icons.get("perbesar"),
            font=self.controller.FONT_UTAMA,
            command=self.show_fullscreen_comparison
        )
        self.btn_perbesar.grid(row=3, column=0, pady=(10, 0), sticky="e")

    # ---------- LOAD DATA ----------
    def load_data(self, data_dict):
        self.record_id = data_dict['id']
        record = fetch_history_by_id(self.record_id)

        if record:
            self.title_label.configure(text=f"Detail Kasus ID: {self.record_id}")
            self.lbl_id.configure(text=self.record_id)
            self.lbl_judul.configure(text=record['judul_kasus'])
            self.lbl_lp.configure(text=record['nomor_lp'] if record['nomor_lp'] else "-")
            self.lbl_tanggal.configure(text=record['tanggal_kejadian'] if record['tanggal_kejadian'] else "-")
            self.lbl_minutiae_count.configure(text=str(record['minutiae_count'] if record['minutiae_count'] is not None else "-"))
            self.lbl_path_mentah.configure(text=record['path_mentah'])
            self.lbl_path_ekstraksi.configure(text=record['path_ekstraksi'])

            self.record_paths = {
                "Mentah": record['path_mentah'],
                "Ekstraksi": record['path_ekstraksi']
            }
            self.image_type_var.set("Mentah")
            self.display_image()
        else:
            messagebox.showerror("Error", "Data kasus tidak ditemukan.")
            self.controller.show_frame("RiwayatPencarian")

    # ---------- THUMBNAIL ----------
    def _make_ctk_image_scaled(self, pil_img, max_w, max_h):
        img = pil_img.copy()
        ow, oh = img.size
        if ow == 0 or oh == 0:
            return None

        scale = min(max_w / ow, max_h / oh, 1.0)
        new_size = (int(ow * scale), int(oh * scale))
        if new_size[0] <= 0 or new_size[1] <= 0:
            new_size = (ow, oh)

        img = img.resize(new_size, Image.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=new_size)

    def display_image(self):
        img_type = self.image_type_var.get()
        img_path = self.record_paths.get(img_type)

        if not img_path or not os.path.exists(img_path):
            self.image_holder.configure(text=f"File {img_type} tidak ditemukan!", image=None)
            self.image_holder.image = None
            return

        try:
            original_image = Image.open(img_path)
            ctk_image = self._make_ctk_image_scaled(original_image, 450, 450)
            if ctk_image is None:
                self.image_holder.configure(text="Gagal memuat gambar.", image=None)
                self.image_holder.image = None
                return

            self.image_holder.configure(text="", image=ctk_image)
            self.image_holder.image = ctk_image
        except Exception as e:
            self.image_holder.configure(text=f"Gagal memuat gambar: {e}", image=None)
            self.image_holder.image = None

    # ---------- FULLSCREEN & ZOOM ----------
    def _make_ctk_image_boxed(self, pil_img, box_w, box_h, zoom_factor=1.0):
        """
        Resize proporsional lalu tempel ke kanvas hitam box_w x box_h.
        zoom_factor > 1.0 = zoom in, < 1.0 = zoom out.
        """
        img = pil_img.convert("RGB")
        ow, oh = img.size
        if ow == 0 or oh == 0:
            return None

        base_scale = min(box_w / ow, box_h / oh)
        scale = max(base_scale * zoom_factor, 0.1)

        new_w, new_h = int(ow * scale), int(oh * scale)
        if new_w <= 0 or new_h <= 0:
            new_w, new_h = ow, oh

        img_resized = img.resize((new_w, new_h), Image.LANCZOS)

        canvas = Image.new("RGB", (box_w, box_h), "black")
        offset_x = (box_w - new_w) // 2
        offset_y = (box_h - new_h) // 2
        canvas.paste(img_resized, (offset_x, offset_y))

        return ctk.CTkImage(light_image=canvas, dark_image=canvas, size=(box_w, box_h))

    def _init_fullscreen_overlay(self):
        if self.fullscreen_overlay is not None:
            return

        parent = self.controller

        self.fullscreen_overlay = ctk.CTkFrame(parent, fg_color="black")
        self.fullscreen_overlay.grid_rowconfigure(1, weight=1)
        self.fullscreen_overlay.grid_columnconfigure(0, weight=1)
        self.fullscreen_overlay.grid_columnconfigure(1, weight=1)

        # HEADER
        header = ctk.CTkFrame(self.fullscreen_overlay, fg_color="black")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 0))
        header.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            header,
            text="Perbandingan Sidik Jari",
            font=self.controller.FONT_SUBJUDUL,
            text_color="white"
        )
        title_label.grid(row=0, column=0, sticky="w")

        close_btn = ctk.CTkButton(
            header,
            text="Tutup",
            width=80,
            command=self.hide_fullscreen_overlay
        )
        close_btn.grid(row=0, column=1, sticky="e")

        # PANEL KIRI
        left_container = ctk.CTkFrame(self.fullscreen_overlay, fg_color="black")
        left_container.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=(10, 0))
        left_container.grid_rowconfigure(1, weight=1)
        left_container.grid_columnconfigure(0, weight=1)

        left_title_frame = ctk.CTkFrame(left_container, fg_color="black")
        left_title_frame.grid(row=0, column=0, pady=(0, 10), sticky="w")
        left_title_frame.grid_columnconfigure(0, weight=0)
        left_title_frame.grid_columnconfigure(1, weight=0)

        self.fs_raw_title = ctk.CTkLabel(
            left_title_frame,
            text="Sidik Jari Mentah",
            font=self.controller.FONT_UTAMA,
            text_color="white"
        )
        self.fs_raw_title.grid(row=0, column=0, padx=(0, 6))

        self._fs_left_toggle_var = ctk.BooleanVar(value=False)
        self.fs_left_checkbox = ctk.CTkCheckBox(
            left_title_frame,
            text="",
            variable=self._fs_left_toggle_var,
            command=self._on_fs_toggle,
            fg_color="#1f6aa5",
            border_color="white",
            checkbox_width=16,
            checkbox_height=16
        )
        self.fs_left_checkbox.grid(row=0, column=1)

        self.fs_raw_image_label = ctk.CTkLabel(left_container, text="")
        self.fs_raw_image_label.grid(row=1, column=0, sticky="nsew")

        # PANEL KANAN
        right_container = ctk.CTkFrame(self.fullscreen_overlay, fg_color="black")
        right_container.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=(10, 0))
        right_container.grid_rowconfigure(1, weight=1)
        right_container.grid_columnconfigure(0, weight=1)

        right_title_frame = ctk.CTkFrame(right_container, fg_color="black")
        right_title_frame.grid(row=0, column=0, pady=(0, 10), sticky="w")
        right_title_frame.grid_columnconfigure(0, weight=0)
        right_title_frame.grid_columnconfigure(1, weight=0)

        self.fs_ext_title = ctk.CTkLabel(
            right_title_frame,
            text="Sidik Jari Hasil Ekstraksi",
            font=self.controller.FONT_UTAMA,
            text_color="white"
        )
        self.fs_ext_title.grid(row=0, column=0, padx=(0, 6))

        self._fs_right_toggle_var = ctk.BooleanVar(value=False)
        self.fs_right_checkbox = ctk.CTkCheckBox(
            right_title_frame,
            text="",
            variable=self._fs_right_toggle_var,
            command=self._on_fs_toggle,
            fg_color="#1f6aa5",
            border_color="white",
            checkbox_width=16,
            checkbox_height=16
        )
        self.fs_right_checkbox.grid(row=0, column=1)

        self.fs_ext_image_label = ctk.CTkLabel(right_container, text="")
        self.fs_ext_image_label.grid(row=1, column=0, sticky="nsew")

        # ROW UNTUK SLIDER ZOOM
        self.fullscreen_overlay.grid_rowconfigure(2, weight=0)

        zoom_frame = ctk.CTkFrame(self.fullscreen_overlay, fg_color="black")
        zoom_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=40, pady=(5, 20))
        zoom_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            zoom_frame,
            text="Zoom:",
            font=self.controller.FONT_UTAMA,
            text_color="white"
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))

        self._fs_zoom_var = ctk.DoubleVar(value=100.0)

        self.zoom_slider = ctk.CTkSlider(
            zoom_frame,
            from_=50,
            to=200,
            variable=self._fs_zoom_var,
            command=self._on_zoom_slider
        )
        self.zoom_slider.grid(row=0, column=1, sticky="ew")

        self.zoom_label = ctk.CTkLabel(
            zoom_frame,
            text="100%",
            font=self.controller.FONT_UTAMA,
            text_color="white"
        )
        self.zoom_label.grid(row=0, column=2, sticky="e", padx=(10, 0))

    def _on_zoom_slider(self, value):
        if self.zoom_label is not None:
            self.zoom_label.configure(text=f"{int(value)}%")
        self._update_fullscreen_images()

    def _on_fs_toggle(self):
        # Checkbox kiri/kanan berubah → update gambar
        self._update_fullscreen_images()

    def show_fullscreen_comparison(self):
        path_mentah = self.record_paths.get("Mentah")
        path_ekstraksi = self.record_paths.get("Ekstraksi")

        if not path_mentah or not os.path.exists(path_mentah):
            messagebox.showerror("Data tidak lengkap", "Path gambar mentah tidak ditemukan.")
            return

        if not path_ekstraksi or not os.path.exists(path_ekstraksi):
            messagebox.showerror("Data tidak lengkap", "Path gambar hasil ekstraksi tidak ditemukan.")
            return

        self._init_fullscreen_overlay()

        w = self.controller.winfo_width()
        h = self.controller.winfo_height()
        if w <= 1 or h <= 1:
            w, h = 1200, 700  # fallback

        max_w_each = (w - 60) // 2
        max_h = h - 130   # ruang header + slider

        self._fs_box_w = int(max_w_each * 0.95)
        self._fs_box_h = int(max_h * 0.95)

        try:
            self._fs_raw_pil = Image.open(path_mentah)
            self._fs_ext_pil = Image.open(path_ekstraksi)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal membuka gambar:\n{e}")
            return

        # reset zoom & checkbox setiap kali buka
        if self._fs_zoom_var is not None:
            self._fs_zoom_var.set(100.0)
            if self.zoom_label is not None:
                self.zoom_label.configure(text="100%")
        if self._fs_left_toggle_var is not None:
            self._fs_left_toggle_var.set(False)
        if self._fs_right_toggle_var is not None:
            self._fs_right_toggle_var.set(False)

        self._update_fullscreen_images()

        self.fullscreen_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.fullscreen_overlay.lift()
        self.controller.update_idletasks()

    def _update_fullscreen_images(self):
        if (
            self.fullscreen_overlay is None
            or self._fs_raw_pil is None
            or self._fs_ext_pil is None
            or self._fs_box_w is None
            or self._fs_box_h is None
        ):
            return

        zoom_factor = 1.0
        if self._fs_zoom_var is not None:
            zoom_factor = max(self._fs_zoom_var.get() / 100.0, 0.1)

        # Tentukan gambar kiri & kanan berdasarkan checkbox
        left_use_ext = self._fs_left_toggle_var.get() if self._fs_left_toggle_var is not None else False
        right_use_raw = self._fs_right_toggle_var.get() if self._fs_right_toggle_var is not None else False

        left_pil = self._fs_ext_pil if left_use_ext else self._fs_raw_pil
        right_pil = self._fs_raw_pil if right_use_raw else self._fs_ext_pil

        self._fs_raw_ctk_image = self._make_ctk_image_boxed(
            left_pil, self._fs_box_w, self._fs_box_h, zoom_factor=zoom_factor
        )
        self._fs_ext_ctk_image = self._make_ctk_image_boxed(
            right_pil, self._fs_box_w, self._fs_box_h, zoom_factor=zoom_factor
        )

        if self._fs_raw_ctk_image is not None:
            self.fs_raw_image_label.configure(image=self._fs_raw_ctk_image, text="")
            self.fs_raw_image_label.image = self._fs_raw_ctk_image
        else:
            self.fs_raw_image_label.configure(text="Gagal memuat gambar mentah.", image=None)
            self.fs_raw_image_label.image = None

        if self._fs_ext_ctk_image is not None:
            self.fs_ext_image_label.configure(image=self._fs_ext_ctk_image, text="")
            self.fs_ext_image_label.image = self._fs_ext_ctk_image
        else:
            self.fs_ext_image_label.configure(text="Gagal memuat gambar hasil ekstraksi.", image=None)
            self.fs_ext_image_label.image = None

    def hide_fullscreen_overlay(self):
        if self.fullscreen_overlay is not None:
            self.fullscreen_overlay.place_forget()
            self.controller.update_idletasks()

    # ---------- EDIT & DELETE ----------
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

            if delete_history(self.record_id, path_mentah, path_ekstraksi):
                messagebox.showinfo("Sukses", "Data dan file kasus berhasil dihapus.")
                self.controller.show_frame("RiwayatPencarian")
            else:
                messagebox.showerror("Error", "Gagal menghapus data.")


# ===========================
# HALAMAN 4C: EDIT RIWAYAT
# ===========================
class EditPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="gray17")
        self.controller = controller
        self.record_id = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Edit Data Kasus", font=controller.FONT_JUDUL).grid(
            row=0, column=0, padx=20, pady=(20, 10), sticky="w"
        )

        self.edit_card = ctk.CTkFrame(self, fg_color="gray15", corner_radius=10)
        self.edit_card.grid(row=1, column=0, padx=20, pady=10, sticky="nwe")
        self.edit_card.grid_columnconfigure(0, weight=1)

        self._setup_edit_form()

    def _setup_edit_form(self):
        controller = self.controller

        ctk.CTkLabel(self.edit_card, text="ID Kasus:", font=controller.FONT_UTAMA, anchor="w").grid(
            row=0, column=0, padx=30, pady=(20, 0), sticky="ew"
        )
        self.lbl_id = ctk.CTkLabel(self.edit_card, text="", font=controller.FONT_SUBJUDUL, anchor="w")
        self.lbl_id.grid(row=1, column=0, padx=30, pady=(5, 10), sticky="ew")

        ctk.CTkLabel(self.edit_card, text="Judul Kasus:", font=controller.FONT_UTAMA, anchor="w").grid(
            row=2, column=0, padx=30, pady=(20, 0), sticky="ew"
        )
        self.entry_judul = ctk.CTkEntry(self.edit_card, font=controller.FONT_UTAMA)
        self.entry_judul.grid(row=3, column=0, padx=30, pady=(5, 10), sticky="ew")

        ctk.CTkLabel(self.edit_card, text="Nomor LP:", font=controller.FONT_UTAMA, anchor="w").grid(
            row=4, column=0, padx=30, pady=(10, 0), sticky="ew"
        )
        self.entry_lp = ctk.CTkEntry(self.edit_card, font=controller.FONT_UTAMA)
        self.entry_lp.grid(row=5, column=0, padx=30, pady=(5, 10), sticky="ew")

        ctk.CTkLabel(self.edit_card, text="Tanggal Kejadian:", font=controller.FONT_UTAMA, anchor="w").grid(
            row=6, column=0, padx=30, pady=(10, 0), sticky="ew"
        )
        self.entry_tanggal = ctk.CTkEntry(self.edit_card, font=controller.FONT_UTAMA)
        self.entry_tanggal.grid(row=7, column=0, padx=30, pady=(5, 20), sticky="ew")

        action_frame = ctk.CTkFrame(self.edit_card, fg_color="transparent")
        action_frame.grid(row=8, column=0, padx=30, pady=30, sticky="e")

        btn_simpan = ctk.CTkButton(
            action_frame,
            text="Simpan Perubahan",
            command=self.save_changes,
            height=40,
            fg_color="#1f6aa5",
            hover_color="#18537a"
        )
        btn_simpan.pack(side="left", padx=10)

        btn_batal = ctk.CTkButton(
            action_frame,
            text="Batal",
            command=lambda: self.controller.show_frame("DetailPage", data={'id': self.record_id}),
            height=40,
            fg_color="gray40",
            hover_color="gray25"
        )
        btn_batal.pack(side="left")

    def load_data(self, data_dict):
        self.record_id = data_dict['id']
        record = fetch_history_by_id(self.record_id)

        if record:
            self.lbl_id.configure(text=str(self.record_id))

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
            self.controller.show_frame("DetailPage", data={'id': self.record_id})
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan perubahan: {e}")
