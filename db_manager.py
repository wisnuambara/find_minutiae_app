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

# =========================================================================
# --- IMPORT VISUALISASI FINGERFLOW (PERBAIKAN TERAKHIR) ---
# =========================================================================

# Menggunakan satu variabel fungsi tunggal untuk visualisasi
draw_minutiae_func = None

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
# --- KONFIGURASI PATHS ---
# =========================================================================

# Tentukan direktori aplikasi saat ini
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
DB_NAME = 'minutiae_app.db'
DB_PATH = os.path.join(BASE_DIR, DB_NAME)

# Folder untuk menyimpan gambar mentah dan hasil ekstraksi
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), 'data_kasus')
os.makedirs(DATA_DIR, exist_ok=True) 

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

def init_db():
    """Menginisialisasi tabel database (hanya dipanggil sekali)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabel Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
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
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()


# =========================================================================
# --- MANAJEMEN USER ---
# =========================================================================

def hash_password(password):
    """Menghasilkan hash SHA-256 untuk password."""
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    """Mendaftarkan user baru ke database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    password_hashed = hash_password(password)
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hashed))
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

def run_minutiae_extraction(input_filepath, case_judul):
    """
    Memproses gambar sidik jari (SJ), mengekstrak minutiae menggunakan Fingerflow,
    dan menyimpan gambar mentah/hasil ekstraksi ke folder DATA_DIR.
    
    Mengembalikan tuple (path_mentah_tersimpan, path_ekstraksi_tersimpan).
    """
    
    # Format judul kasus agar aman digunakan sebagai nama file
    sanitized_judul = "".join(c for c in case_judul if c.isalnum() or c in (' ', '_')).rstrip()[:30].replace(' ', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"{timestamp}_{sanitized_judul}"
    
    path_mentah = os.path.join(DATA_DIR, f"{base_filename}_mentah.png")
    path_ekstraksi = os.path.join(DATA_DIR, f"{base_filename}_ekstraksi.png")

    # 1. Buka Gambar & Konversi ke format yang sesuai
    try:
        # Buka gambar dan konversi ke Grayscale (L)
        img_pil = Image.open(input_filepath).convert("L") 
        img_pil.save(path_mentah, 'PNG') # Simpan yang grayscale untuk arsip
        
        # Konversi ke NumPy Array (1 channel, 0-255)
        img_raw_single_channel = np.array(img_pil)
        
        # PENTING: Membuat gambar 3-Channel (RGB) untuk Fingerflow Extractor dan Visualisasi
        img_raw_3channel = np.stack((img_raw_single_channel,)*3, axis=-1) 
        
    except Exception as e:
        print(f"ERROR: Gagal memuat atau menyimpan gambar mentah: {e}")
        return None, None
    
    # 2. EKSTRAKSI MINUTIAE (Fingerflow)
    try:
        # Tentukan path lengkap ke setiap model menggunakan folder 'models'
        coarse_path = os.path.join(MODEL_DIR, 'CoarseNet.h5')
        fine_path = os.path.join(MODEL_DIR, 'FineNet.h5')
        classify_path = os.path.join(MODEL_DIR, 'ClassifyNet_6_classes.h5')
        core_path = os.path.join(MODEL_DIR, 'CoreNet.weights')
        
        # Pengecekan Eksistensi File Model
        if not all(os.path.exists(p) for p in [coarse_path, fine_path, classify_path, core_path]):
             raise FileNotFoundError(f"Satu atau lebih file model Fingerflow (.h5/weights) tidak ditemukan di: {MODEL_DIR}")

        # Inisialisasi Extractor (Model Loading Terjadi di Sini)
        extractor = Extractor(
            coarse_net_path=coarse_path,
            fine_net_path=fine_path,
            classify_net_path=classify_path,
            core_net_path=core_path
        )
        
        # Ekstraksi minutiae
        output_data = extractor.extract_minutiae(img_raw_3channel) # Output adalah Dictionary
        
        # AMBIL DATAFRAME MINUTIAE DARI DICTIONARY HASIL EKSTRAKSI
        minutiae_df = output_data.get("minutiae")
        
        # Hitung jumlah minutiae yang terdeteksi
        num_minutiae = len(minutiae_df) if minutiae_df is not None and not minutiae_df.empty else 0
        print(f"DEBUG: Jumlah minutiae yang terdeteksi: {num_minutiae}")
        
        # 3. Tampilkan Hasil Ekstraksi (Visualisasi)
        
        # Cek apakah ada minutiae yang terdeteksi
        if num_minutiae == 0:
            print("Peringatan: Tidak ada minutiae yang terdeteksi. Menyimpan gambar mentah 3-channel.")
            img_hasil_pil = Image.fromarray(img_raw_3channel)
        else:
            # Gunakan salinan gambar 3-channel sebagai kanvas
            img_canvas = img_raw_3channel.copy() 
            
            # Panggil draw_minutiae_func (fungsi yang berhasil diimpor atau fallback OpenCV)
            # Meneruskan DataFrame minutiae_df ke fungsi visualisasi
            img_with_minutiae_np = draw_minutiae_func(img_canvas, minutiae_df)
            
            # Konversi hasil NumPy array ke PIL Image untuk disimpan
            img_hasil_pil = Image.fromarray(img_with_minutiae_np)
        
        # Simpan gambar hasil ekstraksi
        img_hasil_pil.save(path_ekstraksi, 'PNG') 
        
    except FileNotFoundError as fnf_e:
        print(f"ERROR: Model tidak ditemukan. Pastikan 4 file model ada di folder 'models'. {fnf_e}")
        return None, None
    except Exception as e:
        print(f"ERROR: Gagal ekstraksi minutiae (Fingerflow). Error: {e}")
        # Hapus file abu-abu jika ada untuk menghindari kebingungan
        if os.path.exists(path_ekstraksi):
            os.remove(path_ekstraksi) 
        return None, None

    # Mengembalikan path tempat file disimpan
    return path_mentah, path_ekstraksi


# =========================================================================
# --- MANAJEMEN RIWAYAT (HISTORY) ---
# =========================================================================

def fetch_history_counts():
    """Mengambil jumlah total kasus (history)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Hitungan total kasus
    cursor.execute('SELECT COUNT(id) FROM history')
    count_umum = cursor.fetchone()[0]
    
    # Placeholder untuk 'lokal' (jika tidak ada filter yang digunakan)
    count_lokal = 0 
    
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
            h.timestamp, u.username
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

def save_history(judul_kasus, nomor_lp, tanggal_kejadian, path_mentah, path_ekstraksi, user_id):
    """Menyimpan riwayat ke database dan mengembalikan ID baris yang baru dibuat."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO history (judul_kasus, nomor_lp, tanggal_kejadian, path_mentah, path_ekstraksi, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (judul_kasus, nomor_lp, tanggal_kejadian, path_mentah, path_ekstraksi, user_id))
        
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
            h.path_mentah, h.path_ekstraksi, h.timestamp, u.username
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

def delete_history(history_id):
    """Menghapus entri riwayat dari database dan file yang terkait."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT path_mentah, path_ekstraksi FROM history WHERE id = ?", (history_id,))
        paths = cursor.fetchone()

        if paths:
            cursor.execute("DELETE FROM history WHERE id = ?", (history_id,))
            conn.commit()
            
            # Hapus file dari sistem
            if os.path.exists(paths['path_mentah']):
                os.remove(paths['path_mentah'])
            if os.path.exists(paths['path_ekstraksi']):
                os.remove(paths['path_ekstraksi'])
            
            conn.close()
            return True
        
        conn.close()
        return False

    except Exception as e:
        print(f"Error deleting history ID {history_id}: {e}")
        conn.close()
        return False


# Inisialisasi DB saat modul dimuat (opsional, tapi disarankan)
if __name__ == '__main__':
    init_db()
    # Contoh pendaftaran admin saat pertama kali dijalankan
    if register_user("admin", "123"):
        print("Database terinisialisasi. User 'admin' (pass: 123) berhasil didaftarkan.")
    else:
        print("Database terinisialisasi. User 'admin' sudah ada.")