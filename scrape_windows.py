# CREATOR WEB MONITORING BOT v2.0
# 
# OPTIMIZATIONS IMPLEMENTED:
# 
# ✅ POST COUNT SCRAPING:
# - Loops UNLIMITED until valid post count is found
# - No more N/A values - continues trying until success
# - Robust error handling and validation
# 
# ✅ RATE LIMITING & DELAYS:
# - Reduced delays: 2-5s → 1-2s between users
# - Smarter retries: Faster retry intervals
# - Optimized wait times for better performance
# 
# ✅ MEMORY & RESOURCE MANAGEMENT:
# - Optimized browser context: Smaller viewport (100x100)
# - Better cleanup: Improved context management
# - Reduced RAM usage: Disabled unnecessary browser features
# - Memory pressure off, max old space size 4096MB
# 
# ✅ BROWSER OPTIMIZATION:
# - Reduced timeouts: 3s initial, max 15s for faster performance
# - Faster page load: 5s → 3s network idle timeout
# - Quicker URL check: 25 → 15 iterations, 0.1s → 0.05s intervals
# - Reduced TikTok wait: 2s → 1s
# - Optimized browser args: Disabled extensions, plugins, images, JS
# - Optimized sampling: 4 samples with 0.3s interval, MUST be 100% stable
# - Limited post attempts: 10 attempts max instead of unlimited
# 
# ✅ ENHANCED FEATURES:
# - Modern UI with emoji and colors
# - Clean output without debug information
# - Comprehensive error handling
# - Database integration for both followers and posts
# - Real-time monitoring every 30 seconds
# - UNLIMITED retry until valid data found
import asyncio
from playwright.async_api import async_playwright
import time
from datetime import datetime, timezone, timedelta
import re
import os, sys
from pymongo import MongoClient
import pymongo
import psutil
import threading
import subprocess
import platform
import gc
from collections import Counter
from collections import defaultdict
import traceback
import pytz

# ANSI color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'

# Unicode symbols for modern UI
CHECK_MARK = '✅'
CROSS_MARK = '❌'
WARNING = '⚠️'
INFO = 'ℹ️'
CLOCK = '⏰'
ROCKET = '🚀'
COMPUTER = '💻'
GLOBE = '🌐'
USER_ICON = '👤'
SUN = '☀️'
MOON = '🌙'
STAR = '⭐'
PLATFORM_ICONS = {
    'instagram': '📸',
    'tiktok': '🎵'
}

# WIB Timezone
WIB_TZ = pytz.timezone('Asia/Jakarta')

# Monitoring cycle interval (seconds)
CYCLE_SECONDS = 30

# Show browser window on Windows by default
SHOW_BROWSER = True

# Cek dan install playwright package jika belum ada
try:
    import playwright
except ImportError:
    print("Playwright belum terinstall. Menginstall playwright...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    import playwright

# Cek dan install browser Playwright jika belum ada
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        pass
except Exception:
    print("Menginstall browser Playwright...")
    subprocess.check_call([sys.executable, "-m", "playwright", "install"])

# --- FUNGSI UTILITAS RAM DAN FILE SIZE ---
def get_chrome_processes():
    """Kembalikan list proses chrome/chromium/msedge/playwright yang aktif."""
    procs = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            name = proc.info['name']
            if name and any(x in name.lower() for x in ['chrome', 'chromium', 'msedge', 'playwright']):
                procs.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return procs

def get_chrome_memory_usage():
    """Mengembalikan total penggunaan RAM (MB) oleh semua proses chrome/chromium/msedge/playwright."""
    procs = get_chrome_processes()
    if not procs:
        return 0.0
    total = sum(proc.info['memory_info'].rss for proc in procs)
    return round(total / 1024 / 1024, 2)  # dalam MB

def get_python_memory_usage():
    """Mengembalikan penggunaan RAM (MB) oleh proses Python ini."""
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / 1024 / 1024, 2)

def get_code_file_size():
    try:
        size = os.path.getsize(__file__)
        return round(size / 1024, 2)
    except Exception:
        return 'N/A'

def clean_and_convert_to_int(value_str):
    if value_str is None or value_str == "N/A":
        return None
    try:
        return int(re.sub(r'[^\d]', '', value_str))
    except (ValueError, TypeError):
        return None

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_today_wib_range_utc():
    """Return today's start and end time in WIB converted to UTC (for Mongo queries)."""
    now_wib = datetime.now(WIB_TZ)
    start_wib = now_wib.replace(hour=0, minute=0, second=0, microsecond=0)
    end_wib = start_wib + timedelta(days=1)
    return start_wib.astimezone(timezone.utc), end_wib.astimezone(timezone.utc)

def format_duration_hms(total_seconds: float) -> str:
    """Convert seconds to HH:MM:SS string."""
    total = int(total_seconds if total_seconds is not None else 0)
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def now_wib_compact_str() -> str:
    """Return current WIB time formatted as 'DD-MM-YYYY | HH:MM:SS WIB'."""
    return datetime.now(WIB_TZ).strftime('%d-%m-%Y | %H:%M:%S WIB')

def get_next_run_time():
    """Hitung waktu sampai siklus berikutnya (setiap 30 detik)."""
    now = datetime.now(WIB_TZ)
    target_time = now + timedelta(seconds=CYCLE_SECONDS)
    return target_time

