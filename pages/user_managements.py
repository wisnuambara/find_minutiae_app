import customtkinter as ctk
import os
from tkinter import messagebox
from PIL import Image
from db_manager import get_all_users, get_user_by_id, update_user, delete_user_and_history

def cut_text(text, limit):
    if text is None:
        return "-"
    text = str(text)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."

# --------------------------------------------------------
#               HALAMAN: USER MANAGEMENT (LIST)
# --------------------------------------------------------
class UserManagementPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="gray17")
        self.controller = controller

        # Pagination & state
        self.page = 1
        self.page_size = 15
        self.total_items = 0

        # Column widths
        self.COL_WIDTH = {
            "id": 70,
            "nama": 360,
            "nrp": 160,
            "username": 200,
            "aksi": 100
        }

        # layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # header
        self._setup_header()

        # table area
        self._setup_table_frame()

        # pagination
        self._setup_pagination_controls()

        self.data_rows = []

    def _setup_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12,6))
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_frame, text="Manajemen User",
                     font=self.controller.FONT_JUDUL,
                     text_color="#1e90ff").grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(header_frame, text="Kelola akun terdaftar",
                     font=self.controller.FONT_SUBJUDUL).grid(row=1, column=0, sticky="w", pady=(2,0))

    def _setup_table_frame(self):
        self.table_outer = ctk.CTkFrame(self, fg_color="gray15")
        self.table_outer.grid(row=1, column=0, sticky="nsew", padx=12, pady=(6,6))
        self.table_outer.grid_columnconfigure(0, weight=1)
        self.table_outer.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.table_outer, fg_color="gray20", height=36)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure((0,1,2,3,4), weight=1)

        titles = [
            ("No", self.COL_WIDTH["id"]),
            ("Nama Lengkap", self.COL_WIDTH["nama"]),
            ("NRP", self.COL_WIDTH["nrp"]),
            ("Username", self.COL_WIDTH["username"]),
            ("Aksi", self.COL_WIDTH["aksi"])
        ]

        for idx, (txt, w) in enumerate(titles):
            lbl = ctk.CTkLabel(header,
                               text=txt,
                               font=self.controller.FONT_SUBJUDUL,
                               anchor="center")
            lbl.grid(row=0, column=idx, padx=4, pady=6, sticky="nsew")
            lbl.configure(width=w)

        # Scrollable area for rows
        self.scroll_area = ctk.CTkScrollableFrame(self.table_outer, fg_color="gray15", height=500)
        self.scroll_area.grid(row=1, column=0, sticky="nsew", pady=(6,6))
        self.scroll_area.grid_columnconfigure(0, weight=1)

        self.rows_container = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        self.rows_container.grid(row=0, column=0, sticky="nsew")
        self.rows_container.grid_columnconfigure(0, weight=1)

    def _setup_pagination_controls(self):
        pag = ctk.CTkFrame(self, fg_color="transparent")
        pag.grid(row=2, column=0, sticky="ew", padx=12, pady=(0,12))
        pag.grid_columnconfigure(1, weight=1)

        self.btn_prev = ctk.CTkButton(pag, text="◀ Sebelumnya", width=90, command=self.prev_page)
        self.btn_prev.grid(row=0, column=0, padx=(0,8))

        self.page_label = ctk.CTkLabel(pag, text=f"Halaman {self.page}", font=self.controller.FONT_UTAMA)
        self.page_label.grid(row=0, column=1)

        self.btn_next = ctk.CTkButton(pag, text="Selanjutnya ▶", width=90, command=self.next_page)
        self.btn_next.grid(row=0, column=2, padx=(8,0))

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.refresh_data()

    def next_page(self):
        if self.page * self.page_size < self.total_items:
            self.page += 1
            self.refresh_data()

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
            raw = get_all_users()
        except Exception as e:
            messagebox.showerror("Error", f"Gagal mengambil data user: {e}")
            raw = []

        self.total_items = len(raw)
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        page_data = raw[start:end]

        self.page_label.configure(
            text=f"Halaman {self.page}, Total User: {self.total_items}"
        )

        self.btn_prev.configure(state="normal" if self.page > 1 else "disabled")
        self.btn_next.configure(
            state="normal" if self.page * self.page_size < self.total_items else "disabled"
        )

        for i, u in enumerate(page_data):
            bg_color = "gray18" if (i % 2 == 0) else "gray17"

            row = ctk.CTkFrame(self.rows_container, fg_color=bg_color, height=42, corner_radius=4)
            row.grid(row=i, column=0, sticky="ew", padx=4, pady=2)
            row.grid_columnconfigure((0,1,2,3,4), weight=1)

            underline = ctk.CTkFrame(row, fg_color="gray12", height=1)
            underline.grid(row=1, column=0, columnspan=5, sticky="ew")

            def on_enter(e, f=row):
                f.configure(fg_color="gray25")
            def on_leave(e, f=row, orig=bg_color):
                f.configure(fg_color=orig)

            row.bind("<Enter>", on_enter)
            row.bind("<Leave>", on_leave)

            # No
            nomor = start + i + 1
            ctk.CTkLabel(row, text=str(nomor),
                         font=self.controller.FONT_UTAMA,
                         anchor="w",
                         width=self.COL_WIDTH["id"]).grid(row=0, column=0, padx=8)

            # Nama
            ctk.CTkLabel(row, text=cut_text(u.get("full_name") or "-", 40),
                         font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
                         anchor="w",
                         width=self.COL_WIDTH["nama"],
                         wraplength=self.COL_WIDTH["nama"]).grid(row=0, column=1, padx=6)

            # NRP
            ctk.CTkLabel(row, text=cut_text(u.get("nrp") or "-", 18),
                         font=self.controller.FONT_UTAMA,
                         anchor="w",
                         width=self.COL_WIDTH["nrp"]).grid(row=0, column=2, padx=4)

            # Username
            ctk.CTkLabel(row, text=cut_text(u.get("username") or "-", 18),
                         font=self.controller.FONT_UTAMA,
                         anchor="w",
                         width=self.COL_WIDTH["username"]).grid(row=0, column=3, padx=4)

            # Tombol lihat
            action = ctk.CTkFrame(row, fg_color="transparent")
            action.grid(row=0, column=4, padx=8, sticky="w")

            icon = None
            try:
                path = os.path.join("icons", "eye.png")
                if os.path.exists(path):
                    pil = Image.open(path)
                    icon = ctk.CTkImage(light_image=pil, dark_image=pil, size=(18,18))
            except:
                icon = None

            btn = ctk.CTkButton(
                action, text="", width=36, height=28, image=icon,
                fg_color="#1f6aa5", hover_color="#18537a",
                command=lambda uid=u['id']: self.show_detail(uid)
            )
            btn.pack()

            self.data_rows.append(row)

    def show_detail(self, user_id):
        try:
            data = get_user_by_id(user_id)
            if not data:
                messagebox.showerror("Error", "User tidak ditemukan.")
                return
            self.controller.show_frame("UserDetail", data)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menampilkan detail: {e}")

