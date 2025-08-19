# 🚀 Creator Web Monitoring Bot v2.0 - Configuration Guide

## 📋 Overview

Script `scrape_windows.py` ini adalah bot monitoring otomatis untuk Instagram dan TikTok yang sekarang menggunakan **konstanta** untuk konfigurasi, tidak lagi memerlukan CLI arguments atau environment variables.

## ⚙️ Konfigurasi

### 🔧 File Konfigurasi

Semua konfigurasi ada di bagian atas file `scrape_windows.py`:

```python
# =============================================================================
# CONFIGURATION CONSTANTS - MODIFY THESE VALUES AS NEEDED
# =============================================================================

# Monitoring cycle interval (seconds)
CYCLE_SECONDS = 5

# Show browser window on Windows by default
SHOW_BROWSER = True

# Post-open wait behavior configuration
POST_OPEN_WAIT_MODE = 'auto'  # 'auto' or 'fixed'
POST_OPEN_WAIT_MS_IG = 5000   # 5000ms = 5 seconds for Instagram
POST_OPEN_WAIT_MS_TIKTOK = 3000  # 3000ms = 3 seconds for TikTok

# =============================================================================
# END CONFIGURATION CONSTANTS
# =============================================================================
```

## 🎯 Parameter Konfigurasi

### 1. **CYCLE_SECONDS** - Interval Monitoring
- **Default**: `5` detik (sangat cepat untuk testing)
- **Recommended**: `30` detik untuk production
- **Maximum**: `3600` detik (1 jam)
- **Penjelasan**: Berapa detik bot akan beristirahat antara setiap monitoring cycle

### 2. **SHOW_BROWSER** - Tampilkan Browser
- **True**: Browser window terlihat (bagus untuk debugging)
- **False**: Headless mode (lebih baik untuk production)
- **Penjelasan**: Apakah browser window ditampilkan atau tidak

### 3. **POST_OPEN_WAIT_MODE** - Mode Tunggu
- **'auto'**: Tunggu sampai elemen siap (recommended)
- **'fixed'**: Selalu tunggu waktu tetap
- **Penjelasan**: Bagaimana bot menunggu setelah membuka halaman

### 4. **POST_OPEN_WAIT_MS_IG** - Waktu Tunggu Instagram
- **Default**: `5000` ms = 5 detik
- **Range**: `1000` - `10000` ms
- **Penjelasan**: Berapa lama menunggu halaman Instagram siap

### 5. **POST_OPEN_WAIT_MS_TIKTOK** - Waktu Tunggu TikTok
- **Default**: `3000` ms = 3 detik
- **Range**: `1000` - `10000` ms
- **Penjelasan**: Berapa lama menunggu halaman TikTok siap

## 🚀 Cara Menjalankan

### 1. **Setup Dependencies**
```bash
# Install Python packages
pip install playwright pymongo psutil pytz

# Install browser Playwright
playwright install
```

### 2. **Jalankan Script**
```bash
# Dari folder root project
cd scrape
python scrape_windows.py

# Atau dengan path lengkap
python scrape/scrape_windows.py
```

### 3. **Tidak Perlu CLI Arguments Lagi!**
```bash
# ❌ DULU (tidak berlaku lagi):
# python scrape_windows.py --cycle-seconds 30 --show-browser false

# ✅ SEKARANG (langsung jalankan):
python scrape_windows.py
```

## 📊 Contoh Konfigurasi

### 🧪 **Testing Mode (Sangat Cepat)**
```python
CYCLE_SECONDS = 5          # Monitoring setiap 5 detik
SHOW_BROWSER = True         # Browser terlihat
POST_OPEN_WAIT_MODE = 'auto'  # Tunggu elemen siap
```

### 🚀 **Production Mode (Optimal)**
```python
CYCLE_SECONDS = 30         # Monitoring setiap 30 detik
SHOW_BROWSER = False        # Headless mode
POST_OPEN_WAIT_MODE = 'auto'  # Tunggu elemen siap
```

### ⚡ **Fast Mode (Balanced)**
```python
CYCLE_SECONDS = 15         # Monitoring setiap 15 detik
SHOW_BROWSER = False        # Headless mode
POST_OPEN_WAIT_MODE = 'fixed'  # Waktu tunggu tetap
```

## 🔄 Cara Mengubah Konfigurasi

### 1. **Edit File Langsung**
- Buka file `scrape/scrape_windows.py`
- Cari bagian `CONFIGURATION CONSTANTS`
- Ubah nilai yang diinginkan
- Simpan file

### 2. **Restart Script**
- Stop script dengan `Ctrl+C`
- Jalankan ulang: `python scrape_windows.py`

## ⚠️ Tips & Warnings

### ✅ **Best Practices**
- Gunakan `CYCLE_SECONDS = 30` untuk production
- Set `SHOW_BROWSER = False` untuk server
- Gunakan mode `'auto'` untuk stabilitas

### ⚠️ **Perhatian**
- Jangan set `CYCLE_SECONDS` terlalu rendah (< 5 detik)
- Waktu tunggu terlalu pendek bisa menyebabkan error
- Monitor penggunaan RAM dan CPU

### 🚫 **Yang Tidak Bisa Diubah via CLI Lagi**
- `--cycle-seconds`
- `--show-browser`
- `--post-open-wait-mode`
- `--post-open-wait-ms-ig`
- `--post-open-wait-ms-tiktok`

## 📈 Monitoring & Logs

Script akan menampilkan:
- Header dengan konfigurasi saat ini
- Progress monitoring untuk setiap user
- Summary setiap cycle
- Memory usage statistics
- Countdown timer untuk cycle berikutnya

## 🗄️ Database

Data tersimpan ke MongoDB Cloud:
- Collection: `stats`
- Cycle type: `{CYCLE_SECONDS}sec` (dinamis)
- Data: followers + posts untuk setiap user

## 🆘 Troubleshooting

### **Error: "Module not found"**
```bash
pip install playwright pymongo psutil pytz
playwright install
```

### **Error: "MongoDB connection failed"**
- Cek koneksi internet
- Pastikan URI MongoDB benar
- Cek firewall/antivirus

### **Error: "Browser launch failed"**
- Restart komputer
- Cek antivirus
- Update Playwright: `playwright install`

### **Performance Issues**
- Kurangi `CYCLE_SECONDS`
- Set `SHOW_BROWSER = False`
- Cek penggunaan RAM/CPU

## 📝 Changelog

### **v2.0 - Constants Only**
- ✅ Semua konfigurasi sekarang konstanta
- ✅ Tidak perlu CLI arguments
- ✅ Tidak perlu environment variables
- ✅ Konfigurasi lebih mudah dan jelas
- ✅ Dokumentasi lengkap

### **v1.x - CLI Arguments**
- ❌ Perlu CLI arguments
- ❌ Perlu environment variables
- ❌ Konfigurasi lebih rumit

---

**🎯 Kesimpulan**: Script sekarang lebih mudah digunakan! Cukup edit konstanta di file dan jalankan. Tidak perlu lagi mengingat CLI arguments yang panjang.
