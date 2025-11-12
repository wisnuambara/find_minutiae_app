FingerFlow - Setup Guide

Selamat! Aplikasi FingerFlow sekarang siap dijalankan. Untuk memastikan aplikasi berjalan lancar di laptop baru, penting untuk mereplikasi lingkungan kerja yang sudah terbukti stabil. Berikut panduan langkah demi langkah.

🛠️ Persiapan

Python 3.7 (disarankan 3.7.9 64-bit)

File requirements.txt (buat dari lingkungan lama: pip freeze > requirements.txt)

1️⃣ Instal Python 3.7

Unduh dan instal Python 3.7.9 dari situs resmi Python. Pastikan jalur instalasi mudah diingat, misal: C:\Python37.

2️⃣ Buat Virtual Environment

Buka Terminal/CMD di folder aplikasi, kemudian buat virtual environment:

"C:\Path\To\Python37\python.exe" -m venv venv_fingerflow_37_new


Aktifkan virtual environment:

venv_fingerflow_37_new\Scripts\activate

3️⃣ Instal Dependency Krusial

Instal paket penting secara terpisah untuk menghindari konflik:

pip install tensorflow==2.5.0 protobuf==3.20.3
pip install scipy==1.2.1 numpy==1.19.5

4️⃣ Instal Sisa Library

Instal library lain sambil menjaga kompatibilitas SciPy:

pip install fingerflow --no-deps
pip install scikit-image pandas pytz keras-applications customtkinter opencv-python matplotlib

5️⃣ Jalankan Aplikasi

Cek instalasi dengan menjalankan aplikasi:

python main.py


Dengan mengikuti langkah-langkah ini, Anda akan mereplikasi lingkungan yang terbukti stabil, menghindari konflik dependency, dan siap menjalankan FingerFlow di laptop baru.
