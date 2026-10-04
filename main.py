import os
import sys
import re
import random
import asyncio
from aiohttp import web
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import (
    FloodWaitError,
    MessageDeleteForbiddenError,
    SlowModeWaitError,
    MessageNotModifiedError
)

# ==================== CẤU HÌNH HỆ THỐNG ANH KHÔI ====================
API_ID = int(os.environ.get("API_ID", 32906102))
API_HASH = os.environ.get("API_HASH", "9fc3add5b6bf34cc5335a85388f34a0f")

DEFAULT_SESSION = "1BVtsOIIBuxPBTJcjHmwH5MpU1DO068XwGFkdO2mxIdbqKtMt_-u3_jQkzaUUDCLtD_-HOZ2NTkXI0cDQistaYUm13b3uR-K_vRgXK168mNbiYd7selpS9nUa4NGQSfZSVu_LuhFmYmJK1kmcXJUD41QdOjuV4Otw-_-CZNk_hL-WiDIe4kX4_7hPdPuis1gm4ysRUsVokf0lBwlhXIwVEggOUTcQ8WAFzzQhDZFxZ6Xqqc74837vt05JS9PnLIRDG-dliqgNC4JRXioFTap8rczjaMYTKmcIk47Rb9M59vzjTCc1CwwqhE5tix0HbBElSdY_R7OFC2jMbCwykCnI__U7OsmUhNs="
SESSION_STRING = os.environ.get("SESSION_STRING", "").strip() or DEFAULT_SESSION

PORT = int(os.environ.get("PORT", 8080))
PREFIX = "."

SUPER_ADMINS = [6094686933]
ALLOWED_USERS = set(SUPER_ADMINS)

# ==================== TƯỜNG LỬA GHOST-SHIELD V7 (TURBO 0.1S) ====================
SYSTEM_CONFIG = {
    "delay": 0.1,          # Tốc độ xả cực hạn 0.1s
    "batch_rest": 15,      # Cứ sau 15 tin thì hạ nhiệt
    "rest_time": 0.5,      # Thời gian nghỉ chỉ 0.5s
    "use_icons": True,
    "lag_mode": False      # Tự động hóa chế độ lag máy cực nặng
}

RUNNING_TASKS = {}
MY_ID = None

# Kho Icon chọc tức độc dị kết hợp Cyber Warlord
MEME_ICONS = ["🤡", "🫵", "💀", "🤫", "🧏‍♂️", "💩", "🐸", "😹", "🤪", "👌", "👻", "😈", "🦴", "🚮", "🥱", "🖕", "🧠", "🤏"]
CYBER_ICONS = ["亗", "𖤍", "🜲", "𒆜", "☬", "⚡", "𒀱", "𓊈☠︎𓊉", "☣", "𖤐", "⚜", "𖣘", "☯", "☸"]
BATQUAI_SYMBOLS = ["☰", "☱", "☲", "☳", "☴", "☵", "☶", "☷"]

# Zero-Width Entropy Injection: Phá vỡ triệt để thuật toán quét trùng Hash SHA-256 của Telegram
INVISIBLE_CHARS = ["\u200b", "\u200c", "\u200d", "\ufeff", "\u2060", "\u200e", "\u200f"]

# Ký tự điều hướng Bi-directional (Bắt GPU/CPU của điện thoại đối phương đảo chiều render liên tục)
BIDI_OVERRIDES = ["\u202e", "\u202d", "\u202a", "\u202b", "\u202c", "\u2066", "\u2067", "\u2068", "\u2069"]

# Tầng dấu Zalgo cực dày gây giật khung hình ứng dụng
ZALGO_UP = [chr(i) for i in range(0x0300, 0x0315)]
ZALGO_DOWN = [chr(i) for i in range(0x0316, 0x0330)]
ZALGO_MID = [chr(i) for i in range(0x0334, 0x0339)]

