import os
import re
import urllib.request

SOURCES_FILE = "sources.txt"
OUTPUT_DIR = "Sumber Gratis"
SELECT_FILE = "chanel_pilihan.txt"
CUSTOM_PLAYLIST = "ZeroTVGRATIS.m3u"

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

    for url_idx, source_url in enumerate(source_urls, 1):
        print(f"Mengambil data dari URL ke-{url_idx}: {source_url}")
        req = urllib.request.Request(source_url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8')
        except Exception as e:
            print(f"GAGAL mengambil data dari URL {source_url}: {e}")
            continue

        lines = content.splitlines()
        print(f"Berhasil membaca {len(lines)} baris dari sumber ke-{url_idx}")
        
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
            i += 1

    # 1. Simpan file M3U terpisah per channel di folder Sumber Gratis
    for channel_name, entries in channels.items():
        file_path = os.path.join(OUTPUT_DIR, f"{channel_name}.m3u")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for block in entries:
                for bline in block:
                    f.write(f"{bline}\n")

    # 2. Buat playlist gabungan khusus berdasarkan chanel_pilihan.txt
    if os.path.exists(SELECT_FILE):
        with open(SELECT_FILE, "r", encoding="utf-8") as f:
            selected_names = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
        if selected_names:
            with open(CUSTOM_PLAYLIST, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for name in selected_names:
                    safe_target = re.sub(r'[\\/*?:"<>|]', "", name).strip().replace(" ", "_")
                    if safe_target in channels:
                        for block in channels[safe_target]:
                            for bline in block:
                                f.write(f"{bline}\n")
                        print(f"Channel ditambahkan: {name}")
                    else:
                        print(f"Channel pilihan tidak ditemukan di semua sumber: {name}")
            print(f"Berhasil memperbarui playlist custom: {CUSTOM_PLAYLIST}")

if __name__ == "__main__":
    parse_and_split_m3u()
