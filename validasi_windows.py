import asyncio
import subprocess
import sys
import re
from typing import Optional, Tuple
from datetime import datetime
import pytz
import platform
import os
try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None

from pymongo import MongoClient
from bson import ObjectId
from playwright.async_api import async_playwright, Page


# ===== Modern UI: Colors and Icons =====
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
BOLD = '\033[1m'

CHECK_MARK = '✅'
CROSS_MARK = '❌'
WARNING = '⚠️'
INFO = 'ℹ️'
CLOCK = '⏰'
ROCKET = '🚀'
COMPUTER = '💻'
GLOBE = '🌐'
USER_ICON = '👤'
STAR = '⭐'

WIB_TZ = pytz.timezone('Asia/Jakarta')

SHOW_BROWSER = True
CYCLE_SECONDS = 5

# Output/UX controls
VERBOSE_SAMPLING = False
VERBOSE_TITLES = False
SHOW_DIFF_SUMMARY = True
VERBOSE_DIFF = False


def ensure_playwright_installed() -> None:
    try:
        import playwright  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    # Ensure browsers are installed
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        with sync_playwright() as _:
            pass
    except Exception:
        subprocess.check_call([sys.executable, "-m", "playwright", "install"])


async def read_text_safe(page: Page, xpath: str, timeout_ms: int = 8000) -> Optional[str]:
    try:
        el = await page.wait_for_selector(f"xpath={xpath}", timeout=timeout_ms)
        text = await el.text_content()
        return (text or "").strip()
    except Exception:
        return None


def now_wib() -> str:
    return datetime.now(WIB_TZ).strftime('%Y-%m-%d %H:%M:%S')


def print_header() -> None:
    print(f"{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{MAGENTA}🔎 USERNAME VALIDATION BOT{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{INFO} {BLUE}System: {platform.system()} {platform.release()}{RESET}")
    print(f"{CLOCK} {BLUE}Current Time (WIB): {now_wib()}{RESET}")
    print(f"{GLOBE} {BLUE}Targets: Instagram (Livecounts) + TikTok (TokCounter){RESET}")
    print(f"{CYAN}{'-'*80}{RESET}")


def clear_screen() -> None:
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
    except Exception:
        pass


# ===== Resource/Code Stats =====
def get_python_memory_usage_mb() -> float:
    if not psutil:
        return 0.0
    try:
        process = psutil.Process(os.getpid())
        return round(process.memory_info().rss / 1024 / 1024, 2)
    except Exception:
        return 0.0


def get_chrome_memory_usage_mb() -> float:
    if not psutil:
        return 0.0
    total = 0
    try:
        for proc in psutil.process_iter(['name', 'memory_info']):
            try:
                name = (proc.info.get('name') or '').lower()
                if any(k in name for k in ['chrome', 'chromium', 'msedge', 'playwright']):
                    mi = proc.info.get('memory_info')
                    if mi:
                        total += mi.rss
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return round(total / 1024 / 1024, 2)
    except Exception:
        return 0.0


def get_code_file_size_kb() -> float:
    try:
        size = os.path.getsize(__file__)
        return round(size / 1024, 2)
    except Exception:
        return 0.0


def print_resource_line(prefix: str = "") -> None:
    py_mb = get_python_memory_usage_mb()
    ch_mb = get_chrome_memory_usage_mb()
    code_kb = get_code_file_size_kb()
    sys_ram = None
    if psutil:
        try:
            sys_ram = psutil.virtual_memory().percent
        except Exception:
            sys_ram = None
    parts = [
        f"{COMPUTER} {BLUE}RAM Py: {py_mb} MB{RESET}",
        f"{COMPUTER} {BLUE}RAM Chrome: {ch_mb} MB{RESET}",
        f"{INFO} {BLUE}Code: {code_kb} KB{RESET}",
    ]
    if sys_ram is not None:
        parts.append(f"{INFO} {BLUE}Sys RAM: {sys_ram:.0f}%{RESET}")
    print((prefix + ' ').rstrip() + ' ' + ' | '.join(parts))