def build_hardware_lag_payload(text: str, intensity: int = 5) -> str:
    """Tạo payload Zalgo kết hợp Bidi Overrides gây nghẽn tiến trình render UI trên điện thoại"""
    builder = []
    for ch in text:
        builder.append(ch)
        if ch.isalnum() or ch == " ":
            # Bơm tầng tầng lớp lớp combining marks
            for _ in range(intensity):
                builder.append(random.choice(ZALGO_UP))
                builder.append(random.choice(ZALGO_DOWN))
                builder.append(random.choice(ZALGO_MID))
            # Chèn ký tự đổi hướng rendering ngẫu nhiên
            builder.append(random.choice(BIDI_OVERRIDES))
    return "".join(builder)

def generate_stealth_text(text: str, apply_lag: bool = False) -> str:
    """Tạo chuỗi Hash duy nhất từng đòn đánh để bypass hệ thống kiểm duyệt tin lặp"""
    words = text.split(" ")
    salted_words = []
    for w in words:
        salt = "".join(random.choices(INVISIBLE_CHARS, k=random.randint(2, 6)))
        salted_words.append(f"{w}{salt}")
    core_text = " ".join(salted_words)

    if apply_lag:
        core_text = build_hardware_lag_payload(core_text, intensity=4)

    if SYSTEM_CONFIG["use_icons"]:
        ic_left = f"{random.choice(CYBER_ICONS)} {random.choice(MEME_ICONS)}"
        ic_right = f"{random.choice(MEME_ICONS)} {random.choice(CYBER_ICONS)}"
        return f"{ic_left} {core_text} {ic_right}"
    return core_text

def parse_and_sort_file(content: str) -> list:
    """Bóc tách hoàn toàn bằng file: Tự nhận biết số thứ tự đầu dòng, sắp xếp chuẩn và loại bỏ số"""
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    parsed = []
    for idx, line in enumerate(lines):
        match = re.match(r"^(\d+)[\.\)\:\-\s]+(.*)$", line)
        if match:
            order_num = int(match.group(1))
            clean_text = match.group(2).strip() or line
            parsed.append((order_num, clean_text))
        else:
            parsed.append((idx + 100000, line))
    parsed.sort(key=lambda x: x[0])
    return [item[1] for item in parsed]

async def safe_respond(event, text):
    """Phản hồi an toàn: Thử sửa tin nhắn nếu có thể, tự động chuyển reply nếu bị cấm edit"""
    if event.out:
        try:
            return await event.edit(text)
        except (MessageNotModifiedError, Exception):
            pass
    try:
        return await event.reply(text)
    except Exception as e:
        print(f"[!] Lỗi safe_respond: {e}")

# ==================== WEB SERVER GIỮ RENDER ONLINE 24/7 ====================
async def handle_health(request):
    return web.Response(
        text="ANH KHOI PRO MAX HYPER-DRIVE 2026\nTURBO SPEED: 0.1S | REST: 0.5S\nFIREWALL: GHOST-SHIELD V7 ACTIVE",
        content_type="text/plain; charset=utf-8",
        status=200
    )

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"[*] Web Server đã kích hoạt thành công trên Port {PORT}")

