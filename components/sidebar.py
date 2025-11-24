import customtkinter as ctk
import os
from PIL import Image

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, width=180, corner_radius=0, fg_color="gray18")
        self.controller = controller

        # --- Load all icons one time ---
        self.icons = {
            "home": self._load_icon("home.png"),
            "cari": self._load_icon("cari-minutiae.png"),
            "riwayat": self._load_icon("riwayat.png"),
            "manajemen": self._load_icon("manajemen-user.png"),
            "logout": self._load_icon("logout.png")
        }

       # ============================
        #       LOAD LOGO
        # ============================
        logo_path = os.path.join("assets", "logo-white-blue.png")
        self.logo_image = None
        if os.path.exists(logo_path):
            try:
                pil = Image.open(logo_path)
                self.logo_image = ctk.CTkImage(light_image=pil, dark_image=pil, size=(80, 80))
            except Exception:
                self.logo_image = None

        # reserve rows
        for r in range(0, 100):
            self.grid_rowconfigure(r, weight=0)
        self.grid_rowconfigure(98, weight=1)

        # ============================
        #          LOGO AREA
        # ============================
        if self.logo_image:
            ctk.CTkLabel(
                self,
                text="",
                image=self.logo_image,
                anchor="center"
            ).grid(row=0, column=0, padx=10, pady=(50, 50), sticky="ew")
        else:
            # fallback text (jaga-jaga kalau logo tidak ditemukan)
            ctk.CTkLabel(
                self,
                text="Find Minutiae",
                font=controller.FONT_JUDUL,
                text_color="#1f6aa5",
                anchor="center"
            ).grid(row=0, column=0, padx=10, pady=(20, 10), sticky="ew")

        # divider line
        ctk.CTkFrame(self, height=2, fg_color="gray30") \
            .grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 20))

        # ----- MENU CONTAINER -----
        self.menu_container = ctk.CTkFrame(self, fg_color="transparent")
        self.menu_container.grid(row=2, column=0, sticky="nsew", padx=0, pady=(0,0))
        self.menu_container.grid_columnconfigure(0, weight=1)

        self.menus = {}
        self.admin_menu_key = "Manajemen User"

        self._build_static_menus()
        self._maybe_add_admin_menu()

        # ----- LOGOUT BUTTON -----
        self.logout_btn = ctk.CTkButton(
            self,
            text="Logout",
            corner_radius=7,
            fg_color="#b33030",
            hover_color="#8b2626",
            text_color="white",
            command=self._on_logout,
            font=controller.FONT_UTAMA,
            anchor="center",
            image=self.icons.get("logout"),
            compound="left"
        )
        self.logout_btn.grid(row=99, column=0, sticky="ew", padx=10, pady=(6, 16))

    # ---------------------
    # ICON LOADER
    # ---------------------
    def _load_icon(self, filename, size=(18, 18)):
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

    # -----------------------
    # MENU BUILDER
    # -----------------------
    def _build_static_menus(self):
        for w in self.menu_container.winfo_children():
            w.destroy()
        self.menus.clear()

        row_counter = 0

        def add(key, text, cmd, icon_key=None):
            nonlocal row_counter
            icon = self.icons.get(icon_key) if icon_key else None

            btn = ctk.CTkButton(
                self.menu_container,
                text=text,
                corner_radius=7,
                fg_color="transparent",
                hover_color="gray25",
                command=cmd,
                font=self.controller.FONT_UTAMA,
                anchor="w",
                image=icon,
                compound="left"
            )
            btn.grid(row=row_counter, column=0, sticky="ew", padx=10, pady=(6, 6))
            self.menus[key] = btn
            row_counter += 1

        add("Home", "Home", lambda: self.controller.show_frame("Home"), icon_key="home")
        add("CariMinutiae", "Cari Minutiae", lambda: self.controller.show_frame("CariMinutiae"), icon_key="cari")
        add("RiwayatPencarian", "Riwayat Pencarian", lambda: self.controller.show_frame("RiwayatPencarian"), icon_key="riwayat")

    # -----------------------
    # ADMIN BUTTON – LEVEL
    # -----------------------
    def _maybe_add_admin_menu(self):
        level = getattr(self.controller, "logged_in_user_level", 0)
        show_admin = (level == 1)

        if show_admin and self.admin_menu_key not in self.menus:
            current_rows = len(self.menu_container.grid_slaves())

            btn = ctk.CTkButton(
                self.menu_container,
                text="Manajemen User",
                corner_radius=7,
                fg_color="transparent",
                hover_color="gray25",
                command=lambda: self.controller.show_frame("UserManagement"),
                font=self.controller.FONT_UTAMA,
                anchor="w",
                image=self.icons.get("manajemen"),
                compound="left"
            )
            btn.grid(row=current_rows, column=0, sticky="ew", padx=10, pady=(6, 6))
            self.menus[self.admin_menu_key] = btn

        if not show_admin and self.admin_menu_key in self.menus:
            self.menus[self.admin_menu_key].destroy()
            del self.menus[self.admin_menu_key]

    def refresh(self):
        self._build_static_menus()
        self._maybe_add_admin_menu()

    # -----------------------
    # ACTIVE MENU HIGHLIGHT
    # -----------------------
    def set_active(self, key):
        for btn in self.menus.values():
            btn.configure(fg_color="transparent")

        if key in self.menus:
            self.menus[key].configure(fg_color="#1f6aa5")

    # -----------------------
    # LOGOUT
    # -----------------------
    def _on_logout(self):
        if hasattr(self.controller, "logout"):
            self.controller.logout()
        else:
            try:
                self.controller.logged_in_user_id = None
                self.controller.logged_in_user_level = 0
            except Exception:
                pass
            self.refresh()