# --------------------------------------------------------
#                HALAMAN: USER DETAIL
# --------------------------------------------------------
class UserDetailPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="gray17")
        self.controller = controller
        self.user_id = None
        self.user_data = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20,10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="Detail User",
                     font=self.controller.FONT_JUDUL).grid(row=0, column=0, sticky="w")

        buttons = ctk.CTkFrame(header, fg_color="transparent")
        buttons.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(buttons, text="Edit Data", width=90,
                       command=self.enter_edit,
                       fg_color="gray40", hover_color="gray25").pack(side="left", padx=6)

        ctk.CTkButton(buttons, text="Hapus", width=90,
                       command=self._delete,
                       fg_color="#cc3300", hover_color="#992600").pack(side="left", padx=6)

        ctk.CTkButton(buttons, text="Kembali", width=90,
                       command=lambda: self.controller.show_frame("UserManagement")
                       ).pack(side="left", padx=6)

        # Content
        content = ctk.CTkFrame(self, fg_color="gray15")
        content.grid(row=1, column=0, sticky="nsew", padx=20, pady=12)
        content.grid_columnconfigure((0,1), weight=1)

        self._setup_info_panel(content, 0)
        self._setup_meta_panel(content, 1)

    def _setup_info_panel(self, parent, col):
        panel = ctk.CTkFrame(parent, fg_color="transparent")
        panel.grid(row=0, column=col, sticky="nwe", padx=30, pady=20)

        ctk.CTkLabel(panel, text="Data Akun:",
                     font=self.controller.FONT_SUBJUDUL,
                     text_color="#1f6aa5").pack(fill="x", pady=(0,10))

        def make_row(label):
            ctk.CTkLabel(panel, text=label, anchor="w",
                         font=self.controller.FONT_UTAMA).pack(fill="x")
            lbl = ctk.CTkLabel(panel, text="-", anchor="w",
                               font=self.controller.FONT_UTAMA)
            lbl.pack(fill="x", pady=(0,10))
            return lbl

        self.lbl_full = make_row("Nama Lengkap:")
        self.lbl_nrp = make_row("NRP:")
        self.lbl_nohp = make_row("No HP:")
        self.lbl_user = make_row("Username:")
        self.lbl_email = make_row("Email:")
        self.lbl_jabatan = make_row("Jabatan:")
        self.lbl_hp = make_row("Nomor HP:")
        self.lbl_level = make_row("Level:")

    def _setup_meta_panel(self, parent, col):
        panel = ctk.CTkFrame(parent, fg_color="transparent")
        panel.grid(row=0, column=col, sticky="nwe", padx=30, pady=20)

        ctk.CTkLabel(panel, text="Metadata:",
                     font=self.controller.FONT_SUBJUDUL,
                     text_color="#1f6aa5").pack(fill="x", pady=(0,10))

        ctk.CTkLabel(panel, text="Dibuat pada:",
                     font=self.controller.FONT_UTAMA, anchor="w").pack(fill="x")

        self.lbl_created = ctk.CTkLabel(panel, text="-",
                                        font=self.controller.FONT_UTAMA,
                                        anchor="w")
        self.lbl_created.pack(fill="x", pady=(0,10))

    def load_data(self, data):
        self.user_id = data.get("id")
        self.user_data = get_user_by_id(self.user_id)
        self._render()

    def _render(self):
        u = self.user_data or {}

        self.lbl_full.configure(text=u.get("full_name") or "-")
        self.lbl_nrp.configure(text=u.get("nrp") or "-")
        self.lbl_nohp.configure(text=u.get("nomor_hp") or "-")
        self.lbl_user.configure(text=u.get("username") or "-")
        self.lbl_email.configure(text=u.get("email") or "-")
        self.lbl_jabatan.configure(text=u.get("jabatan") or "-")
        self.lbl_hp.configure(text=u.get("nomor_hp") or "-")
        self.lbl_created.configure(text=u.get("created_at") or "-")

        # LEVEL USER
        lvl = u.get("level", 0)
        self.lbl_level.configure(text="Admin" if lvl == 1 else "User")

    def enter_edit(self):
        self.controller.show_frame("UserEdit", data={"id": self.user_id})

    def _delete(self):
        if not self.user_id:
            return

        if messagebox.askyesno("Konfirmasi Hapus", "Hapus user ini dan semua data terkait?"):
            if delete_user_and_history(self.user_id):
                messagebox.showinfo("Sukses", "User berhasil dihapus.")
                self.controller.show_frame("UserManagement")
            else:
                messagebox.showerror("Gagal", "Tidak dapat menghapus user.")


