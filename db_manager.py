import sqlite3
import os
import hashlib
from datetime import datetime
from PIL import Image
import numpy as np
import pandas as pd # Tambahkan Pandas untuk menangani DataFrame minutiae

# Impor Pustaka Utama
import cv2 # Digunakan untuk visualisasi fallback OpenCV
from fingerflow.extractor import Extractor 
import shutil 

# =========================================================================
# --- KONFIGURASI PATHS ---
# =========================================================================

# Tentukan direktori aplikasi saat ini
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
DB_NAME = 'minutiae_app_fixed.db'
DB_PATH = os.path.join(BASE_DIR, DB_NAME)
MINUTIAE_COUNT = 0

# Folder untuk menyimpan gambar mentah dan hasil ekstraksi
DATA_DIR = os.path.join(BASE_DIR, 'data_kasus')
MENTAH_DIR = os.path.join(DATA_DIR, 'mentah')
EKSTRAKSI_DIR = os.path.join(DATA_DIR, 'ekstraksi')
# Pastikan semua folder ada
for d in (DATA_DIR, MENTAH_DIR, EKSTRAKSI_DIR):
    os.makedirs(d, exist_ok=True)

# Folder untuk model Fingerflow (.h5)
MODEL_DIR = os.path.join(BASE_DIR, 'models') 
os.makedirs(MODEL_DIR, exist_ok=True) 


# =========================================================================
# --- MANAJEMEN DATABASE (SQLite) ---
# =========================================================================

def get_db_connection():
    """Membuat koneksi ke database SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Agar data bisa diakses seperti dictionary
    return conn

def ensure_user_columns(conn):
    """
    Pastikan kolom-kolom tambahan pada tabel users ada.
    Fungsi ini aman dijalankan berulang kali — ia memeriksa pragma table_info.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    existing = {row[1] for row in cursor.fetchall()}  # set of column names

    # Kolom yang diinginkan beserta tipe SQLnya
    columns = {
        "full_name": "TEXT",
        "nrp": "TEXT",
        "jabatan": "TEXT",
        "nomor_hp": "TEXT",
        "email": "TEXT",
        "is_admin": "INTEGER DEFAULT 0",
        "level": "INTEGER DEFAULT 0",  # 0 = user biasa, 1 = admin
        "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP"
    }

    for col, coldef in columns.items():
        if col not in existing:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {coldef}")
            except Exception as e:
                # Jika gagal tambahkan, lewati (tidak fatal)
                print(f"[migrasi] Gagal menambah kolom {col}: {e}")
    conn.commit()


def create_default_admin(conn, username="admin", password="123"):
    """
    Buat user admin default jika belum ada (berlaku untuk inisialisasi dev).
    Password akan di-hash menggunakan hash_password.
    level = 1 menandakan admin.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username=?", (username,))
    if cursor.fetchone() is None:
        ph = hash_password(password)
        try:
            # pastikan kolom is_admin & level sudah ada (ensure_user_columns sudah dipanggil di init_db)
            cursor.execute(
                "INSERT INTO users (username, password_hash, is_admin, level) VALUES (?, ?, ?, ?)",
                (username, ph, 1, 1)
            )
            conn.commit()
            print(f"[init_db] User admin '{username}' dibuat otomatis.")
        except Exception as e:
            print(f"[init_db] Gagal membuat admin: {e}")
            
def init_db():
    """Menginisialisasi tabel database (hanya dipanggil sekali)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabel Users (diperluas menyimpan profil)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            nrp TEXT,
            jabatan TEXT,
            nomor_hp TEXT,
            email TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    
    # Tabel History (Riwayat Pencarian)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            judul_kasus TEXT NOT NULL,
            nomor_lp TEXT,
            tanggal_kejadian TEXT,
            path_mentah TEXT NOT NULL,
            path_ekstraksi TEXT NOT NULL,
            user_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            minutiae_count INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    
    # Pastikan kolom-kolom users ada (migrasi bila perlu)
    try:
        ensure_user_columns(conn)
    except Exception as e:
        print('[init_db] ensure_user_columns error:', e)

    # Buat admin default jika belum ada
    try:
        create_default_admin(conn)
    except Exception as e:
        print('[init_db] create_default_admin error:', e)

    conn.commit()
    conn.close()