def build_user_query():
    # Include everyone except admins; support both role/roles and isAdmin boolean
    non_admin = {
        "$nor": [
            {"role": "admin"},
            {"roles": "admin"},
            {"roles": {"$in": ["admin"]}},
            {"isAdmin": True},
        ]
    }
    # Efficient fetch: only users whose platform status is explicitly 'belum'
    status_belum = {
        "$or": [
            {"instagram_validation_status": "belum"},
            {"tiktok_verification_status": "belum"},
        ]
    }
    # Must have at least one social link string present
    has_social = {
        "$or": [
            {"socialLinks.instagram": {"$exists": True, "$type": "string", "$ne": ""}},
            {"socialLinks.tiktok": {"$exists": True, "$type": "string", "$ne": ""}},
        ]
    }
    return {"$and": [non_admin, status_belum, has_social]}


def base_non_admin_has_social_query():
    non_admin = {
        "$nor": [
            {"role": "admin"},
            {"roles": "admin"},
            {"roles": {"$in": ["admin"]}},
            {"isAdmin": True},
        ]
    }
    has_social = {
        "$or": [
            {"socialLinks.instagram": {"$exists": True, "$type": "string", "$ne": ""}},
            {"socialLinks.tiktok": {"$exists": True, "$type": "string", "$ne": ""}},
        ]
    }
    return {"$and": [non_admin, has_social]}

def clean_and_convert_to_int(value_str: Optional[str]) -> Optional[int]:
    if value_str is None or value_str == "N/A":
        return None
    try:
        digits = re.sub(r"[^\d]", "", value_str)
        return int(digits) if digits else None
    except Exception:
        return None


async def stable_sample_followers(get_value_func, page: Page, sample_count: int = 3, interval: float = 0.1, timeout: float = 5.0) -> str:
    start = asyncio.get_event_loop().time()
    if VERBOSE_SAMPLING:
        print(f"[SAMPLING] Followers {sample_count}x interval={interval}s timeout={timeout}s")
    while (asyncio.get_event_loop().time() - start) < timeout:
        samples = []
        for i in range(sample_count):
            value = await get_value_func(page)
            samples.append(value)
            if VERBOSE_SAMPLING:
                print(f"[SAMPLING] #{i+1}: {value}")
            if i < sample_count - 1:
                await asyncio.sleep(interval)
        if all(s == samples[0] and s not in (None, "N/A", "") for s in samples):
            if VERBOSE_SAMPLING:
                print(f"[SAMPLING] OK stable: {samples[0]}")
            return samples[0]
        if VERBOSE_SAMPLING:
            print(f"[SAMPLING] Not stable, retry...")
    if VERBOSE_SAMPLING:
        print(f"[SAMPLING] Timeout; returning N/A")
    return "N/A"


async def get_instagram_followers_value(page: Page) -> str:
    try:
        await page.wait_for_selector("div[aria-label='Follower Count']", timeout=10000)
        value_elements = await page.query_selector_all("div[aria-label='Follower Count'] span.odometer-value, div[aria-label='Follower Count'] span.odometer-formatting-mark")
        texts = [await page.evaluate('(el) => el.textContent', elem) for elem in value_elements]
        follower_text = ''.join(texts)
        follower_count = re.sub(r'[^\d]', '', follower_text)
        return follower_count if follower_count else "N/A"
    except Exception:
        return "N/A"


async def get_tiktok_followers_value(page: Page) -> str:
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


