import os
import re
import urllib.request

SOURCES_FILE = "sources.txt"
OUTPUT_DIR = "Sumber Gratis"
SELECT_FILE = "chanel_pilihan.txt"
CUSTOM_PLAYLIST = "ZeroTVGRATIS.m3u"

# Link streaming permanen Anda di urutan teratas
PERMANENT_STREAM_URL = "https://raw.githubusercontent.com/zerofeed-id/WELCOME/refs/heads/main/ZeroTV_Tele.ts"

GITHUB_TOKEN = os.environ.get("GH_PAT", "")

def fetch_url_content(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    target_url = url

    if "githubusercontent.com" in url and GITHUB_TOKEN:
        parts = url.replace("https://raw.githubusercontent.com/", "").split("/")
        if len(parts) >= 3:
            owner = parts[0]
            repo = parts[1]
            path = "/".join(parts[3:])
            target_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
            headers['Accept'] = 'application/vnd.github.v3.raw'
            headers['Authorization'] = f"token {GITHUB_TOKEN}"
    elif "github.com" in url and GITHUB_TOKEN and "api.github.com" not in url:
        headers['Authorization'] = f"token {GITHUB_TOKEN}"

    req = urllib.request.Request(target_url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read().decode('utf-8', errors='ignore')

def normalize_name(name):
    """Fungsi untuk membersihkan teks agar pencocokan lebih fleksibel (mengabaikan spasi, simbol, dan huruf besar/kecil)"""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def parse_and_split_m3u():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    if not os.path.exists(SOURCES_FILE):
        print(f"File {SOURCES_FILE} tidak ditemukan!")
        return

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        source_urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not source_urls:
        print("Tidak ada link sumber yang ditemukan di sources.txt")
        return

    channels = {}
    normalized_channels = {}

    for url_idx, source_url in enumerate(source_urls, 1):
        print(f"Mengambil data dari URL ke-{url_idx}: {source_url}")
        try:
            content = fetch_url_content(source_url)
        except Exception as e:
            print(f"GAGAL mengambil data dari URL {source_url}: {e}")
            continue

        lines = content.splitlines()
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("#EXTINF:"):
                extinf_line = line
                
                match = re.search(r',([^,]+)$', extinf_line)
                raw_name = match.group(1).strip() if match else "Unknown"
                clean_name = re.sub(r'\.\d+[A-Z]+$', '', raw_name)
                safe_name = re.sub(r'[\\/*?:"<>|]', "", clean_name).strip().replace(" ", "_")
                if not safe_name:
                    safe_name = "Unknown"

                block_lines = [extinf_line]
                i += 1
                
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith("#EXTINF:") or next_line.startswith("#EXTM3U"):
                        i -= 1
                        break
                    if next_line:
                        block_lines.append(next_line)
                    i += 1

                if safe_name not in channels:
                    channels[safe_name] = []
                channels[safe_name].append(block_lines)
                
                norm_key = normalize_name(safe_name)
                if norm_key not in normalized_channels:
                    normalized_channels[norm_key] = []
                normalized_channels[norm_key].append(block_lines)
            i += 1

    # Hapus otomatis file .m3u di folder Sumber Gratis jika channel sudah tidak ada di sumber
    current_channel_files = {f"{channel_name}.m3u" for channel_name in channels.keys()}
    if os.path.exists(OUTPUT_DIR):
        for existing_file in os.listdir(OUTPUT_DIR):
            if existing_file.endswith(".m3u"):
                if existing_file not in current_channel_files:
                    old_file_path = os.path.join(OUTPUT_DIR, existing_file)
                    try:
                        os.remove(old_file_path)
                        print(f"File channel kedaluwarsa dihapus: {existing_file}")
                    except Exception as e:
                        print(f"Gagal menghapus file {existing_file}: {e}")

    # 1. Simpan file M3U terpisah per channel di folder Sumber Gratis
    for channel_name, entries in channels.items():
        file_path = os.path.join(OUTPUT_DIR, f"{channel_name}.m3u")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for block in entries:
                for bline in block:
                    f.write(f"{bline}\n")

    # 2. Buat playlist gabungan dengan sistem Exclude (Pengecualian) berdasarkan chanel_pilihan.txt
    excluded_patterns = []
    if os.path.exists(SELECT_FILE):
        with open(SELECT_FILE, "r", encoding="utf-8") as f:
            excluded_patterns = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    with open(CUSTOM_PLAYLIST, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        # --- PENYEMATAN CHANNEL PERMANEN KE BARIS TERATAS ---
        try:
            f.write('#EXTINF:-1 tvg-id="ZeroTV" tvg-name="ZeroTV" group-title="ZeroTV Official",ZeroTV Special\n')
            f.write(PERMANENT_STREAM_URL + "\n")
            print("Channel permanen berhasil disematkan di urutan teratas.")
        except Exception as e:
            print(f"GAGAL menyematkan channel permanen: {e}")
        # ----------------------------------------------------

        print("Mode aktif: Menampilkan SEMUA channel kecuali yang dikecualikan.")
        for channel_name, entries in channels.items():
            # Cek apakah nama channel atau grupnya cocok persis dengan daftar pengecualian (case-insensitive / tanpa peduli kapital)
            is_excluded = False
            for pat in excluded_patterns:
                # Periksa apakah teks pola cocok persis atau bagian dari nama (normalisasi teks)
                if normalize_name(pat) == normalize_name(channel_name):
                    is_excluded = True
                    break
                # Cek juga di dalam baris EXTINF (untuk mendeteksi kategori / group-title)
                for block in entries:
                    if any(pat.lower() in line.lower() for line in block if "group-title" in line):
                        # Pastikan pencocokan kata utuh/spesifik agar "LIVE" tidak memblokir "LIVE EVENT"
                        group_match = re.search(r'group-title="([^"]+)"', block[0], re.IGNORECASE)
                        if group_match and normalize_name(pat) == normalize_name(group_match.group(1)):
                            is_excluded = True
                            break
                if is_excluded:
                    break

            if is_excluded:
                print(f"Channel/Kategori dikecualikan (tidak dimasukkan): {channel_name}")
            else:
                for block in entries:
                    for bline in block:
                        f.write(f"{bline}\n")
                        
    print(f"Berhasil memperbarui playlist custom: {CUSTOM_PLAYLIST}")

if __name__ == "__main__":
    parse_and_split_m3u()