# =========================================================================
# --- IMPORT VISUALISASI FINGERFLOW (PERBAIKAN TERAKHIR) ---
# =========================================================================

# Menggunakan satu variabel fungsi tunggal untuk visualisasi
draw_minutiae_func = None
def enhance_fingerprint_image_array(
    img_bgr,
    target_long_side=512,
    clahe_clip=2.0,
    clahe_grid=(8, 8),
    denoise_strength=5,
    sharp_amount=1.0,
):
    """
    Enhance gambar sidik jari sebelum ekstraksi minutiae.

    Parameter:
        img_bgr : np.ndarray, gambar 3-channel (BGR) uint8
    Return:
        enhanced_bgr : np.ndarray (BGR)
        enhanced_gray : np.ndarray (grayscale)
    """
    import cv2
    import numpy as np

    if img_bgr is None:
        raise ValueError("img_bgr = None (gambar tidak terbaca)")

    # 1. Konversi ke grayscale
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # 2. Resize (upscale kalau gambar kecil)
    h, w = gray.shape[:2]
    long_side = max(h, w)
    if long_side < target_long_side:
        scale = target_long_side / float(long_side)
        new_w, new_h = int(w * scale), int(h * scale)
        gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    else:
        new_h, new_w = h, w  # tidak di-resize

    # 3. CLAHE untuk kontras lokal
    clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=clahe_grid)
    gray_clahe = clahe.apply(gray)

    # 4. Denoise ringan (bilateral)
    if denoise_strength > 0:
        gray_denoised = cv2.bilateralFilter(
            gray_clahe,
            d=7,
            sigmaColor=denoise_strength * 10,
            sigmaSpace=denoise_strength,
        )
    else:
        gray_denoised = gray_clahe

    # 5. Sharpen (unsharp masking)
    if sharp_amount > 0:
        blur = cv2.GaussianBlur(gray_denoised, (0, 0), sigmaX=1.0)
        gray_sharp = cv2.addWeighted(
            gray_denoised,
            1 + sharp_amount,
            blur,
            -sharp_amount,
            0,
        )
    else:
        gray_sharp = gray_denoised

    # 6. Balik ke BGR untuk FingerFlow
    enhanced_bgr = cv2.cvtColor(gray_sharp, cv2.COLOR_GRAY2BGR)

    return enhanced_bgr, gray_sharp
# --- FUNGSI FALLBACK VISUALISASI MENGGUNAKAN OPENCV (SELALU DEFINISIKAN) ---
def draw_minutiae_fallback_cv2(img_canvas, minutiae_df):
    """Visualisasi minutiae manual menggunakan OpenCV."""
    # Input sekarang adalah minutiae_df (Pandas DataFrame)
    
    if minutiae_df is not None and isinstance(minutiae_df, pd.DataFrame) and not minutiae_df.empty:
        
        # Iterasi melalui baris DataFrame
        for index, minutia in minutiae_df.iterrows():
            # Ambil koordinat X dan Y dari kolom DataFrame
            try:
                # Kolom X dan Y dari DataFrame harus diubah ke integer untuk OpenCV
                x, y = int(round(minutia["x"])), int(round(minutia["y"])) 
            except (KeyError, ValueError, IndexError):
                # Abaikan baris data yang rusak atau yang tidak memiliki kolom x/y
                continue
            
            # Gambar lingkaran merah (BGR: Merah = 0, 0, 255)
            # Gambar, Center (x, y), Radius, Warna (BGR: Merah), Ketebalan (-1 = Fill)
            cv2.circle(img_canvas, (x, y), 5, (255, 0, 0), -1) 
            
    return img_canvas 


# --- Mencoba Impor Fungsi Otomatis dari Fingerflow ---
try:
    from fingerflow.io import draw_minutiae as draw_minutiae_func
except ImportError:
    try:
        from fingerflow.extractor import draw_minutiae as draw_minutiae_func
    except ImportError:
        try:
            from fingerflow import draw_minutiae as draw_minutiae_func
        except ImportError:
            pass # Lanjut ke penugasan fallback
            
if draw_minutiae_func is None:
    print("Peringatan: Gagal mengimpor draw_minutiae. Menggunakan visualisasi manual (OpenCV).")
    # Tetapkan fungsi fallback manual sebagai visualizer
    draw_minutiae_func = draw_minutiae_fallback_cv2