async def stable_sample_posts(get_value_func, page: Page, sample_count: int = 3, interval: float = 0.1, timeout: float = 5.0) -> str:
    start = asyncio.get_event_loop().time()
    if VERBOSE_SAMPLING:
        print(f"[SAMPLING] Posts {sample_count}x interval={interval}s timeout={timeout}s")
    while (asyncio.get_event_loop().time() - start) < timeout:
        samples = []
        for i in range(sample_count):
            value = await get_value_func(page)
            samples.append(value)
            if VERBOSE_SAMPLING:
                print(f"[SAMPLING] #{i+1}: {value}")
            if i < sample_count - 1:
                await asyncio.sleep(interval)
        if all(s == samples[0] and s not in (None, "N/A", "") for s in samples):
            if VERBOSE_SAMPLING:
                print(f"[SAMPLING] OK stable: {samples[0]}")
            return samples[0]
        if VERBOSE_SAMPLING:
            print(f"[SAMPLING] Not stable, retry...")
    if VERBOSE_SAMPLING:
        print(f"[SAMPLING] Timeout; returning N/A")
    return "N/A"


async def get_instagram_posts_value(page: Page) -> str:
    try:
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

                const direct = document.querySelector('.posts-odometer');
                const fromDirect = getDigitsFrom(direct);
                if (fromDirect) return fromDirect;

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


async def try_get_instagram_posts_quick(page: Page) -> str:
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
                const direct = document.querySelector('.posts-odometer');
                const fromDirect = getDigitsFrom(direct);
                if (fromDirect) return fromDirect;
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


async def get_tiktok_posts_value(page: Page) -> str:
    try:
        selectors = [
            "div[aria-label='Post Count']",
            "div[aria-label='Posts Count']",
            ".post-count",
            "//html/body/div/div/div[3]/div[4]/div[3]/div/div/div",
        ]
        post_container = None
        for selector in selectors:
            try:
                if selector.startswith("//"):
                    post_container = await page.wait_for_selector(f"xpath={selector}", timeout=5000)
                else:
                    post_container = await page.wait_for_selector(selector, timeout=5000)
                if post_container:
                    break
            except Exception:
                continue
        if not post_container:
            return "N/A"
        digit_count = await page.evaluate(
            """
            () => {
                const container = document.querySelector('div[aria-label="Post Count"], div[aria-label="Posts Count"], .post-count') || 
                                 document.evaluate('//html/body/div/div/div[3]/div[4]/div[3]/div/div/div', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (!container) return 0;
                const digits = container.querySelectorAll('span.odometer-digit, .odometer-digit');
                return digits.length;
            }
            """
        )
        if digit_count > 0:
            post_count = ""
            for i in range(1, digit_count + 1):
                try:
                    value = await page.evaluate(
                        f"""
                        () => {{
                            const container = document.querySelector('div[aria-label="Post Count"], div[aria-label="Posts Count"], .post-count') || 
                                             document.evaluate('//html/body/div/div/div[3]/div[4]/div[3]/div/div/div', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                            if (!container) return '';
                            const digit = container.querySelector('span:nth-child({i}) span.odometer-value, span:nth-child({i}) .odometer-value');
                            return digit ? digit.textContent : '';
                        }}
                        """
                    )
                    post_count += value
                except Exception:
                    continue
            if post_count and post_count.strip() and post_count.isdigit():
                return post_count
        value_elements = await page.query_selector_all("div[aria-label='Post Count'] span.odometer-value, div[aria-label='Posts Count'] span.odometer-value, .post-count span.odometer-value, div[aria-label='Post Count'] .odometer-value, div[aria-label='Posts Count'] .odometer-value, .post-count .odometer-value")
        if value_elements:
            texts = [await page.evaluate('(el) => el.textContent', elem) for elem in value_elements]
            post_text = ''.join(texts)
            post_count = re.sub(r'[^\\d]', '', post_text)
            if post_count and post_count.isdigit():
                return post_count
        return "N/A"
    except Exception:
        return "N/A"