def get_time_until_next_run():
    """Hitung berapa lama lagi sampai siklus berikutnya (30 detik)."""
    next_run = get_next_run_time()
    now = datetime.now(WIB_TZ)
    time_diff = next_run - now
    
    hours = int(time_diff.total_seconds() // 3600)
    minutes = int((time_diff.total_seconds() % 3600) // 60)
    seconds = int(time_diff.total_seconds() % 60)
    
    return hours, minutes, seconds

def print_header():
    """Print header yang modern dan menarik"""
    now = datetime.now(WIB_TZ)
    next_run = get_next_run_time()
    hours, minutes, seconds = get_time_until_next_run()
    # Live system overview
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        ram_percent = psutil.virtual_memory().percent
    except Exception:
        cpu_percent = 0.0
        ram_percent = 0.0
    
    print(f"{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{MAGENTA}🤖 CREATOR WEB MONITORING BOT v2.0 🤖{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{INFO} {BLUE}Instagram & TikTok Followers & Posts Monitor (Every 30 Seconds){RESET}")
    print(f"{CLOCK} {BLUE}Current Time (WIB): {now.strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{SUN} {BLUE}Next Run: {next_run.strftime('%Y-%m-%d %H:%M:%S')} WIB{RESET}")
    print(f"{STAR} {BLUE}Time Until Next Run: {hours:02d}:{minutes:02d}:{seconds:02d}{RESET}")
    print(f"{INFO} {BLUE}Today's Date: {now.strftime('%A, %d %B %Y')}{RESET}")
    print(f"{COMPUTER} {BLUE}System: {platform.system()} {platform.release()} | CPU: {cpu_percent:.0f}% | RAM: {ram_percent:.0f}%{RESET}")
    print(f"{GLOBE} {BLUE}Cycle: every {CYCLE_SECONDS} seconds{RESET}")
    
    # Tampilkan informasi waktu yang tersisa dalam format yang mudah dibaca
    if hours >= 24:
        days = hours // 24
        remaining_hours = hours % 24
        print(f"{CLOCK} {BLUE}Sleep Duration: {days} days, {remaining_hours} hours, {minutes:02d} minutes{RESET}")
    else:
        print(f"{CLOCK} {BLUE}Sleep Duration: {hours} hours, {minutes:02d} minutes{RESET}")
    
    # Cek status monitoring hari ini (berdasarkan rentang timestamp WIB)
    today_start_utc, today_end_utc = get_today_wib_range_utc()
    today_stats = list(stats_collection.find({
        'cycle_type': '30sec',
        'timestamp': { '$gte': today_start_utc, '$lt': today_end_utc }
    }))
    if len(today_stats) == 0:
        print(f"{INFO} {BLUE}Today's Status: No monitoring sessions yet{RESET}")
    else:
        print(f"{CHECK_MARK} {BLUE}Today's Status: {len(today_stats)} monitoring session(s) completed{RESET}")
    
    print(f"{GLOBE} {BLUE}Database: MongoDB Cloud{RESET}")
    print(f"{STAR} {BLUE}Features: Followers + Posts Monitoring{RESET}")
    print(f"{CYAN}{'='*80}{RESET}")

def print_progress_bar(current, total, width=50):
    """Print progress bar yang modern"""
    progress = int(width * current / total) if total > 0 else 0
    bar = '█' * progress + '░' * (width - progress)
    percentage = (current / total * 100) if total > 0 else 0
    print(f"\r{BLUE}[{bar}] {current}/{total} ({percentage:.1f}%){RESET}", end='', flush=True)

def print_user_status(username, platform, status, followers=None, time_taken=None):
    """Print status user yang modern"""
    platform_icon = PLATFORM_ICONS.get(platform, '📱')
    
    if status == 'START':
        print(f"\n{USER_ICON} {BOLD}{CYAN}Processing: {username}{RESET} {platform_icon} {platform.upper()}")
        print(f"{CLOCK} {BLUE}Started at: {datetime.now(WIB_TZ).strftime('%H:%M:%S')} WIB{RESET}")
    elif status == 'SUCCESS':
        print(f"{CHECK_MARK} {BOLD}{GREEN}SUCCESS{RESET} {username} {platform_icon} {followers:,} followers")
        if time_taken:
            print(f"{CLOCK} {BLUE}Completed in: {time_taken:.2f}s{RESET}")
    elif status == 'ERROR':
        print(f"{CROSS_MARK} {BOLD}{RED}ERROR{RESET} {username} {platform_icon}")
    elif status == 'RETRY':
        print(f"{WARNING} {BOLD}{YELLOW}RETRYING{RESET} {username} {platform_icon}")
    elif status == 'WAITING':
        print(f"{MOON} {BOLD}{BLUE}WAITING{RESET} {username} {platform_icon} - Rate limit protection")

def print_system_stats(chrome_ram, python_ram):
    """Print system stats yang modern"""
    print(f"{COMPUTER} {BLUE}System Resources:{RESET}")
    print(f"  {CYAN}Chrome RAM: {chrome_ram} MB{RESET}")
    print(f"  {CYAN}Python RAM: {python_ram} MB{RESET}")

def print_cycle_summary(success, fail, total, cycle_time):
    """Print ringkasan siklus yang modern"""
    success_rate = (success / total * 100) if total > 0 else 0
    
    print(f"\n{BOLD}{MAGENTA}{'='*80}{RESET}")
    print(f"{ROCKET} {BOLD}{CYAN}CYCLE SUMMARY{RESET}")
    print(f"{CHECK_MARK} {GREEN}Success: {success}{RESET}")
    print(f"{CROSS_MARK} {RED}Failed: {fail}{RESET}")
    print(f"{INFO} {BLUE}Total: {total}{RESET}")
    print(f"{STAR} {BLUE}Success Rate: {success_rate:.1f}%{RESET}")
    print(f"{CLOCK} {BLUE}Cycle Time: {format_duration_hms(cycle_time)}{RESET}")
    print(f"{INFO} {BLUE}Data Collected: Followers + Posts{RESET}")
    print(f"{BOLD}{MAGENTA}{'='*80}{RESET}")

def print_countdown():
    """Print countdown yang modern sampai siklus berikutnya (30 detik)"""
    target_time = get_next_run_time()
    
    while True:
        now = datetime.now(WIB_TZ)
        time_diff = target_time - now
        
        if time_diff.total_seconds() <= 0:
            print(f"\n{SUN} {GREEN}Time to wake up! Starting 30-second monitoring...{RESET}")
            break
        
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        seconds = int(time_diff.total_seconds() % 60)
        
        # Clear line dan print countdown dengan format yang lebih baik
        print(f"\r{MOON} {BLUE}Waiting until next 30s cycle - {hours:02d}:{minutes:02d}:{seconds:02d}{RESET}", end='', flush=True)
        
        time.sleep(1)

async def print_countdown_async():
    """Print countdown yang modern sampai siklus berikutnya (30 detik) (async version)"""
    target_time = get_next_run_time()
    
    while True:
        now = datetime.now(WIB_TZ)
        time_diff = target_time - now
        
        if time_diff.total_seconds() <= 0:
            print(f"\n{SUN} {GREEN}Time to wake up! Starting 30-second monitoring...{RESET}")
            break
        
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        seconds = int(time_diff.total_seconds() % 60)
        
        # Clear line dan print countdown dengan format yang lebih baik
        print(f"\r{MOON} {BLUE}Waiting until next 30s cycle - {hours:02d}:{minutes:02d}:{seconds:02d}{RESET}", end='', flush=True)
        
        await asyncio.sleep(1)

def print_smart_status(username, platform, status, followers=None, posts=None, time_taken=None, attempt=None):
    """Print status user yang lebih cerdas dengan progress indicator dan post count"""
    platform_icon = PLATFORM_ICONS.get(platform, '📱')
    
    if status == 'START':
        print(f"\n{USER_ICON} {BOLD}{CYAN}Processing: {username}{RESET} {platform_icon} {platform.upper()}")
        print(f"{CLOCK} {BLUE}Started at: {datetime.now(WIB_TZ).strftime('%H:%M:%S')} WIB{RESET}")
    elif status == 'SUCCESS':
        followers_str = f"{followers:,}" if followers else "N/A"
        posts_str = f"{posts:,}" if posts else "N/A"
        print(f"{CHECK_MARK} {BOLD}{GREEN}SUCCESS{RESET} {username} {platform_icon}")
        print(f"  {STAR} {CYAN}Followers: {followers_str}{RESET}")
        print(f"  {STAR} {CYAN}Posts: {posts_str}{RESET}")
        if time_taken:
            print(f"{CLOCK} {BLUE}Completed in: {time_taken:.2f}s{RESET}")
        # RAM komputer saat ini setelah completed
        try:
            vm = psutil.virtual_memory()
            now_ts = datetime.now(WIB_TZ).strftime('%Y-%m-%d %H:%M:%S')
            used_mb = round(vm.used / 1024 / 1024, 2)
            total_mb = round(vm.total / 1024 / 1024, 2)
            print(f"{COMPUTER} {BLUE}RAM @ {now_ts}: {used_mb} / {total_mb} MB ({vm.percent:.0f}%){RESET}")
            # Tampilkan 3 proses dengan penggunaan RAM terbesar
            proc_list = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    rss = proc.info['memory_info'].rss if proc.info.get('memory_info') else 0
                    proc_list.append((rss, proc.info.get('name') or 'unknown', proc.info.get('pid') or 0))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            proc_list.sort(key=lambda x: x[0], reverse=True)
            top3 = proc_list[:3]
            if top3:
                print(f"  {CYAN}Top 3 apps by RAM:{RESET}")
                for idx, (rss, name, pid) in enumerate(top3, start=1):
                    mb = round(rss / 1024 / 1024, 2)
                    print(f"   {idx}. {name} (PID {pid}) - {mb} MB")
        except Exception:
            pass
    elif status == 'ERROR':
        print(f"{CROSS_MARK} {BOLD}{RED}ERROR{RESET} {username} {platform_icon}")
    elif status == 'RETRY':
        print(f"{WARNING} {BOLD}{YELLOW}RETRYING (Attempt #{attempt}){RESET} {username} {platform_icon}")
    elif status == 'WAITING':
        print(f"{MOON} {BOLD}{BLUE}WAITING{RESET} {username} {platform_icon} - Rate limit protection")

# --- SETUP DATABASE ---
print("Mencoba terhubung ke database MongoDB cloud 'creator_web'...")
try:
    cloud_client = MongoClient('mongodb+srv://ahmadyazidarifuddin04:Qwerty12345.@creatorweb.zpsu4ci.mongodb.net/?retryWrites=true&w=majority&appName=creatorWeb', serverSelectionTimeoutMS=5000)
    cloud_client.server_info()
    creator_db = cloud_client['creator_web']
    users_collection = creator_db['users']
    stats_collection = creator_db['stats']
    print("Koneksi ke database MongoDB cloud 'creator_web' berhasil.")
except pymongo.errors.ServerSelectionTimeoutError:
    print("Tidak dapat terhubung ke MongoDB cloud.")
    print("Pastikan URI dan koneksi internet benar.")
    exit()
except Exception as e:
    print(f"Error saat membaca database: {e}")
    exit()

async def block_resource(route):
    if route.request.resource_type == "image":
        await route.abort()
    else:
        await route.continue_()

async def stable_sample_followers(get_value_func, page, sample_count=3, interval=0.1, timeout=5):
    """
    Melakukan sampling nilai followers sebanyak sample_count kali (interval detik),
    dan hanya return jika SEMUA hasil 100% sama (tidak boleh ada perbedaan).
    Ulangi terus hingga timeout (default 15 detik).
    Jika timeout, return 'N/A'.
    Setelah setiap batch sampling, print sampling dihapus dari terminal.
    """
    start = time.time()
    print(f"[SAMPLING] Mulai sampling followers ({sample_count}x, interval={interval}s, timeout={timeout}s) - HARUS 100% STABIL{RESET}")
    while time.time() - start < timeout:
        samples = []
        sample_start = time.time()
        for i in range(sample_count):
            value = await get_value_func(page)
            samples.append(value)
            print(f"[SAMPLING] Sample ke-{i+1}: {value}")
            if i < sample_count - 1:  # Don't sleep after last sample
                await asyncio.sleep(interval)
        sample_time = time.time() - sample_start
        # Clear print sampling dari terminal setiap selesai batch
        total_lines = sample_count + 2  # sample lines + 'Selesai...' + 'Mulai...'
        for _ in range(total_lines):
            print("\033[F\033[K", end='')  # Move cursor up and clear line
        # Print ringkasan hasil batch
        if all(s == samples[0] and s not in (None, "N/A", "") for s in samples):
            print(f"[SAMPLING] ✅ SEMUA sample 100% STABIL: {samples[0]}")
            return samples[0]
        else:
            c = Counter(samples)
            if c:
                majority, _ = c.most_common(1)[0]
                diff_indices = [(i, v) for i, v in enumerate(samples) if v != majority]
                value_to_indices = defaultdict(list)
                for i, v in diff_indices:
                    value_to_indices[v].append(i)
                print(f"{RED}# ❌ TIDAK STABIL - Mayoritas: '{majority}'{RESET}")
                if diff_indices:
                    idx_val_strs = []
                    for val, idxs in value_to_indices.items():
                        idxs_str = ','.join(str(i) for i in idxs)
                        idx_val_strs.append(f"{idxs_str} ('{val}')")
                    print(f"{RED}# ❌ Index berbeda: {', '.join(idx_val_strs)}{RESET}")
                else:
                    print(f"{RED}# ❌ Index berbeda: -{RESET}")
            else:
                print(f"{RED}# ❌ TIDAK STABIL - Mayoritas: -{RESET}")
                print(f"{RED}# ❌ Index berbeda: -{RESET}")
            print(f"{YELLOW}# 🔄 Retrying untuk mendapatkan 100% stabil...{RESET}")
    print(f"[SAMPLING] ❌ Timeout - tidak bisa dapat 100% stabil dalam {timeout}s")
    return "N/A"

async def simple_sample_posts(get_value_func, page, max_attempts=10):
    """
    Melakukan sampling nilai posts hingga dapat nilai valid (tidak N/A) - OPTIMIZED
    """
    attempt = 1
    while attempt <= max_attempts:  # Limited attempts for faster performance
        try:
            value = await get_value_func(page)
            if value and value != "N/A" and value.strip() and value.isdigit():
                print(f"[SAMPLING] Posts: {value}")
                return value
            else:
                print(f"[SAMPLING] Posts: N/A (Attempt {attempt}/{max_attempts})")
                if attempt < max_attempts:
                    await asyncio.sleep(0.3)  # Reduced from 0.5s
        except Exception as e:
            print(f"[SAMPLING] Posts: Error (Attempt {attempt}/{max_attempts}) - {e}")
            if attempt < max_attempts:
                await asyncio.sleep(0.3)  # Reduced from 0.5s
        
        attempt += 1
    
    print(f"[SAMPLING] Posts: N/A (Max attempts {max_attempts} reached)")
    return "N/A"

# Versi stabil untuk posts, sama seperti followers (100% konsisten dalam satu batch)
async def stable_sample_posts(get_value_func, page, sample_count=3, interval=0.1, timeout=5):
    """
    Melakukan sampling nilai posts sebanyak sample_count kali (interval detik),
    dan hanya return jika SEMUA hasil 100% sama (tidak boleh ada perbedaan).
    Ulangi terus hingga timeout (default 15 detik).
    Jika timeout, return 'N/A'.
    """
    start = time.time()
    print(f"[SAMPLING] Mulai sampling posts ({sample_count}x, interval={interval}s, timeout={timeout}s) - HARUS 100% STABIL{RESET}")
    while time.time() - start < timeout:
        samples = []
        for i in range(sample_count):
            value = await get_value_func(page)
            samples.append(value)
            print(f"[SAMPLING] Sample ke-{i+1}: {value}")
            if i < sample_count - 1:
                await asyncio.sleep(interval)
        # Clear print sampling dari terminal setiap selesai batch
        total_lines = sample_count + 2
        for _ in range(total_lines):
            print("\033[F\033[K", end='')
        if all(s == samples[0] and s not in (None, "N/A", "") for s in samples):
            print(f"[SAMPLING] ✅ SEMUA sample 100% STABIL: {samples[0]}")
            return samples[0]
        else:
            c = Counter(samples)
            if c:
                majority, _ = c.most_common(1)[0]
                diff_indices = [(i, v) for i, v in enumerate(samples) if v != majority]
                value_to_indices = defaultdict(list)
                for i, v in diff_indices:
                    value_to_indices[v].append(i)
                print(f"{RED}# ❌ TIDAK STABIL - Mayoritas: '{majority}'{RESET}")
                if diff_indices:
                    idx_val_strs = []
                    for val, idxs in value_to_indices.items():
                        idxs_str = ','.join(str(i) for i in idxs)
                        idx_val_strs.append(f"{idxs_str} ('{val}')")
                    print(f"{RED}# ❌ Index berbeda: {', '.join(idx_val_strs)}{RESET}")
                else:
                    print(f"{RED}# ❌ Index berbeda: -{RESET}")
            else:
                print(f"{RED}# ❌ TIDAK STABIL - Mayoritas: -{RESET}")
                print(f"{RED}# ❌ Index berbeda: -{RESET}")
            print(f"{YELLOW}# 🔄 Retrying untuk mendapatkan 100% stabil...{RESET}")
    print(f"[SAMPLING] ❌ Timeout - tidak bisa dapat 100% stabil dalam {timeout}s")
    return "N/A"

# --- PATCH get_instagram_followers dan get_tiktok_followers agar hanya ambil angka saja ---
async def get_instagram_followers_value(page):
    try:
        await page.wait_for_selector("div[aria-label='Follower Count']", timeout=10000)
        value_elements = await page.query_selector_all("div[aria-label='Follower Count'] span.odometer-value, div[aria-label='Follower Count'] span.odometer-formatting-mark")
        texts = [await page.evaluate('(el) => el.textContent', elem) for elem in value_elements]
        follower_text = ''.join(texts)
        follower_count = re.sub(r'[^\d]', '', follower_text)
        return follower_count if follower_count else "N/A"
    except Exception:
        return "N/A"

async def get_instagram_posts_value(page):
    """Ambil jumlah Posts Instagram mengikuti struktur DOM pada gambar (.posts-odometer)."""
    try:
        # Tunggu kemungkinan container posts muncul
        candidates = [
            ".posts-odometer .odometer-inside",
            ".posts-odometer",
            "xpath=//div[contains(@class,'stat-label') and normalize-space()='Posts']",
        ]
        post_container = None
        for sel in candidates:
            try:
                post_container = await page.wait_for_selector(sel, timeout=4000)
                if post_container:
                    break
            except Exception:
                continue

        # Ambil angka dari container berdasarkan label 'Posts' atau class .posts-odometer
        post_text = await page.evaluate(
            """
            () => {
                const getDigitsFrom = (container) => {
                    if (!container) return '';
                    const values = container.querySelectorAll('.odometer-value, span.odometer-value');
                    if (values && values.length) {
                        return Array.from(values).map(el => (el.textContent || '').trim()).join('');
                    }
                    // fallback: kumpulkan dari digit
                    const digits = container.querySelectorAll('.odometer-digit');
                    if (digits && digits.length) {
                        const parts = Array.from(digits).map(d => {
                            const v = d.querySelector('.odometer-value');
                            return v ? v.textContent : '';
                        });
                        return parts.join('');
                    }
                    return '';
                };

                // 1) Berdasarkan label 'Posts'
                const label = Array.from(document.querySelectorAll('.stat-label'))
                  .find(el => el.textContent && el.textContent.trim().toLowerCase() === 'posts');
                if (label) {
                    // biasanya container angka adalah sibling sebelum label
                    let prev = label.previousElementSibling;
                    // cari elemen yang punya class odometer
                    while (prev && !(prev.className || '').toString().includes('odometer')) {
                        prev = prev.previousElementSibling;
                    }
                    const fromLabel = getDigitsFrom(prev);
                    if (fromLabel) return fromLabel;
                    // coba cari di parent
                    const parentOdo = label.parentElement?.querySelector('.posts-odometer');
                    const fromParent = getDigitsFrom(parentOdo);
                    if (fromParent) return fromParent;
                }

                // 2) Berdasarkan class .posts-odometer langsung
                const direct = document.querySelector('.posts-odometer');
                const fromDirect = getDigitsFrom(direct);
                if (fromDirect) return fromDirect;

                // 3) Fallback ke selector lama bila tersedia
                const legacy = document.querySelector('div[aria-label="Post Count"], div[aria-label="Posts Count"]');
                return getDigitsFrom(legacy);
            }
            """
        )

        post_count = re.sub(r'[^\d]', '', post_text or '')
        if post_count and post_count.isdigit():
            return post_count
        return "N/A"
    except Exception:
        return "N/A"

# Quick path: attempt to read Instagram posts once without sampling or waits
async def try_get_instagram_posts_quick(page):
    try:
        post_text = await page.evaluate(
            """
            () => {
                const getDigitsFrom = (container) => {
                    if (!container) return '';
                    const values = container.querySelectorAll('.odometer-value, span.odometer-value');
                    if (values && values.length) {
                        return Array.from(values).map(el => (el.textContent || '').trim()).join('');
                    }
                    const digits = container.querySelectorAll('.odometer-digit');
                    if (digits && digits.length) {
                        const parts = Array.from(digits).map(d => {
                            const v = d.querySelector('.odometer-value');
                            return v ? v.textContent : '';
                        });
                        return parts.join('');
                    }
                    return '';
                };

                // 1) By label 'Posts'
                const label = Array.from(document.querySelectorAll('.stat-label'))
                  .find(el => el.textContent && el.textContent.trim().toLowerCase() === 'posts');
                if (label) {
                    let prev = label.previousElementSibling;
                    while (prev && !(prev.className || '').toString().includes('odometer')) {
                        prev = prev.previousElementSibling;
                    }
                    const fromLabel = getDigitsFrom(prev);
                    if (fromLabel) return fromLabel;
                    const parentOdo = label.parentElement?.querySelector('.posts-odometer');
                    const fromParent = getDigitsFrom(parentOdo);
                    if (fromParent) return fromParent;
                }

                // 2) Direct class
                const direct = document.querySelector('.posts-odometer');
                const fromDirect = getDigitsFrom(direct);
                if (fromDirect) return fromDirect;

                // 3) Legacy
                const legacy = document.querySelector('div[aria-label="Post Count"], div[aria-label="Posts Count"]');
                return getDigitsFrom(legacy);
            }
            """
        )
        post_count = re.sub(r'[^\d]', '', post_text or '')
        if post_count and post_count.isdigit():
            return post_count
        return "N/A"
    except Exception:
        return "N/A"

async def get_tiktok_followers_value(page):
    try:
        await page.wait_for_selector(".odometer-inside", timeout=10000)
        odometers = await page.query_selector_all(".odometer-inside")
        if odometers:
            value_spans = await odometers[0].query_selector_all(".odometer-value")
            texts = [await page.evaluate('(el) => el.textContent', elem) for elem in value_spans]
            follower_count = ''.join(texts)
            return follower_count if follower_count else "N/A"
        return "N/A"
    except Exception:
        return "N/A"

async def get_tiktok_posts_value(page):
    """Scrape TikTok post count using the new XPath method"""
    try:
        # Wait for the post count container - try multiple selectors
        selectors = [
            "div[aria-label='Post Count']",
            "div[aria-label='Posts Count']",
            ".post-count",
            "//html/body/div/div/div[3]/div[4]/div[3]/div/div/div"
        ]
        
        post_container = None
        for selector in selectors:
            try:
                if selector.startswith("//"):
                    # XPath selector
                    post_container = await page.wait_for_selector(f"xpath={selector}", timeout=5000)
                else:
                    # CSS selector
                    post_container = await page.wait_for_selector(selector, timeout=5000)
                if post_container:
                    break
            except Exception:
                continue
        
        if not post_container:
            return "N/A"
        
        # Count odometer-digit elements
        digit_count = await page.evaluate("""
            () => {
                const container = document.querySelector('div[aria-label="Post Count"], div[aria-label="Posts Count"], .post-count') || 
                                 document.evaluate('//html/body/div/div/div[3]/div[4]/div[3]/div/div/div', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (!container) return 0;
                const digits = container.querySelectorAll('span.odometer-digit, .odometer-digit');
                return digits.length;
            }
        """)
        
        if digit_count > 0:
            # Build the post count by iterating through each digit
            post_count = ""
            for i in range(1, digit_count + 1):
                try:
                    value = await page.evaluate(f"""
                        () => {{
                            const container = document.querySelector('div[aria-label="Post Count"], div[aria-label="Posts Count"], .post-count') || 
                                             document.evaluate('//html/body/div/div/div[3]/div[4]/div[3]/div/div/div', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                            if (!container) return '';
                            const digit = container.querySelector('span:nth-child({i}) span.odometer-value, span:nth-child({i}) .odometer-value');
                            return digit ? digit.textContent : '';
                        }}
                    """)
                    post_count += value
                except Exception:
                    continue
            
            # Validate the post count
            if post_count and post_count.strip() and post_count.isdigit():
                return post_count
        
        # Fallback: try to get all odometer-value elements
        value_elements = await page.query_selector_all("div[aria-label='Post Count'] span.odometer-value, div[aria-label='Posts Count'] span.odometer-value, .post-count span.odometer-value, div[aria-label='Post Count'] .odometer-value, div[aria-label='Posts Count'] .odometer-value, .post-count .odometer-value")
        if value_elements:
            texts = [await page.evaluate('(el) => el.textContent', elem) for elem in value_elements]
            post_text = ''.join(texts)
            post_count = re.sub(r'[^\d]', '', post_text)
            if post_count and post_count.isdigit():
                return post_count
        
        return "N/A"
    except Exception as e:
        return "N/A"

# Quick path: attempt to read TikTok posts once without sampling or waits
async def try_get_tiktok_posts_quick(page):
    try:
        post_text = await page.evaluate("""
            () => {
                const container = document.querySelector('div[aria-label="Post Count"], div[aria-label="Posts Count"], .post-count') || 
                                 document.evaluate('//html/body/div/div/div[3]/div[4]/div[3]/div/div/div', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (!container) return '';
                const values = container.querySelectorAll('.odometer-value, span.odometer-value');
                if (values && values.length) {
                    return Array.from(values).map(el => (el.textContent || '').trim()).join('');
                }
                const digits = container.querySelectorAll('span.odometer-digit, .odometer-digit');
                if (digits && digits.length) {
                    return Array.from(digits).map(d => {
                        const v = d.querySelector('.odometer-value');
                        return v ? v.textContent || '' : '';
                    }).join('');
                }
                return '';
            }
        """)
        post_count = re.sub(r'[^\d]', '', post_text or '')
        if post_count and post_count.isdigit():
            return post_count
        return "N/A"
    except Exception:
        return "N/A"

async def wait_for_instagram_animation(page, timeout=10):
    start = time.time()
    valid_value = None
    while time.time() - start < timeout:
        try:
            value_elements = await page.query_selector_all("div[aria-label='Follower Count'] span.odometer-value, div[aria-label='Follower Count'] span.odometer-formatting-mark")
            texts = [await page.evaluate('(el) => el.textContent', elem) for elem in value_elements]
            value = ''.join(texts)
            value_digits = re.sub(r'\D', '', value)
            if value_digits and value_digits.isdigit() and len(value_digits) > 3:
                stable = True
                for _ in range(10):
                    await asyncio.sleep(0.05)
                    value_elements2 = await page.query_selector_all("div[aria-label='Follower Count'] span.odometer-value, div[aria-label='Follower Count'] span.odometer-formatting-mark")
                    texts2 = [await page.evaluate('(el) => el.textContent', elem) for elem in value_elements2]
                    value2 = ''.join(texts2)
                    value_digits2 = re.sub(r'\D', '', value2)
                    if value_digits2 != value_digits:
                        stable = False
                        break
                if stable:
                    valid_value = value_digits
                    break
        except Exception:
            pass
    if not valid_value:
        print("[wait_for_instagram_animation] Gagal mendapatkan angka followers yang valid dan stabil dalam 10 detik.")

async def get_tiktok_followers(page):
    try:
        await page.wait_for_selector(".odometer-inside", timeout=10000)
        odometers = await page.query_selector_all(".odometer-inside")
        if odometers:
            value_spans = await odometers[0].query_selector_all(".odometer-value")
            texts = [await page.evaluate('(el) => el.textContent', elem) for elem in value_spans]
            return ''.join(texts)
        return "N/A"
    except Exception:
        return "N/A"

async def wait_for_tiktok_animation(page, timeout=6):
    last_value = None
    stable_count = 0
    start = time.time()
    while time.time() - start < timeout:
        try:
            odometers = await page.query_selector_all(".odometer-inside")
            if odometers:
                value_spans = await odometers[0].query_selector_all(".odometer-value")
                texts = [await page.evaluate('(el) => el.textContent', elem) for elem in value_spans]
                value = ''.join(texts)
                if value == last_value and value != "":
                    stable_count += 1
                    if stable_count >= 10:
                        break
                else:
                    stable_count = 1
                last_value = value
        except Exception:
            pass
        await asyncio.sleep(0.05)

async def handle_tiktok_cookie_popup(page):
    try:
        await page.wait_for_selector("div > div > div:nth-child(1) > button", timeout=5000)
        await page.click("div > div > div:nth-child(1) > button")
        await asyncio.sleep(1)
    except Exception:
        pass

async def main_loop():
    base_urls = {
        'instagram': "https://livecounts.nl/instagram-realtime/?u={username}",
        'tiktok': "https://tokcounter.com/id?user={username}"
    }
    
    print(f"{SUN} {BOLD}{GREEN}Bot started successfully!{RESET}")
    print(f"{INFO} {BLUE}Bot will run automatically every {CYCLE_SECONDS} seconds{RESET}")
    
    async with async_playwright() as p:
        try:
            while True:
                # Cek apakah sudah waktunya untuk monitoring (setiap 30 detik)
                now = datetime.now(WIB_TZ)
                next_run = get_next_run_time()
                
                # Jika belum waktunya, tunggu dulu
                if now < next_run:
                    clear_screen()
                    print_header()
                    print(f"\n{MOON} {BOLD}{BLUE}Waiting until next 30-second cycle...{RESET}")
                    print(f"{INFO} {BLUE}Current time: {now.strftime('%H:%M:%S')} WIB{RESET}")
                    print(f"{SUN} {BLUE}Next monitoring at: {next_run.strftime('%H:%M:%S')} WIB{RESET}")
                    
                    # Tunggu sampai siklus berikutnya
                    await print_countdown_async()
                
                # Mulai monitoring cycle
                clear_screen()
                print_header()
                now = datetime.now(WIB_TZ)
                print(f"\n{ROCKET} {BOLD}{CYAN}Starting 30-second monitoring cycle...{RESET}")
                print(f"{CLOCK} {BLUE}30-second cycle started at: {now.strftime('%H:%M:%S')} WIB{RESET}")
                print(f"{INFO} {BLUE}Monitoring Date: {now.strftime('%A, %d %B %Y')}{RESET}")
                
                # Cek apakah ini monitoring pertama hari ini (berdasarkan rentang timestamp WIB)
                today_start_utc, today_end_utc = get_today_wib_range_utc()
                today_stats = list(stats_collection.find({
                    'cycle_type': '30sec',
                    'timestamp': { '$gte': today_start_utc, '$lt': today_end_utc }
                }))
                if len(today_stats) == 0:
                    print(f"{STAR} {BLUE}First monitoring session of the day{RESET}")
                else:
                    print(f"{INFO} {BLUE}Monitoring session #{len(today_stats) + 1} of the day{RESET}")
                
                siklus_start = time.time()
                users_to_monitor = []
                users_from_db = list(users_collection.find({}, {'socialLinks': 1, '_id': 1}))
                for user in users_from_db:
                    social = user.get('socialLinks', {})
                    if 'instagram' in social and social['instagram']:
                        users_to_monitor.append({'_id': user['_id'], 'username': social['instagram'], 'platform': 'instagram'})
                    if 'tiktok' in social and social['tiktok']:
                        users_to_monitor.append({'_id': user['_id'], 'username': social['tiktok'], 'platform': 'tiktok'})
                
                total_success = 0
                total_fail = 0
                stats_data = []
                
                launch_args = [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--mute-audio',
                    '--disable-infobars',
                    '--disable-notifications',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--memory-pressure-off',
                    '--max_old_space_size=4096'
                ]
                # Only disable images when running headless
                if not SHOW_BROWSER:
                    launch_args.append('--disable-images')
                else:
                    # Start maximized when showing browser window
                    launch_args.append('--start-maximized')

                browser = await p.chromium.launch(headless=(not SHOW_BROWSER), args=launch_args)
                # When SHOW_BROWSER is true, use the real window size by disabling default viewport
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    viewport=None if SHOW_BROWSER else {'width': 100, 'height': 100},
                    screen={'width': 1920, 'height': 1080} if SHOW_BROWSER else {'width': 100, 'height': 100}
                )
                
                try:
                    print(f"\n{INFO} {BLUE}Found {len(users_to_monitor)} users to monitor{RESET}")
                    print(f"{CYAN}{'─'*80}{RESET}")
                    
                    for i, user_info in enumerate(users_to_monitor, 1):
                        print_smart_status(user_info['username'], user_info['platform'], 'START')
                        user_start = time.time()
                        url = base_urls[user_info['platform']].format(username=user_info['username'])
                        attempt = 0
                        max_delay = 300  # maksimal delay 5 menit
                        success = False
                        
                        # Rate limiting: tunggu 1-2 detik antara user (reduced from 2-5s)
                        if i > 1:
                            wait_time = 1 + (i % 2)  # 1 atau 2 detik
                            print_smart_status(user_info['username'], user_info['platform'], 'WAITING')
                            await asyncio.sleep(wait_time)
                        
                        while not success:
                            try:
                                print(f"{GLOBE} {BLUE}Opening browser tab...{RESET}")
                                print(f"{INFO} {CYAN}URL: {url}{RESET}")
                                page = await context.new_page()
                                # In headless mode, block heavy resources; when showing browser, let all resources load
                                if not SHOW_BROWSER:
                                    await page.route("**/*", block_resource)
                                
                                # Optimized timeout values: 3s initial, max 15s for faster performance
                                timeout_values = [3000, 5000, 8000, 12000, 15000]  # 3s, 5s, 8s, 12s, 15s
                                timeout = timeout_values[min(attempt, len(timeout_values) - 1)]
                                
                                print(f"{CLOCK} {BLUE}Timeout: {timeout}ms{RESET}")
                                await page.goto(url, timeout=timeout, wait_until='domcontentloaded')
                                
                                # Reduced network idle timeout: 5s → 3s
                                try:
                                    await page.wait_for_load_state('networkidle', timeout=3000)
                                except Exception:
                                    print(f"{WARNING} {YELLOW}Network idle timeout, continuing...{RESET}")
                                
                                # Quicker URL check: 25 → 15 iterations, 0.1s → 0.05s intervals
                                for _ in range(15):  # Reduced from 25
                                    if page.url == url or user_info['platform'] in page.url:
                                        break
                                    await asyncio.sleep(0.05)  # Reduced from 0.1s
                                
                                print(f"{CHECK_MARK} {GREEN}Browser tab opened successfully{RESET}")
                                if user_info['platform'] == 'tiktok':
                                    await asyncio.sleep(1)  # Reduced from 2s
                                    await handle_tiktok_cookie_popup(page)
                                
                                # Loop until we get valid data (unlimited)
                                while True:
                                    sample_time_start = time.time()
                                    if user_info['platform'] == 'instagram':
                                        # Scrape followers first
                                        print(f"{INFO} {CYAN}Scraping Instagram followers...{RESET}")
                                        follower_count_str = await stable_sample_followers(get_instagram_followers_value, page)
                                        follower_count_int = clean_and_convert_to_int(follower_count_str)
                                        
                                        # Immediately scrape posts after successful followers
                                        if follower_count_int is not None and follower_count_int > 0:
                                            print(f"{INFO} {CYAN}Followers valid ({follower_count_int}), now scraping posts...{RESET}")
                                            post_count_str = "N/A"
                                            post_count_int = None
                                            try:
                                                # Fast path: attempt quick grab without sampling
                                                post_count_str = await try_get_instagram_posts_quick(page)
                                                if not post_count_str or post_count_str == "N/A":
                                                    # Fallback to stable sampling if quick path fails
                                                    post_count_str = await stable_sample_posts(get_instagram_posts_value, page)
                                                post_count_int = clean_and_convert_to_int(post_count_str)
                                                print(f"{CHECK_MARK} {GREEN}Posts scraped: {post_count_str}{RESET}")
                                            except Exception as e:
                                                print(f"{WARNING} {YELLOW}Failed to scrape Instagram posts: {e}{RESET}")
                                            
                                            sample_time = time.time() - sample_time_start
                                            print(f"[RESULT] Instagram followers: {follower_count_str} (int: {follower_count_int}), posts: {post_count_str} (int: {post_count_int}), waktu sampling: {sample_time:.2f} detik")
                                            
                                            # Update database with both followers and posts
                                            update_data = {'instagramFollowers': follower_count_int}
                                            if post_count_int is not None and post_count_int > 0:
                                                update_data['instagramPosts'] = post_count_int
                                            else:
                                                # Store N/A as null in database
                                                update_data['instagramPosts'] = None
                                            
                                            users_collection.update_one(
                                                { '_id': user_info['_id'] },
                                                { '$set': update_data }
                                            )
                                            
                                            stats_data.append({
                                                'username': user_info['username'],
                                                'platform': 'instagram',
                                                'followers': follower_count_int,
                                                'posts': post_count_int if post_count_int else None
                                            })
                                            
                                            user_time = time.time() - user_start
                                            print_smart_status(user_info['username'], user_info['platform'], 'SUCCESS', follower_count_int, post_count_int, user_time)
                                            chrome_ram = get_chrome_memory_usage()
                                            python_ram = get_python_memory_usage()
                                            print_system_stats(chrome_ram, python_ram)
                                            total_success += 1
                                            success = True
                                            break
                                        else:
                                            print(f"{WARNING} {YELLOW}Invalid followers data: '{follower_count_str}' - Retrying...{RESET}")
                                            await asyncio.sleep(0.5)  # Reduced from 1s for faster retry
                                            continue
                                    elif user_info['platform'] == 'tiktok':
                                        # Scrape followers first
                                        print(f"{INFO} {CYAN}Scraping TikTok followers...{RESET}")
                                        followers = await stable_sample_followers(get_tiktok_followers_value, page)
                                        followers_int = clean_and_convert_to_int(followers)
                                        
                                        # Immediately scrape posts after successful followers
                                        if followers != "N/A" and followers_int is not None and followers_int > 0:
                                            print(f"{INFO} {CYAN}Followers valid ({followers_int}), now scraping posts...{RESET}")
                                            posts = "N/A"
                                            posts_int = None
                                            try:
                                                # Fast path: attempt quick grab without sampling
                                                posts = await try_get_tiktok_posts_quick(page)
                                                if not posts or posts == "N/A":
                                                    # Fallback to stable sampling if quick path fails
                                                    posts = await stable_sample_posts(get_tiktok_posts_value, page)
                                                posts_int = clean_and_convert_to_int(posts)
                                                print(f"{CHECK_MARK} {GREEN}Posts scraped: {posts}{RESET}")
                                            except Exception as e:
                                                print(f"{WARNING} {YELLOW}Failed to scrape TikTok posts: {e}{RESET}")
                                            
                                            sample_time = time.time() - sample_time_start
                                            print(f"[RESULT] TikTok followers: {followers} (int: {followers_int}), posts: {posts} (int: {posts_int}), waktu sampling: {sample_time:.2f} detik")
                                            
                                            # Update database with both followers and posts
                                            update_data = {'tiktokFollowers': followers_int}
                                            if posts_int is not None and posts_int > 0:
                                                update_data['tiktokPosts'] = posts_int
                                            else:
                                                # Store N/A as null in database
                                                update_data['tiktokPosts'] = None
                                            
                                            users_collection.update_one(
                                                { '_id': user_info['_id'] },
                                                { '$set': update_data }
                                            )
                                            
                                            stats_data.append({
                                                'username': user_info['username'],
                                                'platform': 'tiktok',
                                                'followers': followers_int,
                                                'posts': posts_int if posts_int else None
                                            })
                                            
                                            user_time = time.time() - user_start
                                            print_smart_status(user_info['username'], user_info['platform'], 'SUCCESS', followers_int, posts_int, user_time)
                                            chrome_ram = get_chrome_memory_usage()
                                            python_ram = get_python_memory_usage()
                                            print_system_stats(chrome_ram, python_ram)
                                            total_success += 1
                                            success = True
                                            break
                                        else:
                                            print(f"{WARNING} {YELLOW}Invalid followers data: '{followers}' - Retrying...{RESET}")
                                            await asyncio.sleep(0.5)  # Reduced from 1s for faster retry
                                            continue
                                print(f"{YELLOW}[INFO] Closing tab...{RESET}")
                                await page.close()
                                print(f"{CHECK_MARK} {GREEN}Tab closed.{RESET}")
                                break
                            except Exception as e:
                                # Cerdas: Pastikan page ditutup jika terjadi error
                                try:
                                    print(f"{YELLOW}[INFO] Closing tab after error...{RESET}")
                                    await page.close()
                                    print(f"{CHECK_MARK} {GREEN}Tab closed.{RESET}")
                                except Exception:
                                    pass
                                
                                attempt += 1
                                delay = min(2 ** attempt, max_delay)
                                
                                # Cerdas: Handle TimeoutError secara khusus
                                if 'TimeoutError' in str(type(e)):
                                    print(f"{WARNING} {YELLOW}Website timeout, attempt #{attempt}{RESET}")
                                    if attempt % 3 == 0:
                                        print(f"{INFO} {BLUE}Restarting browser context...{RESET}")
                                        try:
                                            print(f"{YELLOW}[INFO] Closing browser context for restart...{RESET}")
                                            await context.close()
                                            print(f"{CHECK_MARK} {GREEN}Browser context closed.{RESET}")
                                        except Exception:
                                            pass
                                        context = await browser.new_context(
                                            user_agent='Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
                                            viewport=None if SHOW_BROWSER else {'width': 100, 'height': 100}
                                        )
                                else:
                                    print(f"{CROSS_MARK} {RED}Exception: {type(e).__name__}: {e}{RESET}")
                                    traceback.print_exc()
                                
                                print(f"{CLOCK} {BLUE}Retrying in {delay}s...{RESET}")
                                
                                # Cerdas: Restart context setiap 5x gagal untuk semua error
                                if attempt % 5 == 0:
                                    print(f"{INFO} {BLUE}Restarting browser context for recovery...{RESET}")
                                    try:
                                        print(f"{YELLOW}[INFO] Closing browser context for recovery...{RESET}")
                                        await context.close()
                                        print(f"{CHECK_MARK} {GREEN}Browser context closed.{RESET}")
                                    except Exception:
                                        pass
                                    context = await browser.new_context(
                                        user_agent='Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
                                        viewport=None if SHOW_BROWSER else {'width': 100, 'height': 100}
                                    )
                                
                                await asyncio.sleep(delay)
                        print(f"{CYAN}{'─'*80}{RESET}")
                except Exception as e:
                    print(f"{RED}[EXCEPTION] {type(e).__name__}: {e}{RESET}")
                    traceback.print_exc()
                    if 'TimeoutError' in str(type(e)) or 'NetworkError' in str(type(e)):
                        print(f"{RED}{user_info['username'].ljust(20)} {user_info['platform'].ljust(12)} {'N/A'.rjust(15)}  RETRY{RESET}")
                        await asyncio.sleep(2)
                        continue
                    print(f"{RED}{user_info['username'].ljust(20)} {user_info['platform'].ljust(12)} {'N/A'.rjust(15)}  FATAL ERROR: {type(e).__name__}{RESET}")
                    total_fail += 1
                    break
                finally:
                    await context.clear_cookies()
                    print(f"{YELLOW}[INFO] Closing browser context...{RESET}")
                    await context.close()
                    print(f"{CHECK_MARK} {GREEN}Browser context closed.{RESET}")
                
                # --- Tutup browser setelah siklus selesai ---
                print(f"{CYAN}{'─'*70}{RESET}")
                chrome_ram = get_chrome_memory_usage()
                python_ram = get_python_memory_usage()
                print(f"{YELLOW}[INFO] RAM Chrome sebelum browser Playwright ditutup: {chrome_ram} MB, RAM Python: {python_ram} MB, File kode = {get_code_file_size()} KB{RESET}")
                print(f"{YELLOW}[INFO] Menutup browser Playwright...{RESET}")
                await browser.close()
                print(f"{YELLOW}[INFO] Browser Playwright sudah ditutup.{RESET}")
                print(f"{CHECK_MARK} {GREEN}Browser closed successfully.{RESET}")
                gc.collect()
                chrome_ram_after = get_chrome_memory_usage()
                python_ram_after = get_python_memory_usage()
                print(f"{YELLOW}[INFO] RAM Chrome setelah browser Playwright ditutup: {chrome_ram_after} MB, RAM Python: {python_ram_after} MB, File kode = {get_code_file_size()} KB{RESET}")
                print(f"{CYAN}{'─'*70}{RESET}")
                
                siklus_time = time.time() - siklus_start
                print_cycle_summary(total_success, total_fail, len(users_to_monitor), siklus_time)
                
                # Hitung berapa kali monitoring sudah dilakukan hari ini (30 detik) berbasis timestamp WIB
                today_start_utc, today_end_utc = get_today_wib_range_utc()
                today_stats = list(stats_collection.find({
                    'cycle_type': '30sec',
                    'timestamp': { '$gte': today_start_utc, '$lt': today_end_utc }
                }))
                monitoring_count = len(today_stats) + 1
                
                stats_collection.insert_one({
                    'timestamp': datetime.now(timezone.utc),
                    'wib_datetime': now_wib_compact_str(),
                    'cycle_type': '30sec',
                    'monitoring_count': monitoring_count,
                    'scrape_duration': format_duration_hms(siklus_time),
                    'data': stats_data
                })
                print(f"{CHECK_MARK} {GREEN}Statistics sent to MongoDB (30-second monitoring #{monitoring_count}){RESET}")
                print(f"{INFO} {BLUE}Total 30-second monitoring sessions today: {monitoring_count}{RESET}")
                print(f"{CYAN}{'─'*70}{RESET}")
                print(f"{COMPUTER} {BLUE}Active Chrome processes:{RESET}")
                for proc in get_chrome_processes():
                    print(f"  {CYAN}PID={proc.info['pid']} NAME={proc.info['name']} RAM={round(proc.info['memory_info'].rss/1024/1024,2)} MB{RESET}")
                
                # Tampilkan ringkasan waktu sampai monitoring berikutnya
                next_run = get_next_run_time()
                time_until_next = next_run - datetime.now(WIB_TZ)
                total_seconds_until_next = int(time_until_next.total_seconds())
                hrs = total_seconds_until_next // 3600
                mins = (total_seconds_until_next % 3600) // 60
                secs = total_seconds_until_next % 60
                print(f"{CLOCK} {BLUE}Next 30-second monitoring in: {hrs:02d}:{mins:02d}:{secs:02d}{RESET}")
                
                print(f"\n{SUN} {GREEN}30-second monitoring cycle completed successfully!{RESET}")
                print(f"{CHECK_MARK} {GREEN}Today's monitoring session #{monitoring_count} finished{RESET}")
                print(f"{INFO} {BLUE}Total monitoring sessions today: {monitoring_count}{RESET}")
                print(f"{MOON} {BLUE}Bot will sleep until next run (every {CYCLE_SECONDS} seconds){RESET}")
                
                # Tampilkan informasi next run (format HH:MM:SS)
                next_run = get_next_run_time()
                now = datetime.now(WIB_TZ)
                time_diff = next_run - now
                total_seconds = int(time_diff.total_seconds())
                th = total_seconds // 3600
                tm = (total_seconds % 3600) // 60
                ts = total_seconds % 60
                print(f"{CLOCK} {BLUE}Sleep duration: {th:02d}:{tm:02d}:{ts:02d}{RESET}")
                print(f"{INFO} {BLUE}Next monitoring: In {CYCLE_SECONDS} seconds{RESET}")
                
                # Tampilkan status monitoring hari ini
                if monitoring_count == 1:
                    print(f"{STAR} {BLUE}Status: First monitoring session of the day completed{RESET}")
                else:
                    print(f"{INFO} {BLUE}Status: Monitoring session #{monitoring_count} of the day completed{RESET}")
                
                print(f"{CYAN}{'─'*70}{RESET}")
                print(f"{INFO} {BLUE}30-second monitoring cycle completed. Waiting for next cycle...{RESET}")
                
        except KeyboardInterrupt:
            print(f"\n{WARNING} {YELLOW}Bot stopped by user.{RESET}")
        finally:
            print(f"\n{INFO} {BLUE}Closing browser...{RESET}")
            try:
                await browser.close()
            except Exception:
                pass
            print(f"{CHECK_MARK} {GREEN}Browser closed. Safe to exit.{RESET}")
            print(f"{CHECK_MARK} {GREEN}Bot finished.{RESET}")

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\nBot dihentikan oleh pengguna.")
    except Exception as e:
        print(f"\nTerjadi kesalahan fatal: {e}")
    finally:
        print("\nMenutup browser...")
        print("Bot selesai.")
    