# =========================================================================
# --- MANAJEMEN USER ---
# =========================================================================

def hash_password(password):
    """Menghasilkan hash SHA-256 untuk password."""
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username, password, full_name=None, nrp=None, jabatan=None, nomor_hp=None, email=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    password_hashed = hash_password(password)
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, full_name, nrp, jabatan, nomor_hp, email) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (username, password_hashed, full_name, nrp, jabatan, nomor_hp, email)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Username sudah ada
        conn.close()
        return False

def check_user_credentials(username, password):
    """Mengecek kredensial login. Mengembalikan user_id (integer) jika sukses, None jika gagal."""
    conn = get_db_connection()
    cursor = conn.cursor()
    password_hashed = hash_password(password)

    cursor.execute("SELECT id FROM users WHERE username = ? AND password_hash = ?", (username, password_hashed))
    user = cursor.fetchone()
    conn.close()

    if user:
        return user[0] # Mengembalikan INTEGER user_id
    return None


# =========================================================================
# --- LOGIKA EKSTRAKSI MINUTIAE (CORE LOGIC) ---
# =========================================================================

def run_minutiae_extraction(input_filepath, case_judul, progress_callback=None):
    def report(msg):
        if progress_callback is not None:
            try:
                progress_callback(msg)
            except Exception:
                pass

    # Format judul kasus agar aman digunakan sebagai nama file
    report("Menyiapkan nama file & lokasi output...")
    sanitized_judul = "".join(
        c for c in case_judul if c.isalnum() or c in (" ", "_")
    ).rstrip()[:30].replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"{timestamp}_{sanitized_judul}"

    path_mentah = os.path.join(DATA_DIR, f"{base_filename}_mentah.png")
    path_ekstraksi = os.path.join(DATA_DIR, f"{base_filename}_ekstraksi.png")

    # 1. Buka Gambar & Simpan Versi Mentah (Grayscale)
    try:
        # Buka gambar dan konversi ke Grayscale (L)
        report("Memuat gambar dan menyimpan versi mentah (Hitam Putih)...")
        img_pil = Image.open(input_filepath).convert("L")
        img_pil.save(path_mentah, "PNG")  # simpan mentah grayscale untuk arsip

        # Konversi ke NumPy Array (1 channel, 0-255)
        img_raw_single_channel = np.array(img_pil)

        # Buat 3-channel (BGR) untuk diproses OpenCV / FingerFlow
        img_raw_3channel = np.stack(
            (img_raw_single_channel,) * 3,
            axis=-1,
        ).astype("uint8")

    except Exception as e:
        print(f"ERROR: Gagal memuat atau menyimpan gambar mentah: {e}")
        return None, None

    # 1b. ENHANCE GAMBAR SEBELUM DIUMPANKAN KE FINGERFLOW
    try:
        report("Meningkatkan kualitas gambar sidik jari...")
        enhanced_bgr, enhanced_gray = enhance_fingerprint_image_array(
            img_raw_3channel,
            target_long_side=512,
            clahe_clip=2.0,
            clahe_grid=(8, 8),
            denoise_strength=5,
            sharp_amount=1.0,
        )
    except Exception as e:
        print(f"WARNING: Gagal enhance gambar, pakai gambar mentah 3-channel. Error: {e}")
        enhanced_bgr = img_raw_3channel
        enhanced_gray = img_raw_single_channel

    # 2. EKSTRAKSI MINUTIAE (Fingerflow)
    try:
        # Tentukan path lengkap ke setiap model menggunakan folder 'models'
        report("Memuat model...")
        coarse_path = os.path.join(MODEL_DIR, "CoarseNet.h5")
        fine_path = os.path.join(MODEL_DIR, "FineNet.h5")
        classify_path = os.path.join(MODEL_DIR, "ClassifyNet_6_classes.h5")
        core_path = os.path.join(MODEL_DIR, "CoreNet.weights")

        # Pengecekan Eksistensi File Model
        if not all(os.path.exists(p) for p in [coarse_path, fine_path, classify_path, core_path]):
            raise FileNotFoundError(
                f"Satu atau lebih file model Fingerflow (.h5/weights) tidak ditemukan di: {MODEL_DIR}"
            )

        # Inisialisasi Extractor
        report("memuat model ekstraksi minutiae...")
        extractor = Extractor(
            coarse_net_path=coarse_path,
            fine_net_path=fine_path,
            classify_net_path=classify_path,
            core_net_path=core_path,
        )
         # Ekstraksi minutiae → PAKAI GAMBAR YANG SUDAH DI-ENHANCE
        report("Menjalankan ekstraksi minutiae...")
        output_data = extractor.extract_minutiae(enhanced_bgr)  # Output: dict

        # AMBIL DATAFRAME MINUTIAE
        minutiae_df = output_data.get("minutiae")

        # Hitung jumlah minutiae
        num_minutiae = (
            len(minutiae_df)
            if minutiae_df is not None and not minutiae_df.empty
            else 0
        )

        global MINUTIAE_COUNT 
        MINUTIAE_COUNT = num_minutiae  # Simpan ke atribut untuk referensi luar
        print(f"DEBUG: Jumlah minutiae yang terdeteksi: {num_minutiae}")

        # 3. Visualisasi Hasil Ekstraksi
        report("Menyusun visualisasi hasil ekstraksi...")
        if num_minutiae == 0:
            print(
                "Peringatan: Tidak ada minutiae yang terdeteksi. Menyimpan gambar enhance grayscale saja."
            )
            # pakai enhanced_gray sebagai gambar hasil
            img_hasil_pil = Image.fromarray(enhanced_gray)
        else:
            # Gunakan salinan gambar enhance 3-channel sebagai kanvas
            img_canvas = enhanced_bgr.copy()

            # Panggil draw_minutiae_func (dari fingerflow atau fallback OpenCV)
            img_with_minutiae_np = draw_minutiae_func(img_canvas, minutiae_df)

            # Konversi ke PIL untuk disimpan
            report("Menyimpan gambar hasil ekstraksi...")
            img_hasil_pil = Image.fromarray(img_with_minutiae_np)

        # Simpan gambar hasil ekstraksi
        img_hasil_pil.save(path_ekstraksi, "PNG")

    except FileNotFoundError as fnf_e:
        print(
            f"ERROR: Model tidak ditemukan. Pastikan 4 file model ada di folder 'models'. {fnf_e}"
        )
        return None, None
    except Exception as e:
        print(f"ERROR: Gagal ekstraksi minutiae (Fingerflow). Error: {e}")
        if os.path.exists(path_ekstraksi):
            os.remove(path_ekstraksi)
        return None, None

    # Mengembalikan path tempat file disimpan
    return path_mentah, path_ekstraksi


