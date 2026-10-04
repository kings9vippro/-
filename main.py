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

# ID Admin cấp quyền điều khiển
SUPER_ADMINS = [6094686933]
ALLOWED_USERS = set(SUPER_ADMINS)

# Cấu hình Tốc độ Siêu Tốc & Tường lửa Anti-Ban
SYSTEM_CONFIG = {
    "delay": 0.1,          # Vận tốc siêu tốc 0.1s mỗi đòn
    "use_icons": True,     # Bật icon chọc tức độc dị
    "batch_rest": 15,      # Cứ sau 15 tin sẽ nghỉ hạ nhiệt
    "rest_time": 0.5,      # Thời gian nghỉ cực ngắn 0.5s
    "glitch_mode": True    # Bật hiệu ứng Zalgo ma quái gây lag khung hình
}

RUNNING_TASKS = {}
LATEST_FILE = None  # Tự lưu file mới nhất được gửi lên
MY_ID = None

# Kho Icon Meme Khinh Bỉ + Cyber Warlord
MEME_ICONS = ["🤡", "🫵", "💀", "🤫", "🧏‍♂️", "💩", "🐸", "😹", "🤪", "👌", "👻", "😈", "🦴", "🚮", "🥱", "🖕"]
CYBER_ICONS = ["亗", "𖤍", "🜲", "𒆜", "☬", "⚡", "𒀱", "𓊈☠︎𓊉", "☣", "𖤐", "⚜", "𖣘", "☯", "☸"]
BATQUAI_SYMBOLS = ["☰", "☱", "☲", "☳", "☴", "☵", "☶", "☷"]

# Ký tự vô hình & Đổi hướng chống quét Hash lặp tin
INVISIBLE_CHARS = ["\u200b", "\u200c", "\u200d", "\ufeff", "\u2060", "\u200e", "\u200f"]

# Bảng dấu Zalgo Unicode Combining siêu nặng bắt điện thoại render lag
ZALGO_UP = [chr(i) for i in range(0x0300, 0x0315)]
ZALGO_DOWN = [chr(i) for i in range(0x0316, 0x0330)]
ZALGO_MID = [chr(i) for i in range(0x0334, 0x0339)]

def make_extreme_zalgo(text: str, intensity: int = 5) -> str:
    """Bơm 8 tầng ký tự Zalgo ma quái khiến parser Telegram giật lag"""
    res = []
    for char in text:
        res.append(char)
        if char.isalnum():
            for _ in range(intensity):
                res.append(random.choice(ZALGO_UP))
                res.append(random.choice(ZALGO_DOWN))
                res.append(random.choice(ZALGO_MID))
    return "".join(res)

def generate_stealth_text(text: str) -> str:
    """Đột biến mã Hash chống chặn Spam kết hợp hiệu ứng chọc tức"""
    if SYSTEM_CONFIG["glitch_mode"]:
        text = make_extreme_zalgo(text, intensity=3)

    words = text.split(" ")
    salted = []
    for w in words:
        salt = "".join(random.choices(INVISIBLE_CHARS, k=random.randint(1, 4)))
        salted.append(f"{w}{salt}")
    core_text = " ".join(salted)

    if SYSTEM_CONFIG["use_icons"]:
        ic_left = f"{random.choice(CYBER_ICONS)} {random.choice(MEME_ICONS)}"
        ic_right = f"{random.choice(MEME_ICONS)} {random.choice(CYBER_ICONS)}"
        return f"{ic_left} {core_text} {ic_right}"
    return core_text

def parse_and_sort_file(content: str) -> list:
    """Tự động phát hiện số thứ tự đầu dòng (1., 2), 3-...), sắp xếp từ nhỏ đến lớn và xóa số"""
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
    """Phản hồi an toàn: Sửa tin nhắn của chính mình hoặc reply tức thì"""
    if event.out:
        try:
            return await event.edit(text)
        except (MessageNotModifiedError, Exception):
            pass
    try:
        return await event.reply(text)
    except Exception:
        pass