async def try_get_tiktok_posts_quick(page: Page) -> str:
    try:
        post_text = await page.evaluate(
            """
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
            """
        )
        post_count = re.sub(r'[^\d]', '', post_text or '')
        if post_count and post_count.isdigit():
            return post_count
        return "N/A"
    except Exception:
        return "N/A"


async def block_resource(route):
    if route.request.resource_type == "image":
        await route.abort()
    else:
        await route.continue_()
def normalize_username(platform: str, value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.startswith('@'):
        text = text[1:]
    # Extract from URLs if provided
    try:
        if 'instagram.com' in text:
            m = re.search(r"instagram\.com/([^/?#]+)/?", text, re.IGNORECASE)
            if m:
                text = m.group(1)
        if 'tiktok.com' in text:
            m = re.search(r"tiktok\.com/@?([^/?#]+)/?", text, re.IGNORECASE)
            if m:
                text = m.group(1)
    except Exception:
        pass
    return text or None


async def verify_instagram_username(page: Page, username: str) -> str:
    # Livecounts.nl Instagram realtime page
    url = f"https://livecounts.nl/instagram-realtime/?u={username}"
    if VERBOSE_TITLES:
        print(f"{GLOBE} {BLUE}Open: {url}{RESET}")
    await page.goto(url, timeout=15000, wait_until="domcontentloaded")
    if VERBOSE_TITLES:
        print(f"{CHECK_MARK} {GREEN}Loaded Instagram page{RESET}")
    # Attempt to get the H2 text that should equal the username, else sometimes shows 'livecounts.nl'
    xpath_title = "/html/body/div[2]/div/div/div[1]/div[2]/div[2]/h2"

    # Poll up to ~10s; determine by majority if needed
    status: Optional[str] = None
    
    def canonicalize(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (value or "").lower())

    expected = canonicalize(username)
    livecounts_key = canonicalize("livecounts.nl")
    count_live = 0
    count_non_live = 0

    for _ in range(10):  # 10 x 500ms = 5s
        text = await read_text_safe(page, xpath_title, timeout_ms=1000)
        if text:
            raw = (text or "").strip()
            canon = canonicalize(raw)
            if VERBOSE_TITLES:
                print(f"{INFO} {CYAN}Instagram title: '{raw}'{RESET}")
            # Early positive if username appears exactly/substring
            if canon == expected or (expected and expected in canon):
                status = "benar"
                break
            # Tally majority
            if canon == livecounts_key:
                count_live += 1
            elif canon:
                count_non_live += 1
        await asyncio.sleep(0.5)

    if status is None:
        # Majority rule (out of 10 samples): if non-livecounts appears more, treat as valid
        status = "benar" if count_non_live > count_live else "salah"
        print(f"{INFO} {BLUE}Majority decision — non-livecounts: {count_non_live}/10, livecounts.nl: {count_live}/10{RESET}")
    print(f"{STAR} {BLUE}Instagram validation for '{username}': {BOLD}{status.upper()}{RESET}")
    return status


async def fetch_instagram_followers(page: Page) -> Optional[int]:
    raw = await stable_sample_followers(get_instagram_followers_value, page)
    return clean_and_convert_to_int(raw)


async def handle_tiktok_cookie_popup(page: Page) -> None:
    try:
        await page.wait_for_selector("div > div > div:nth-child(1) > button", timeout=5000)
        await page.click("div > div > div:nth-child(1) > button")
        await asyncio.sleep(0.5)
    except Exception:
        pass


async def verify_tiktok_username(page: Page, username: str) -> str:
    # TokCounter Indonesian page
    url = f"https://tokcounter.com/id?user={username}"
    if VERBOSE_TITLES:
        print(f"{GLOBE} {BLUE}Open: {url}{RESET}")
    await page.goto(url, timeout=15000, wait_until="domcontentloaded")
    await handle_tiktok_cookie_popup(page)

    # Error text xpath and expected content
    xpath_error = "/html/body/div/div/div[3]/div[1]/div/p[2]"
    error_text = await read_text_safe(page, xpath_error, timeout_ms=7000)

    message_snippet = "Kami tidak dapat menemukan pengguna dengan ID ini"
    if VERBOSE_TITLES and error_text:
        print(f"{INFO} {CYAN}TokCounter message: '{error_text}'{RESET}")
    if error_text and message_snippet.lower() in error_text.lower():
        print(f"{STAR} {BLUE}TikTok validation for '{username}': {BOLD}SALAH{RESET}")
        return "salah"
    print(f"{STAR} {BLUE}TikTok validation for '{username}': {BOLD}BENAR{RESET}")
    return "benar"


async def fetch_tiktok_followers(page: Page) -> Optional[int]:
    raw = await stable_sample_followers(get_tiktok_followers_value, page)
    return clean_and_convert_to_int(raw)


async def main() -> None:
    ensure_playwright_installed()

    print_header()
    # Connect to MongoDB Cloud
    print(f"{INFO} {BLUE}Connecting MongoDB Cloud: creator_web.users{RESET}")
    mongo_client = MongoClient('mongodb+srv://ahmadyazidarifuddin04:Qwerty12345.@creatorweb.zpsu4ci.mongodb.net/?retryWrites=true&w=majority&appName=creatorWeb', serverSelectionTimeoutMS=5000)
    db = mongo_client["creator_web"]
    users = db["users"]
    print(f"{CHECK_MARK} {GREEN}Database connected (cloud){RESET}")

    # Continuous processing loop to catch new/updated users
    cycle = 0

    async with async_playwright() as p:
        clear_screen()
        print_header()
        print_resource_line(prefix="")
        print(f"{ROCKET} {CYAN}Launching browser (visible={SHOW_BROWSER})...{RESET}")
        # Fast, efficient context similar to scrape_windows.py
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
            '--max_old_space_size=4096',
            '--start-maximized'
        ]
        browser = await p.chromium.launch(headless=not SHOW_BROWSER, args=launch_args)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            viewport=None
        )
        print(f"{CHECK_MARK} {GREEN}Browser ready{RESET}")

        try:
            prev_usernames: dict = {}
            while True:
                cycle += 1
                # Modern rolling display per cycle
                clear_screen()
                print_header()
                print_resource_line(prefix="")
                query = build_user_query()
                projection = {
                    "socialLinks": 1,
                    "role": 1,
                    "roles": 1,
                    "isAdmin": 1,
                    "instagram_validation_status": 1,
                    "tiktok_verification_status": 1,
                    "instagram_last_validated_username": 1,
                    "tiktok_last_validated_username": 1,
                }
                user_docs = list(users.find(query, projection))
                print(f"{INFO} {BLUE}Cycle #{cycle}: {len(user_docs)} user(s) loaded for evaluation{RESET}")

                # Build current snapshot of usernames for change detection (always)
                curr_usernames: dict = {}
                baseline_query = base_non_admin_has_social_query()
                baseline_projection = {"socialLinks": 1}
                try:
                    baseline_docs = list(users.find(baseline_query, baseline_projection))
                    for d in baseline_docs:
                        sid = str(d.get("_id"))
                        s = (d.get("socialLinks") or {})
                        curr_usernames[sid] = {
                            "ig": normalize_username("instagram", s.get("instagram")),
                            "tt": normalize_username("tiktok", s.get("tiktok")),
                        }
                except Exception:
                    curr_usernames = {}

                # Compare with previous snapshot to force validation on username changes (track per-platform)
                force_users: set = set()
                force_ig_users: set = set()
                force_tt_users: set = set()
                for sid, names in curr_usernames.items():
                    prev = prev_usernames.get(sid)
                    if prev is None:
                        # new user; handled by 'belum' filter typically, but keep record
                        continue
                    ig_changed = bool(names.get("ig") and prev.get("ig") and names.get("ig") != prev.get("ig"))
                    tt_changed = bool(names.get("tt") and prev.get("tt") and names.get("tt") != prev.get("tt"))
                    if ig_changed or tt_changed:
                        force_users.add(sid)
                        if ig_changed:
                            force_ig_users.add(sid)
                        if tt_changed:
                            force_tt_users.add(sid)

                # Diff summary for monitoring (always show once per cycle)
                if SHOW_DIFF_SUMMARY:
                    prev_keys = set(prev_usernames.keys())
                    curr_keys = set(curr_usernames.keys())
                    new_users = curr_keys - prev_keys
                    gone_users = prev_keys - curr_keys
                    ig_changed_list = []
                    tt_changed_list = []
                    for sid in curr_keys & prev_keys:
                        p = prev_usernames.get(sid) or {}
                        c = curr_usernames.get(sid) or {}
                        if p.get('ig') and c.get('ig') and p.get('ig') != c.get('ig'):
                            ig_changed_list.append((sid, p.get('ig'), c.get('ig')))
                        if p.get('tt') and c.get('tt') and p.get('tt') != c.get('tt'):
                            tt_changed_list.append((sid, p.get('tt'), c.get('tt')))
                    print(f"{INFO} {BLUE}Snapshot users → prev:{len(prev_usernames)} curr:{len(curr_usernames)} | new:{len(new_users)} gone:{len(gone_users)} | IG changed:{len(ig_changed_list)} TT changed:{len(tt_changed_list)}{RESET}")
                    if VERBOSE_DIFF:
                        max_show = 5
                        if new_users:
                            print(f"  {INFO} {BLUE}New users (showing up to {max_show}):{RESET}")
                            for sid in list(new_users)[:max_show]:
                                print(f"   - {sid}: ig={curr_usernames.get(sid,{}).get('ig')} tt={curr_usernames.get(sid,{}).get('tt')}")
                        if gone_users:
                            print(f"  {INFO} {BLUE}Gone users (up to {max_show}):{RESET}")
                            for sid in list(gone_users)[:max_show]:
                                print(f"   - {sid}")
                        if ig_changed_list:
                            print(f"  {INFO} {BLUE}IG changed (up to {max_show}):{RESET}")
                            for sid, old, new in ig_changed_list[:max_show]:
                                print(f"   - {sid}: {old} → {new}")
                        if tt_changed_list:
                            print(f"  {INFO} {BLUE}TT changed (up to {max_show}):{RESET}")
                            for sid, old, new in tt_changed_list[:max_show]:
                                print(f"   - {sid}: {old} → {new}")

                # Decide which users to validate this cycle: statuses 'belum' plus changed/new usernames
                ig_benar = ig_salah = 0
                tt_benar = tt_salah = 0
                ig_failed_usernames = []
                tt_failed_usernames = []

                # User IDs from DB status filter
                status_ids = set(str(doc.get('_id')) for doc in user_docs)
                # Changed/new IDs from snapshot diff
                prev_keys = set(prev_usernames.keys())
                curr_keys = set(curr_usernames.keys())
                new_users = curr_keys - prev_keys
                changed_ids = set(force_users)
                target_ids = status_ids | new_users | changed_ids

                if not target_ids:
                    print(f"{INFO} {BLUE}No pending users. Sleeping {CYCLE_SECONDS}s...{RESET}")
                    prev_usernames = curr_usernames
                    await asyncio.sleep(CYCLE_SECONDS)
                    continue

                # Fetch only targets for this cycle
                try:
                    target_oid = [ObjectId(s) for s in target_ids]
                    user_docs = list(users.find({'_id': {'$in': target_oid}}, projection))
                    print(f"{INFO} {BLUE}Will validate {len(user_docs)} user(s) this cycle (status 'belum' + changed/new){RESET}")
                except Exception:
                    pass

                for idx, doc in enumerate(user_docs, start=1):
                    social = (doc or {}).get("socialLinks", {}) or {}
                    user_id = doc.get("_id")
                    user_id_str = str(user_id) if user_id is not None else ""
                    role = doc.get("role")
                    roles = doc.get("roles")
                    print(f"\n{INFO} {BLUE}[{idx}] User {user_id_str} role={role} roles={roles} social={social}{RESET}")

                    # Determine whether this user needs IG or TikTok validation this cycle (defensive server-side filter is already applied: status == 'belum')
                    raw_ig = social.get("instagram")
                    raw_tt = social.get("tiktok")
                    ig_status_prev = doc.get("instagram_validation_status")
                    tt_status_prev = doc.get("tiktok_verification_status")

                    # Default needs: only when explicit 'belum'
                    need_ig = (str(ig_status_prev).lower() == "belum")
                    need_tt = (str(tt_status_prev).lower() == "belum")

                    # Force only the platform(s) that changed usernames between cycles
                    sid = user_id_str
                    if sid in force_ig_users and normalize_username("instagram", raw_ig or ""):
                        need_ig = True
                    if sid in force_tt_users and normalize_username("tiktok", raw_tt or ""):
                        need_tt = True
                    if raw_ig and normalize_username("instagram", raw_ig):
                        if not ig_status_prev or str(ig_status_prev).lower() in ("", "none", "belum"):
                            need_ig = True
                    if raw_tt and normalize_username("tiktok", raw_tt):
                        if not tt_status_prev or str(tt_status_prev).lower() in ("", "none", "belum"):
                            need_tt = True

                    # If both statuses are missing and there is at least one social link, force evaluation
                    if (not ig_status_prev and raw_ig) or (not tt_status_prev and raw_tt):
                        need_ig = need_ig or bool(raw_ig)
                        need_tt = need_tt or bool(raw_tt)

                    if not need_ig and not need_tt:
                        print(f"{INFO} {BLUE}No 'belum' status for user {user_id_str}; skipping{RESET}")
                        continue

                    # Instagram verification
                    raw_ig = social.get("instagram")
                    ig_username = normalize_username("instagram", raw_ig)
                    if need_ig and ig_username:
                        print(f"\n{USER_ICON} {BOLD}{CYAN}[{idx}] Validating Instagram: {ig_username}{RESET}")
                        page = await context.new_page()
                        try:
                            ig_status = await verify_instagram_username(page, ig_username)
                            followers_int: Optional[int] = None
                            posts_int: Optional[int] = None
                            if ig_status == "benar":
                                # Also fetch followers when valid
                                followers_int = await fetch_instagram_followers(page)
                                print(f"{INFO} {BLUE}Instagram followers: {followers_int if followers_int is not None else 'N/A'}{RESET}")
                                # Posts fast path then stable if needed
                                posts_str = await try_get_instagram_posts_quick(page)
                                if not posts_str or posts_str == "N/A":
                                    posts_str = await stable_sample_posts(get_instagram_posts_value, page)
                                posts_int = clean_and_convert_to_int(posts_str)
                                print(f"{INFO} {BLUE}Instagram posts: {posts_int if posts_int is not None else 'N/A'}{RESET}")
                            update_data = {"instagram_validation_status": ig_status}
                            if followers_int is not None:
                                update_data["instagramFollowers"] = followers_int
                            if ig_status == "benar" and posts_int is not None:
                                update_data["instagramPosts"] = posts_int
                            users.update_one({"_id": user_id}, {"$set": update_data})
                            if ig_status == "benar":
                                ig_benar += 1
                            else:
                                ig_salah += 1
                                ig_failed_usernames.append(ig_username)
                            print(f"{CHECK_MARK} {GREEN}Updated DB instagram_validation_status → {ig_status}{RESET}")
                        except Exception as e:
                            print(f"{CROSS_MARK} {RED}Instagram validation error: {type(e).__name__}: {e}{RESET}")
                        finally:
                            await page.close()
                    else:
                        print(f"{WARNING} {YELLOW}Skip Instagram: username not found for user {user_id_str}{RESET}")

                    # TikTok verification
                    raw_tt = social.get("tiktok")
                    tt_username = normalize_username("tiktok", raw_tt)
                    if need_tt and tt_username:
                        print(f"\n{USER_ICON} {BOLD}{CYAN}[{idx}] Validating TikTok: {tt_username}{RESET}")
                        page = await context.new_page()
                        try:
                            tt_status = await verify_tiktok_username(page, tt_username)
                            followers_int: Optional[int] = None
                            posts_int: Optional[int] = None
                            if tt_status == "benar":
                                followers_int = await fetch_tiktok_followers(page)
                                print(f"{INFO} {BLUE}TikTok followers: {followers_int if followers_int is not None else 'N/A'}{RESET}")
                                # Posts fast path then stable if needed
                                posts_str = await try_get_tiktok_posts_quick(page)
                                if not posts_str or posts_str == "N/A":
                                    posts_str = await stable_sample_posts(get_tiktok_posts_value, page)
                                posts_int = clean_and_convert_to_int(posts_str)
                                print(f"{INFO} {BLUE}TikTok posts: {posts_int if posts_int is not None else 'N/A'}{RESET}")
                            update_data = {"tiktok_verification_status": tt_status}
                            if followers_int is not None:
                                update_data["tiktokFollowers"] = followers_int
                            if tt_status == "benar" and posts_int is not None:
                                update_data["tiktokPosts"] = posts_int
                            users.update_one({"_id": user_id}, {"$set": update_data})
                            if tt_status == "benar":
                                tt_benar += 1
                            else:
                                tt_salah += 1
                                tt_failed_usernames.append(tt_username)
                            print(f"{CHECK_MARK} {GREEN}Updated DB tiktok_verification_status → {tt_status}{RESET}")
                        except Exception as e:
                            print(f"{CROSS_MARK} {RED}TikTok validation error: {type(e).__name__}: {e}{RESET}")
                        finally:
                            await page.close()
                    else:
                        print(f"{WARNING} {YELLOW}Skip TikTok: username not found for user {user_id_str}{RESET}")

                # End-of-cycle summary and sleep
                print(f"\n{BOLD}{CYAN}{'-'*80}{RESET}")
                print(f"{STAR} {BLUE}Instagram → benar: {ig_benar}, salah: {ig_salah}{RESET}")
                if ig_failed_usernames:
                    print(f"  {YELLOW}Instagram salah list:{RESET}")
                    for name in ig_failed_usernames[:5]:
                        print(f"   - {name}")
                    if len(ig_failed_usernames) > 5:
                        print(f"   … +{len(ig_failed_usernames)-5} more")
                print(f"{STAR} {BLUE}TikTok    → benar: {tt_benar}, salah: {tt_salah}{RESET}")
                if tt_failed_usernames:
                    print(f"  {YELLOW}TikTok salah list:{RESET}")
                    for name in tt_failed_usernames[:5]:
                        print(f"   - {name}")
                    if len(tt_failed_usernames) > 5:
                        print(f"   … +{len(tt_failed_usernames)-5} more")
                print(f"{BOLD}{CYAN}{'-'*80}{RESET}")
                print_resource_line(prefix="")
                print(f"{INFO} {BLUE}Sleeping {CYCLE_SECONDS}s and watching for new/updated users...{RESET}")
                # Reset previous snapshot to free memory and store current for next cycle
                prev_usernames = curr_usernames
                await asyncio.sleep(CYCLE_SECONDS)
        finally:
            print(f"\n{INFO} {BLUE}Closing browser...{RESET}")
            await context.close()
            await browser.close()
            print(f"{CHECK_MARK} {GREEN}Done{RESET}")


if __name__ == "__main__":
    asyncio.run(main())