# =========================================================================
# --- MANAJEMEN RIWAYAT (HISTORY) ---
# =========================================================================

def fetch_history_counts(id):
    """Mengambil jumlah total kasus (history)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Hitungan total kasus
    cursor.execute('SELECT COUNT(id) FROM history')
    count_umum = cursor.fetchone()[0]
    
    # Placeholder untuk 'lokal' (jika tidak ada filter yang digunakan)
    cursor.execute('SELECT COUNT(id) FROM history WHERE user_id = ?', (id,))
    count_lokal = cursor.fetchone()[0]
    
    conn.close()
    
    return count_umum, count_lokal

def get_history_data(user_id=None):
    """
    Mengambil data riwayat dari database, difilter berdasarkan user_id jika diberikan.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    sql_query = '''
        SELECT 
            h.id, h.judul_kasus, h.nomor_lp, h.tanggal_kejadian, 
            h.timestamp,h.minutiae_count, u.username
        FROM history h
        JOIN users u ON h.user_id = u.id
    '''
    params = []

    if user_id is not None:
        sql_query += ' WHERE h.user_id = ?'
        params.append(user_id)
        
    sql_query += ' ORDER BY h.timestamp DESC'

    try:
        cursor.execute(sql_query, params)
        data = cursor.fetchall()
        return data
    except Exception as e:
        print(f"Error executing get_history_data: {e}")
        return []
    finally:
        conn.close()