# ==================== KHỞI TẠO TELETHON CLIENT ====================
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== BỘ ĐIỀU PHỐI ĐỘC QUYỀN BẰNG FILE ====================
@client.on(events.NewMessage)
async def central_file_handler(event):
    global MY_ID, ALLOWED_USERS

    try:
        sender_id = event.sender_id

        # 1. TỰ ĐỘNG LƯU FILE KHI GỬI TỆP TIN .TXT (KHÔNG CẦN NHẬP CHỮ)
        if (event.out or sender_id in ALLOWED_USERS) and event.message.file:
            fname = getattr(event.message.file, "name", None)
            if fname and str(fname).lower().endswith(".txt"):
                save_path = await event.message.download_media(file=fname)
                print(f"[*] [TỰ ĐỘNG LƯU FILE]: {save_path}")
                await safe_respond(event, f"📥 **ĐÃ LƯU FILE SERVER:** `{os.path.basename(save_path)}`\n⚡ Sẵn sàng xả 0.1s: `{PREFIX}xaf {os.path.basename(save_path)}`")
                return

        # 2. KIỂM TRA QUYỀN ĐIỀU KHIỂN
        is_authorized = event.out or (sender_id in ALLOWED_USERS)
        if not is_authorized:
            return

        raw_text = (event.message.message or "").strip()
        if not raw_text.startswith(PREFIX):
            return

        parts = raw_text.split()
        cmd = parts[0].lower()
        args = parts[1:]
        chat_id = event.chat_id

        print(f"[>] [KÍCH HOẠT LỆNH]: {cmd} | Chat: {chat_id}")

        # --- LỆNH: .ping ---
        if cmd == f"{PREFIX}ping":
            await safe_respond(
                event,
                f"⚡ **ANH KHÔI HYPER-DRIVE TURBO 0.1S ONLINE!** 🤡🫵\n"
                f"🛡️ **Firewall Anti-Ban:** `GHOST SHIELD V7 ULTRA`\n"
                f"⏱️ **Vận tốc:** `{SYSTEM_CONFIG['delay']}s/đòn` | **Nghỉ:** `{SYSTEM_CONFIG['rest_time']}s`\n"
                f"🌀 **Chế độ Lag Máy:** `{'BẬT (ZALGO+BIDI)' if SYSTEM_CONFIG['lag_mode'] else 'TẮT'}`\n"
                f"🌐 **Server Render:** `Live 24/7 Hoàn Hảo`"
            )
            return

        # --- LỆNH: .help / .lenh ---
        if cmd in [f"{PREFIX}help", f"{PREFIX}lenh"]:
            menu = (
                "👑 **HỆ THỐNG ĐIỀU KHIỂN FILE & TURBO 0.1S - ANH KHÔI** 🤪👌\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "**📁 QUẢN LÝ BẰNG FILE:**\n"
                f"• Gửi file `.txt` vào bất kỳ chat nào -> Tự nạp vào server\n"
                f"• `{PREFIX}dsfile` : Xem tất cả các file đang có trên server\n"
                f"• `{PREFIX}xemfile <tên>` : Đọc trước nội dung file\n"
                f"• `{PREFIX}xoafile <tên>` : Xóa file khỏi máy chủ\n\n"
                "**🔥 CHIẾN DỊCH HỎA LỰC 0.1S (THEO FILE):**\n"
                f"• `{PREFIX}xaf <tên_file>` : Xả 1 lượt tốc độ 0.1s (Tự lọc số dòng)\n"
                f"• `{PREFIX}treongon <tên_file>` : Treo xoay vòng vô tận 24/7 từ file\n"
                f"• `{PREFIX}lagfile <tên_file>` : Xả đòn cấy Zalgo + Bát Quái gây giật lag máy\n"
                f"• `{PREFIX}batquaifile <tên_file>` : Trận pháp xoay vần 8 quẻ từ nội dung file\n"
                f"• `{PREFIX}dung` : Đình chỉ lập tức mọi luồng xả / treo\n\n"
                "**🛡️ ANTI-BAN & ĐIỀU KHIỂN TỐC ĐỘ:**\n"
                f"• `{PREFIX}delay <giây>` : Cài đặt độ trễ (Hạ xuống tới `0.1s`)\n"
                f"• `{PREFIX}nghi <giây>` : Cài đặt thời gian xả nhiệt (Rút xuống `0.5s`)\n"
                f"• `{PREFIX}lag` : Bật/Tắt chế độ tự cấy Zalgo lag máy vào mọi câu\n"
                f"• `{PREFIX}icon` : Bật/Tắt dàn icon chọc tức 🤡🫵💀\n\n"
                "**🧹 THANH TRỪNG TIN NHẮN:**\n"
                f"• `{PREFIX}del [số]` : Xóa tin nhắn của chính mình\n"
                f"• `{PREFIX}xoahet` (Reply tin) : Quét sạch tin từ điểm reply"
            )
            await safe_respond(event, menu)
            return

        # --- LỆNH: .dsfile, .xemfile, .xoafile ---
        if cmd == f"{PREFIX}dsfile":
            files = [f for f in os.listdir(".") if os.path.isfile(f) and f.endswith(".txt")]
            if not files:
                return await safe_respond(event, "📁 Server chưa có file `.txt` nào. Hãy gửi file `.txt` vào chat để nạp!")
            ds = "\n".join([f"• `{f}` ({os.path.getsize(f)} bytes)" for f in files[:35]])
            await safe_respond(event, f"📁 **DANH SÁCH FILE VĂN BẢN TRÊN SERVER:**\n{ds}")
            return

        if cmd == f"{PREFIX}xemfile":
            if not args:
                return await safe_respond(event, f"💡 Cú pháp: `{PREFIX}xemfile <tên_file>`")
            fname = args[0]
            if not os.path.exists(fname):
                return await safe_respond(event, f"❌ Không tìm thấy file `{fname}`!")
            try:
                with open(fname, "r", encoding="utf-8", errors="ignore") as f:
                    data = f.read(3000)
                await safe_respond(event, f"📄 **NỘI DUNG `{fname}`:**\n```\n{data}\n```")
            except Exception as e:
                await safe_respond(event, f"❌ Lỗi đọc file: {e}")
            return

        if cmd == f"{PREFIX}xoafile":
            if not args:
                return await safe_respond(event, f"💡 Cú pháp: `{PREFIX}xoafile <tên_file>`")
            fname = args[0]
            if fname in ["main.py", "requirements.txt"]:
                return await safe_respond(event, "⚠️ Không được xóa file hệ thống!")
            if not os.path.exists(fname):
                return await safe_respond(event, f"❌ File `{fname}` không tồn tại.")
            try:
                os.remove(fname)
                await safe_respond(event, f"🗑️ Đã xóa file `{fname}` thành công!")
            except Exception as e:
                await safe_respond(event, f"❌ Lỗi xóa file: {e}")
            return

        # --- LỆNH: .delay & .nghi ---
        if cmd == f"{PREFIX}delay":
            if not args:
                return await safe_respond(event, f"⏱️ Delay hiện tại: `{SYSTEM_CONFIG['delay']}s/đòn`")
            try:
                val = float(args[0])
                if val < 0.05:
                    return await safe_respond(event, "⚠️ **Cảnh báo Firewall:** Mức tối thiểu là `0.1s` để tránh bị Telegram Drop Socket!")
                SYSTEM_CONFIG["delay"] = val
                await safe_respond(event, f"🛡️ Đã thiết lập vận tốc siêu tốc: `{val}s/đòn` ⚡")
            except Exception:
                await safe_respond(event, "❌ Số giây không hợp lệ!")
            return

        if cmd == f"{PREFIX}nghi":
            if not args:
                return await safe_respond(event, f"⏱️ Thời gian nghỉ xả nhiệt hiện tại: `{SYSTEM_CONFIG['rest_time']}s`")
            try:
                val = float(args[0])
                SYSTEM_CONFIG["rest_time"] = max(0.2, val)
                await safe_respond(event, f"🛡️ Đã cài đặt thời gian nghỉ xả nhiệt: `{SYSTEM_CONFIG['rest_time']}s`")
            except Exception:
                await safe_respond(event, "❌ Số giây không hợp lệ!")
            return

        # --- LỆNH: .lag (BẬT/TẮT TỰ ĐỘNG CHÈN PAYLOAD GÂY LAG MÁY) ---
        if cmd == f"{PREFIX}lag":
            SYSTEM_CONFIG["lag_mode"] = not SYSTEM_CONFIG["lag_mode"]
            st = "BẬT CỰC NẶNG (ZALGO + BIDI OVERLOAD) ☠️" if SYSTEM_CONFIG["lag_mode"] else "TẮT ⚪"
            await safe_respond(event, f"🌀 Chế độ cấy mã lag giật khung hình: **{st}**")
            return

        # --- LỆNH: .icon ---
        if cmd == f"{PREFIX}icon":
            SYSTEM_CONFIG["use_icons"] = not SYSTEM_CONFIG["use_icons"]
            st = "BẬT 🤡🫵💀" if SYSTEM_CONFIG["use_icons"] else "TẮT ⚪"
            await safe_respond(event, f"𖤍 Dàn Icon chọc tức: **{st}**")
            return

        # --- LỆNH: .dung / .stop ---
        if cmd in [f"{PREFIX}dung", f"{PREFIX}stop"]:
            if RUNNING_TASKS.get(chat_id):
                RUNNING_TASKS[chat_id] = False
                await safe_respond(event, "🛑 **ĐÃ THU HỒI TRẬN PHÁP – TOÀN BỘ LUỒNG XẢ ĐÃ NGẮT!**")
            else:
                await safe_respond(event, "⚠️ Không có tác vụ xả nào đang chạy tại đoạn chat này.")
            return

        # --- LỆNH: .xaf (XẢ FILE TỐC ĐỘ 0.1S) ---
        if cmd == f"{PREFIX}xaf":
            if not args:
                return await safe_respond(event, f"💡 Cú pháp: `{PREFIX}xaf <tên_file>` (Dùng `{PREFIX}dsfile` để xem danh sách)")
            fname = args[0]
            if not os.path.exists(fname):
                return await safe_respond(event, f"❌ Không tìm thấy file `{fname}`! Hãy gửi file `.txt` vào chat để bot nạp.")

            try:
                with open(fname, "r", encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
            except Exception as e:
                return await safe_respond(event, f"❌ Lỗi đọc file: {e}")

            lines = parse_and_sort_file(raw)
            if not lines:
                return await safe_respond(event, "⚠️ File không có nội dung hợp lệ!")

            try:
                await event.delete()
            except Exception:
                pass

            RUNNING_TASKS[chat_id] = True
            count = 0

            for line in lines:
                if not RUNNING_TASKS.get(chat_id):
                    break

                final_msg = generate_stealth_text(line, apply_lag=SYSTEM_CONFIG["lag_mode"])

                sent = False
                while not sent and RUNNING_TASKS.get(chat_id):
                    try:
                        await client.send_message(chat_id, final_msg)
                        sent = True
                        count += 1
                    except FloodWaitError as e:
                        print(f"[FIREWALL] Gặp FloodWait! Tự ngủ {e.seconds}s để bảo toàn tài khoản...")
                        await asyncio.sleep(e.seconds + 1)
                    except SlowModeWaitError as e:
                        await asyncio.sleep(e.seconds + 1)
                    except Exception as e:
                        print(f"[LỖI GỬI]: {e}")
                        await asyncio.sleep(0.2)
                        break

                # Xả nhiệt cực ngắn 0.5s sau mỗi chu kỳ 15 tin
                if count % SYSTEM_CONFIG["batch_rest"] == 0 and RUNNING_TASKS.get(chat_id):
                    await asyncio.sleep(SYSTEM_CONFIG["rest_time"])

                # Delay 0.1s kết hợp Micro-Jitter chống quét mẫu bot
                jitter = random.uniform(0.01, 0.04)
                await asyncio.sleep(SYSTEM_CONFIG["delay"] + jitter)

            RUNNING_TASKS[chat_id] = False
            return

        # --- LỆNH: .treongon (XOAY VÒNG 24/7 TỪ FILE) ---
        if cmd == f"{PREFIX}treongon":
            if not args:
                return await safe_respond(event, f"💡 Cú pháp: `{PREFIX}treongon <tên_file>`")
            fname = args[0]
            if not os.path.exists(fname):
                return await safe_respond(event, f"❌ File `{fname}` không tồn tại!")

            try:
                with open(fname, "r", encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
            except Exception as e:
                return await safe_respond(event, f"❌ Lỗi đọc file: {e}")

            lines = parse_and_sort_file(raw)
            if not lines:
                return await safe_respond(event, "⚠️ File rỗng!")

            try:
                await event.delete()
            except Exception:
                pass

            RUNNING_TASKS[chat_id] = True
            idx = 0
            total_lines = len(lines)
            count = 0

            while RUNNING_TASKS.get(chat_id):
                current_line = lines[idx]
                final_msg = generate_stealth_text(current_line, apply_lag=SYSTEM_CONFIG["lag_mode"])

                sent = False
                while not sent and RUNNING_TASKS.get(chat_id):
                    try:
                        await client.send_message(chat_id, final_msg)
                        sent = True
                        count += 1
                    except FloodWaitError as e:
                        await asyncio.sleep(e.seconds + 1)
                    except SlowModeWaitError as e:
                        await asyncio.sleep(e.seconds + 1)
                    except Exception:
                        await asyncio.sleep(0.4)
                        break

                idx = (idx + 1) % total_lines

                if count % SYSTEM_CONFIG["batch_rest"] == 0 and RUNNING_TASKS.get(chat_id):
                    await asyncio.sleep(SYSTEM_CONFIG["rest_time"])

                jitter = random.uniform(0.01, 0.05)
                await asyncio.sleep(SYSTEM_CONFIG["delay"] + jitter)

            RUNNING_TASKS[chat_id] = False
            return

        # --- LỆNH: .lagfile (CẤY SIÊU ZALGO VÀ BIDI OVERLOAD VÀO TỪNG DÒNG FILE) ---
        if cmd == f"{PREFIX}lagfile":
            if not args:
                return await safe_respond(event, f"💡 Cú pháp: `{PREFIX}lagfile <tên_file>`")
            fname = args[0]
            if not os.path.exists(fname):
                return await safe_respond(event, f"❌ Không tìm thấy file `{fname}`!")

            try:
                with open(fname, "r", encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
            except Exception as e:
                return await safe_respond(event, f"❌ Lỗi đọc file: {e}")

            lines = parse_and_sort_file(raw)
            if not lines:
                return await safe_respond(event, "⚠️ File không có nội dung!")

            try:
                await event.delete()
            except Exception:
                pass

            RUNNING_TASKS[chat_id] = True
            count = 0

            for line in lines:
                if not RUNNING_TASKS.get(chat_id):
                    break

                # Tạo đòn đánh Zalgo cực hạn
                lag_payload = generate_stealth_text(line, apply_lag=True)

                sent = False
                while not sent and RUNNING_TASKS.get(chat_id):
                    try:
                        await client.send_message(chat_id, lag_payload)
                        sent = True
                        count += 1
                    except FloodWaitError as e:
                        await asyncio.sleep(e.seconds + 1)
                    except SlowModeWaitError as e:
                        await asyncio.sleep(e.seconds + 1)
                    except Exception:
                        await asyncio.sleep(0.3)
                        break

                if count % SYSTEM_CONFIG["batch_rest"] == 0 and RUNNING_TASKS.get(chat_id):
                    await asyncio.sleep(SYSTEM_CONFIG["rest_time"])

                jitter = random.uniform(0.02, 0.06)
                await asyncio.sleep(SYSTEM_CONFIG["delay"] + jitter)

            RUNNING_TASKS[chat_id] = False
            return

        # --- LỆNH: .batquaifile (TRẬN PHÁP 8 QUẺ KINH DỊCH THEO FILE) ---
        if cmd == f"{PREFIX}batquaifile":
            if not args:
                return await safe_respond(event, f"💡 Cú pháp: `{PREFIX}batquaifile <tên_file>`")
            fname = args[0]
            if not os.path.exists(fname):
                return await safe_respond(event, f"❌ Không tìm thấy file `{fname}`!")

            try:
                with open(fname, "r", encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
            except Exception as e:
                return await safe_respond(event, f"❌ Lỗi đọc file: {e}")

            lines = parse_and_sort_file(raw)
            if not lines:
                return await safe_respond(event, "⚠️ File rỗng!")

            try:
                await event.delete()
            except Exception:
                pass

            RUNNING_TASKS[chat_id] = True
            count = 0

            for line in lines:
                if not RUNNING_TASKS.get(chat_id):
                    break

                q = random.choice(BATQUAI_SYMBOLS)
                meme = random.choice(MEME_ICONS)
                cyber = random.choice(CYBER_ICONS)
                transformed = f"☯ {cyber} [{q} BÁT QUÁI TRẬN {q}] {cyber} ☯\n👉 {line} 👈\n{meme} {random.choice(BATQUAI_SYMBOLS)} ANH KHÔI ĐỘC TÔN {random.choice(BATQUAI_SYMBOLS)} {meme}"
                final_msg = generate_stealth_text(transformed, apply_lag=SYSTEM_CONFIG["lag_mode"])

                sent = False
                while not sent and RUNNING_TASKS.get(chat_id):
                    try:
                        await client.send_message(chat_id, final_msg)
                        sent = True
                        count += 1
                    except FloodWaitError as e:
                        await asyncio.sleep(e.seconds + 1)
                    except SlowModeWaitError as e:
                        await asyncio.sleep(e.seconds + 1)
                    except Exception:
                        await asyncio.sleep(0.3)
                        break

                if count % SYSTEM_CONFIG["batch_rest"] == 0 and RUNNING_TASKS.get(chat_id):
                    await asyncio.sleep(SYSTEM_CONFIG["rest_time"])

                jitter = random.uniform(0.02, 0.05)
                await asyncio.sleep(SYSTEM_CONFIG["delay"] + jitter)

            RUNNING_TASKS[chat_id] = False
            return

        # --- LỆNH: .del & .xoahet ---
        if cmd == f"{PREFIX}del":
            count = int(args[0]) if (args and args[0].isdigit()) else 1
            try:
                await event.delete()
            except Exception:
                pass
            deleted = 0
            async for msg in client.iter_messages(chat_id, from_user="me", limit=count + 5):
                if deleted >= count:
                    break
                try:
                    await msg.delete()
                    deleted += 1
                    await asyncio.sleep(0.04)
                except Exception:
                    pass
            return

        if cmd in [f"{PREFIX}xoahet", f"{PREFIX}purge"]:
            reply = await event.get_reply_message()
            if not reply:
                return await safe_respond(event, "💡 Hãy **Reply** vào tin nhắn bắt đầu muốn xóa rồi gõ `.xoahet`")
            start_id = reply.id
            end_id = event.id
            try:
                await event.delete()
            except Exception:
                pass
            msg_ids = []
            async for msg in client.iter_messages(chat_id, min_id=start_id - 1, max_id=end_id):
                msg_ids.append(msg.id)
            if msg_ids:
                for i in range(0, len(msg_ids), 100):
                    batch = msg_ids[i:i + 100]
                    try:
                        await client.delete_messages(chat_id, batch)
                        await asyncio.sleep(0.08)
                    except MessageDeleteForbiddenError:
                        pass
            return

    except Exception as e:
        print(f"[!] LỖI SỰ KIỆN: {e}")

# ==================== KHỞI ĐỘNG HỆ THỐNG ====================
async def main():
    global MY_ID, ALLOWED_USERS
    await start_web_server()
    await client.start()

    me = await client.get_me()
    MY_ID = me.id
    ALLOWED_USERS.add(MY_ID)

    print("=" * 65)
    print(f"[*] HỆ THỐNG HYPER-DRIVE 0.1S ANH KHÔI ĐÃ SẴN SÀNG!")
    print(f"[*] Tài khoản Bot: {me.first_name} | @{me.username} | ID: {me.id}")
    print(f"[*] Cấu hình Vận tốc: {SYSTEM_CONFIG['delay']}s | Nghỉ: {SYSTEM_CONFIG['rest_time']}s | Ghost-Shield v7: ACTIVE")
    print("=" * 65)

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