# ==================== MÁY CHỦ WEB CHO RENDER LIVE 24/7 ====================
async def handle_health(request):
    return web.Response(
        text="ANH KHOI PRO MAX TURBO 0.1S\nFILE-BASED ENGINE ACTIVE\nSTATUS: ONLINE 24/7",
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
    print(f"[*] Web Server đã kích hoạt thành công tại Port {PORT}")

# ==================== KHỞI TẠO TELETHON CLIENT ====================
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== BỘ ĐIỀU PHỐI TIN NHẮN TẬP TRUNG ====================
@client.on(events.NewMessage)
async def central_handler(event):
    global MY_ID, ALLOWED_USERS, LATEST_FILE

    try:
        sender_id = event.sender_id

        # 1. TỰ ĐỘNG BẮT FILE .TXT (Không cần gõ bất kỳ câu chữ nào)
        if (event.out or sender_id in ALLOWED_USERS) and event.message.file:
            fname = getattr(event.message.file, "name", None)
            if fname and str(fname).lower().endswith(".txt"):
                save_path = await event.message.download_media(file=fname)
                LATEST_FILE = os.path.basename(save_path)
                print(f"[*] [TỰ ĐỘNG NẠP FILE MỚI]: {LATEST_FILE}")
                await safe_respond(
                    event,
                    f"📁 **ĐÃ NẠP TỰ ĐỘNG FILE KỊCH BẢN!**\n"
                    f"• Tên file: `{LATEST_FILE}`\n"
                    f"• Vận tốc: `{SYSTEM_CONFIG['delay']}s/đòn` | Nghỉ: `{SYSTEM_CONFIG['rest_time']}s`\n"
                    f"👉 Gõ `{PREFIX}chay` để xả ngay hoặc `{PREFIX}treo` để xoay vòng 24/7!"
                )
                return

        # 2. Kiểm tra quyền điều khiển
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

        print(f"[>] [LỆNH]: {cmd} | Chat: {chat_id}")

        # --- LỆNH: .ping ---
        if cmd == f"{PREFIX}ping":
            cur_file = LATEST_FILE or "Chưa nạp file nào"
            await safe_respond(
                event,
                f"⚡ **ANH KHÔI TURBO 0.1S – ULTRA SHIELD V7 ONLINE!** 🤡🫵\n"
                f"🛡️ **Firewall Anti-Ban:** `GHOST HASH MUTATOR`\n"
                f"⏱️ **Vận tốc:** `{SYSTEM_CONFIG['delay']}s/đòn` | **Nghỉ hạ nhiệt:** `{SYSTEM_CONFIG['rest_time']}s`\n"
                f"📁 **File kịch bản hiện tại:** `{cur_file}`\n"
                f"🌀 **Chế độ Glitch Lag Máy:** `{'BẬT 🔥' if SYSTEM_CONFIG['glitch_mode'] else 'TẮT ⚪'}`"
            )
            return

        # --- LỆNH: .help / .lenh ---
        if cmd in [f"{PREFIX}help", f"{PREFIX}lenh"]:
            menu = (
                "👑 **HỆ THỐNG ĐIỀU HÀNH KỊCH BẢN FILE - ANH KHÔI 2026** 🤪👌\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "**📁 THAO TÁC FILE TỰ ĐỘNG (KHÔNG CẦN NHẬP CHỮ):**\n"
                f"• Gửi file `.txt` vào chat -> Tự động nạp file ngay lập tức\n"
                f"• `{PREFIX}chay [tên_file]` : Xả kịch bản tốc độ 0.1s (Bỏ trống = Lấy file mới nhất)\n"
                f"• `{PREFIX}treo [tên_file]` : Treo xoay vòng vô tận 24/7 tốc độ 0.1s\n"
                f"• `{PREFIX}dung` : Đình chỉ lập tức mọi luồng xả / treo\n"
                f"• `{PREFIX}dsfile` : Xem danh sách file có sẵn trên máy chủ\n"
                f"• `{PREFIX}xoafile <tên>` : Xóa file kịch bản khỏi máy chủ\n\n"
                "**🛡️ ANTI-BAN & ĐIỀU CHỈNH TỐC ĐỘ:**\n"
                f"• `{PREFIX}setdelay <giây>` : Cài đặt giây mỗi đòn (Mặc định: `0.1`)\n"
                f"• `{PREFIX}setrest <giây>` : Cài đặt giây nghỉ xả nhiệt (Mặc định: `0.5`)\n"
                f"• `{PREFIX}glitch` : Bật/Tắt hiệu ứng Zalgo ma quái lag máy đối phương\n"
                f"• `{PREFIX}icon` : Bật/Tắt dàn icon chọc tức 🤡🫵💀\n\n"
                "**🧹 DỌN DẸP TIN NHẮN:**\n"
                f"• `{PREFIX}del [số]` : Xóa tin nhắn của chính mình\n"
                f"• `{PREFIX}xoahet` (Reply tin) : Quét sạch tin từ điểm reply"
            )
            await safe_respond(event, menu)
            return

        # --- LỆNH: .setdelay (HẠ XUỐNG 0.1S) ---
        if cmd == f"{PREFIX}setdelay":
            if not args:
                return await safe_respond(event, f"⏱️ Delay hiện tại: `{SYSTEM_CONFIG['delay']}s/đòn`")
            try:
                val = float(args[0])
                SYSTEM_CONFIG["delay"] = max(0.05, val)
                await safe_respond(event, f"🛡️ Đã thiết lập vận tốc siêu tốc: `{SYSTEM_CONFIG['delay']}s/đòn` ⚡")
            except Exception:
                await safe_respond(event, "❌ Số giây không hợp lệ!")
            return

        # --- LỆNH: .setrest (NGHỈ 0.5S) ---
        if cmd == f"{PREFIX}setrest":
            if not args:
                return await safe_respond(event, f"⏱️ Thời gian nghỉ giải nhiệt hiện tại: `{SYSTEM_CONFIG['rest_time']}s`")
            try:
                val = float(args[0])
                SYSTEM_CONFIG["rest_time"] = max(0.2, val)
                await safe_respond(event, f"🛡️ Đã thiết lập thời gian nghỉ hạ nhiệt: `{SYSTEM_CONFIG['rest_time']}s`")
            except Exception:
                await safe_respond(event, "❌ Số giây không hợp lệ!")
            return

        # --- LỆNH: .glitch (BẬT/TẮT ZALGO LAG MÁY) ---
        if cmd == f"{PREFIX}glitch":
            SYSTEM_CONFIG["glitch_mode"] = not SYSTEM_CONFIG["glitch_mode"]
            st = "BẬT CỰC HẠN 🔥 (Gây lag giật khung hình)" if SYSTEM_CONFIG["glitch_mode"] else "TẮT ⚪"
            await safe_respond(event, f"🌀 Chế độ Zalgo ma quái: **{st}**")
            return

        # --- LỆNH: .icon ---
        if cmd == f"{PREFIX}icon":
            SYSTEM_CONFIG["use_icons"] = not SYSTEM_CONFIG["use_icons"]
            st = "BẬT 🤡🫵💀" if SYSTEM_CONFIG["use_icons"] else "TẮT ⚪"
            await safe_respond(event, f"𖤍 Dàn Icon chọc tức: **{st}**")
            return

        # --- LỆNH: .dsfile, .xoafile ---
        if cmd == f"{PREFIX}dsfile":
            files = [f for f in os.listdir(".") if os.path.isfile(f) and f.endswith(".txt")]
            if not files:
                return await safe_respond(event, "📁 Server chưa có file kịch bản `.txt` nào. Hãy gửi file vào chat!")
            ds = "\n".join([f"• `{f}` ({os.path.getsize(f)} bytes)" for f in files[:35]])
            await safe_respond(event, f"📁 **DANH SÁCH FILE KỊCH BẢN TRÊN SERVER:**\n{ds}")
            return

        if cmd == f"{PREFIX}xoafile":
            if not args:
                return await safe_respond(event, f"💡 Cú pháp: `{PREFIX}xoafile <tên_file>`")
            fname = args[0]
            if fname in ["main.py", "requirements.txt"]:
                return await safe_respond(event, "⚠️ Không được xóa file gốc hệ thống!")
            if not os.path.exists(fname):
                return await safe_respond(event, f"❌ File `{fname}` không tồn tại.")
            try:
                os.remove(fname)
                if LATEST_FILE == fname:
                    LATEST_FILE = None
                await safe_respond(event, f"🗑️ Đã xóa file `{fname}` thành công!")
            except Exception as e:
                await safe_respond(event, f"❌ Lỗi: {e}")
            return

        # --- LỆNH: .dung / .stop ---
        if cmd in [f"{PREFIX}dung", f"{PREFIX}stop"]:
            if RUNNING_TASKS.get(chat_id):
                RUNNING_TASKS[chat_id] = False
                await safe_respond(event, "🛑 **ĐÃ THU HỒI TRẬN PHÁP – TOÀN BỘ LUỒNG ĐÃ DỪNG!**")
            else:
                await safe_respond(event, "⚠️ Không có tác vụ nào đang chạy tại đoạn chat này.")
            return

        # --- LỆNH: .chay (XẢ FILE 1 LƯỢT Ở VẬN TỐC 0.1S) ---
        if cmd in [f"{PREFIX}chay", f"{PREFIX}xaf"]:
            target_file = args[0] if args else LATEST_FILE
            if not target_file:
                return await safe_respond(event, "❌ Chưa có file kịch bản nào! Hãy gửi 1 file `.txt` vào chat trước.")

            if not os.path.exists(target_file):
                return await safe_respond(event, f"❌ Không tìm thấy file `{target_file}` trên máy chủ!")

            try:
                with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
            except Exception as e:
                return await safe_respond(event, f"❌ Lỗi đọc file: {e}")

            lines = parse_and_sort_file(raw)
            if not lines:
                return await safe_respond(event, "⚠️ File rỗng hoặc không có nội dung hợp lệ!")

            try:
                await event.delete()
            except Exception:
                pass

            RUNNING_TASKS[chat_id] = True
            count = 0

            for line in lines:
                if not RUNNING_TASKS.get(chat_id):
                    break

                final_msg = generate_stealth_text(line)
                sent = False
                while not sent and RUNNING_TASKS.get(chat_id):
                    try:
                        await client.send_message(chat_id, final_msg)
                        sent = True
                        count += 1
                    except FloodWaitError as e:
                        print(f"[FIREWALL] Bắt gặp FloodWait! Tự ngủ {e.seconds}s để bảo vệ tài khoản...")
                        await asyncio.sleep(e.seconds + 1)
                    except SlowModeWaitError as e:
                        print(f"[FIREWALL] Nhóm bật SlowMode! Chờ {e.seconds}s...")
                        await asyncio.sleep(e.seconds + 1)
                    except Exception as e:
                        print(f"[LỖI GỬI]: {e}")
                        await asyncio.sleep(0.2)
                        break

                # Nghỉ giải nhiệt định kỳ cực ngắn đúng 0.5s
                if count % SYSTEM_CONFIG["batch_rest"] == 0 and RUNNING_TASKS.get(chat_id):
                    await asyncio.sleep(SYSTEM_CONFIG["rest_time"])

                await asyncio.sleep(SYSTEM_CONFIG["delay"])

            RUNNING_TASKS[chat_id] = False
            return

        # --- LỆNH: .treo (TREO NGÔN XOAY VÒNG 24/7 Ở VẬN TỐC 0.1S) ---
        if cmd in [f"{PREFIX}treo", f"{PREFIX}treongon"]:
            target_file = args[0] if args else LATEST_FILE
            if not target_file:
                return await safe_respond(event, "❌ Chưa có file kịch bản nào! Hãy gửi 1 file `.txt` vào chat trước.")

            if not os.path.exists(target_file):
                return await safe_respond(event, f"❌ File `{target_file}` không tồn tại!")

            try:
                with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
            except Exception as e:
                return await safe_respond(event, f"❌ Lỗi đọc file: {e}")

            lines = parse_and_sort_file(raw)
            if not lines:
                return await safe_respond(event, "⚠️ File kịch bản rỗng!")

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
                final_msg = generate_stealth_text(current_line)

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

                idx = (idx + 1) % total_lines

                # Nghỉ giải nhiệt định kỳ 0.5s
                if count % SYSTEM_CONFIG["batch_rest"] == 0 and RUNNING_TASKS.get(chat_id):
                    await asyncio.sleep(SYSTEM_CONFIG["rest_time"])

                await asyncio.sleep(SYSTEM_CONFIG["delay"])

            RUNNING_TASKS[chat_id] = False
            return

        # --- LỆNH: .del ---
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

        # --- LỆNH: .xoahet / .purge ---
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
                        await asyncio.sleep(0.1)
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

    print("=" * 60)
    print(f"[*] HỆ THỐNG ĐIỀU HÀNH FILE ANH KHÔI 2026 ĐÃ KHỞI CHẠY!")
    print(f"[*] Tài khoản Bot: {me.first_name} | @{me.username} | ID: {me.id}")
    print(f"[*] Vận tốc xả đòn: {SYSTEM_CONFIG['delay']}s | Nghỉ hạ nhiệt: {SYSTEM_CONFIG['rest_time']}s")
    print(f"[*] Chế độ Zalgo Lag Máy: {SYSTEM_CONFIG['glitch_mode']}")
    print("=" * 60)

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