def save_history(judul_kasus, nomor_lp, tanggal_kejadian, path_mentah, path_ekstraksi, user_id, minutiae_count=None):
    """Menyimpan riwayat ke database dan mengembalikan ID baris yang baru dibuat."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO history (judul_kasus, nomor_lp, tanggal_kejadian, path_mentah, path_ekstraksi, user_id, minutiae_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (judul_kasus, nomor_lp, tanggal_kejadian, path_mentah, path_ekstraksi, user_id, minutiae_count))
        
        last_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return last_id
        
    except Exception as e:
        print(f"Error saving history: {e}")
        conn.close()
        return None

def fetch_history_by_id(history_id):
    """Mengambil detail satu entri riwayat berdasarkan ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            h.id, h.judul_kasus, h.nomor_lp, h.tanggal_kejadian, 
            h.path_mentah, h.path_ekstraksi, h.timestamp, h.minutiae_count, u.username
        FROM history h
        JOIN users u ON h.user_id = u.id
        WHERE h.id = ?
    ''', (history_id,))
    data = cursor.fetchone()
    conn.close()
    return data

def update_history_data(history_id, judul, nomor_lp, tanggal):
    """Mengupdate data kasus (judul, LP, tanggal) di database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE history 
            SET judul_kasus = ?, nomor_lp = ?, tanggal_kejadian = ?
            WHERE id = ?
        ''', (judul, nomor_lp, tanggal, history_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating history ID {history_id}: {e}")
        conn.close()
        return False

def delete_history(history_id, path_mentah=None, path_ekstraksi=None):
    """Menghapus data history + menghapus file mentah & ekstraksi."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Hapus data pada database
        cursor.execute("DELETE FROM history WHERE id = ?", (history_id,))
        conn.commit()
        conn.close()

        # Hapus file mentah
        if path_mentah and os.path.exists(path_mentah):
            try:
                os.remove(path_mentah)
            except Exception as e:
                print(f"Gagal menghapus file mentah: {e}")

        # Hapus file ekstraksi
        if path_ekstraksi and os.path.exists(path_ekstraksi):
            try:
                os.remove(path_ekstraksi)
            except Exception as e:
                print(f"Gagal menghapus file ekstraksi: {e}")

        return True

    except Exception as e:
        print(f"Error deleting history ID {history_id}: {e}")
        conn.close()
        return False

def move_and_rename_history_images(history_id, old_path_mentah, old_path_ekstraksi):
    """
    Pindahkan dan rename file gambar mentah & ekstraksi
    ke folder:
      - data_kasus/mentah/ID_mentah.png
      - data_kasus/ekstraksi/ID_ekstraksi.png
    lalu update path di tabel history.

    Return: (final_path_mentah, final_path_ekstraksi)
    """
    # Pastikan folder tujuan tetap ada (jaga-jaga)
    os.makedirs(MENTAH_DIR, exist_ok=True)
    os.makedirs(EKSTRAKSI_DIR, exist_ok=True)

    new_mentah = None
    new_ekstraksi = None

    # --- Pindah & rename gambar mentah ---
    if old_path_mentah and os.path.exists(old_path_mentah):
        ext_mentah = os.path.splitext(old_path_mentah)[1] or ".png"
        new_mentah = os.path.join(MENTAH_DIR, f"{history_id}_mentah{ext_mentah}")
        try:
            shutil.move(old_path_mentah, new_mentah)
        except Exception as e:
            print(f"WARNING: gagal memindahkan file mentah: {e}")
            new_mentah = None

    # --- Pindah & rename gambar ekstraksi ---
    if old_path_ekstraksi and os.path.exists(old_path_ekstraksi):
        ext_ekstraksi = os.path.splitext(old_path_ekstraksi)[1] or ".png"
        new_ekstraksi = os.path.join(EKSTRAKSI_DIR, f"{history_id}_ekstraksi{ext_ekstraksi}")
        try:
            shutil.move(old_path_ekstraksi, new_ekstraksi)
        except Exception as e:
            print(f"WARNING: gagal memindahkan file ekstraksi: {e}")
            new_ekstraksi = None

    # --- Update path di database ---
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE history
            SET path_mentah   = COALESCE(?, path_mentah),
                path_ekstraksi = COALESCE(?, path_ekstraksi)
            WHERE id = ?
            """,
            (new_mentah, new_ekstraksi, history_id),
        )
        conn.commit()
    except Exception as e:
        print(f"WARNING: gagal update path history ID {history_id}: {e}")
    finally:
        conn.close()

    # Kalau rename gagal, tetap kembalikan path lama supaya UI masih bisa pakai
    final_mentah = new_mentah or old_path_mentah
    final_ekstraksi = new_ekstraksi or old_path_ekstraksi
    return final_mentah, final_ekstraksi