# --------------------------------------------------------
#                HALAMAN: USER EDIT
# --------------------------------------------------------
class UserEditPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="gray17")
        self.controller = controller
        self.record_id = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self,
                     text="Edit Data User",
                     font=controller.FONT_JUDUL).grid(row=0, column=0,
                                                      padx=20, pady=(20, 10), sticky="w")

        self.edit_card = ctk.CTkFrame(self, fg_color="gray15", corner_radius=10)
        self.edit_card.grid(row=1, column=0, padx=20, pady=10, sticky="nwe")
        self.edit_card.grid_columnconfigure(0, weight=1)

        self._setup_edit_form()

    def _setup_edit_form(self):
        ctk.Label = ctk.CTkLabel
        controller = self.controller

        # Nama Lengkap
        ctk.Label(self.edit_card, text="Nama Lengkap:",
                  font=controller.FONT_UTAMA).grid(row=0, column=0, padx=30, pady=(20,0), sticky="w")
        self.entry_full = ctk.CTkEntry(self.edit_card, font=controller.FONT_UTAMA)
        self.entry_full.grid(row=1, column=0, padx=30, pady=(5,10), sticky="ew")

        # NRP
        ctk.Label(self.edit_card, text="NRP:",
                  font=controller.FONT_UTAMA).grid(row=2, column=0, padx=30, pady=(10,0), sticky="w")
        self.entry_nrp = ctk.CTkEntry(self.edit_card, font=controller.FONT_UTAMA)
        self.entry_nrp.grid(row=3, column=0, padx=30, pady=(5,10), sticky="ew")

        # Email
        ctk.Label(self.edit_card, text="Email:",
                  font=controller.FONT_UTAMA).grid(row=4, column=0, padx=30, pady=(10,0), sticky="w")
        self.entry_email = ctk.CTkEntry(self.edit_card, font=controller.FONT_UTAMA)
        self.entry_email.grid(row=5, column=0, padx=30, pady=(5,10), sticky="ew")

        # Jabatan
        ctk.Label(self.edit_card, text="Jabatan:",
                  font=controller.FONT_UTAMA).grid(row=6, column=0, padx=30, pady=(10,0), sticky="w")
        self.entry_jabatan = ctk.CTkEntry(self.edit_card, font=controller.FONT_UTAMA)
        self.entry_jabatan.grid(row=7, column=0, padx=30, pady=(5,20), sticky="ew")

        # Nomor HP
        ctk.Label(self.edit_card, text="Nomor HP:",
                  font=controller.FONT_UTAMA).grid(row=8, column=0, padx=30, pady=(10,0), sticky="w")
        self.entry_hp = ctk.CTkEntry(self.edit_card, font=controller.FONT_UTAMA)
        self.entry_hp.grid(row=9, column=0, padx=30, pady=(5,10), sticky="ew")

        # ============================
        #     LEVEL USER (DITAMBAHKAN)
        # ============================
        ctk.Label(self.edit_card, text="Level User:",
                  font=controller.FONT_UTAMA).grid(row=10, column=0, padx=30, pady=(10,0), sticky="w")

        self.combo_level = ctk.CTkComboBox(
            self.edit_card,
            values=["User", "Admin"],
            state="readonly",
            font=controller.FONT_UTAMA,
        )
        self.combo_level.grid(row=11, column=0, padx=30, pady=(5,10), sticky="ew")

        # Tombol aksi → geser dari row 10 ke row 12
        action_frame = ctk.CTkFrame(self.edit_card, fg_color="transparent")
        action_frame.grid(row=12, column=0, padx=30, pady=30, sticky="e")

        ctk.CTkButton(action_frame, text="Simpan Perubahan",
                      height=40, fg_color="#1f6aa5", hover_color="#18537a",
                      command=self.save_changes).pack(side="left", padx=10)

        ctk.CTkButton(action_frame, text="Batal", height=40,
                      fg_color="gray40", hover_color="gray25",
                      command=lambda: self.controller.show_frame("UserDetail", data={"id": self.record_id})
                      ).pack(side="left")

    def load_data(self, data_dict):
        self.record_id = data_dict.get("id")
        data = get_user_by_id(self.record_id)
        if not data:
            messagebox.showerror("Error", "User tidak ditemukan.")
            self.controller.show_frame("UserManagement")
            return

        # isi field
        self.entry_full.delete(0, ctk.END)
        self.entry_full.insert(0, data.get("full_name") or "")

        self.entry_nrp.delete(0, ctk.END)
        self.entry_nrp.insert(0, data.get("nrp") or "")

        self.entry_email.delete(0, ctk.END)
        self.entry_email.insert(0, data.get("email") or "")

        self.entry_jabatan.delete(0, ctk.END)
        self.entry_jabatan.insert(0, data.get("jabatan") or "")

        self.entry_hp.delete(0, ctk.END)
        self.entry_hp.insert(0, data.get("nomor_hp") or "")

        # ===== LOAD LEVEL USER =====
        lvl = data.get("level", 0)
        self.combo_level.set("Admin" if lvl == 1 else "User")

    def save_changes(self):
        if not self.record_id:
            return

        # ===== SAVE LEVEL =====
        level = 1 if self.combo_level.get() == "Admin" else 0

        ok = update_user(
            self.record_id,
            full_name=self.entry_full.get().strip(),
            nrp=self.entry_nrp.get().strip(),
            jabatan=self.entry_jabatan.get().strip(),
            email=self.entry_email.get().strip(),
            nomor_hp=self.entry_hp.get().strip(),
            is_admin=level   # sangat penting!
        )

        if ok:
            messagebox.showinfo("Sukses", "Perubahan disimpan.")
            self.controller.show_frame("UserDetail", data={"id": self.record_id})
        else:
            messagebox.showerror("Gagal", "Gagal menyimpan perubahan.")