# Inisialisasi DB saat modul dimuat (opsional, tapi disarankan)

def force_admin_fix():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET level = 1, is_admin = 1 WHERE username = 'admin'")
    conn.commit()
    conn.close()
    print("[FIX] Admin diperbaiki menjadi level=1")

if __name__ == '__main__':
    init_db()
    force_admin_fix()
    # Contoh pendaftaran admin saat pertama kali dijalankan
    if register_user("admin", "123"):
        print("Database terinisialisasi. User 'admin' (pass: 123) berhasil didaftarkan.")
    else:
        print("Database terinisialisasi. User 'admin' sudah ada.")



# ---------------- User management helpers ----------------

# ---------------- Robust user helpers ----------------
def _get_user_columns(conn):
    """Return set of column names in users table."""
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(users)")
        cols = {row[1] for row in cursor.fetchall()}
        return cols
    except Exception:
        return set()

def get_all_users():
    """Return list of all users as dicts. Works even if some newer columns aren't present."""
    conn = get_db_connection()
    cols = _get_user_columns(conn)
    select_cols = ["id", "username"]
    # optional cols in preferred order
    for c in ["full_name", "nrp", "jabatan", "nomor_hp", "email", "is_admin", "level", "created_at"]:
        if c in cols:
            select_cols.append(c)
    sql = "SELECT " + ", ".join(select_cols) + " FROM users ORDER BY id DESC"
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    conn.close()
    users = []
    for r in rows:
        obj = {}
        for i, col in enumerate(select_cols):
            obj[col] = r[i]
        users.append(obj)
    return users

def get_user_by_id(user_id):
    """Return user dict for given id. Works with older/newer schemas."""
    conn = get_db_connection()
    cols = _get_user_columns(conn)
    select_cols = ["id", "username"]
    for c in ["full_name", "nrp", "jabatan", "nomor_hp", "email", "is_admin", "level", "created_at"]:
        if c in cols:
            select_cols.append(c)
    sql = "SELECT " + ", ".join(select_cols) + " FROM users WHERE id=?"
    cursor = conn.cursor()
    cursor.execute(sql, (user_id,))
    r = cursor.fetchone()
    conn.close()
    if not r:
        return None
    obj = {}
    for i, col in enumerate(select_cols):
        obj[col] = r[i]
    return obj

def update_user(user_id, full_name=None, nrp=None, jabatan=None, nomor_hp=None, email=None, is_admin=None, password=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    fields = []
    params = []
    if full_name is not None:
        fields.append("full_name = ?"); params.append(full_name)
    if nrp is not None:
        fields.append("nrp = ?"); params.append(nrp)
    if jabatan is not None:
        fields.append("jabatan = ?"); params.append(jabatan)
    if nomor_hp is not None:
        fields.append("nomor_hp = ?"); params.append(nomor_hp)
    if email is not None:
        fields.append("email = ?"); params.append(email)
    if is_admin is not None:
        # ensure column exists; if not, skip setting
        cols = _get_user_columns(conn)
        val = 1 if is_admin else 0
        if "is_admin" in cols:
            fields.append("is_admin = ?"); params.append(val)
        if "level" in cols:
            fields.append("level = ?"); params.append(val)
    if password is not None:
        ph = hash_password(password)
        fields.append("password_hash = ?"); params.append(ph)
    if not fields:
        conn.close()
        return False
    params.append(user_id)
    sql = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(sql, params)
    conn.commit()
    conn.close()
    return True

def delete_user_and_history(user_id):

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # delete history entries by user_id (assuming history table has user_id column)
        cursor.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
        # delete user
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        print('[db_manager] delete_user_and_history error:', e)
        return False
# -------------------------------------------------------
def get_minutiae_count():
    """Mengembalikan jumlah minutiae dari ekstraksi terakhir."""
    global MINUTIAE_COUNT
    return MINUTIAE_COUNT
