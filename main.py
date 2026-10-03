import os
import sys
import re
import random
import asyncio
from aiohttp import web
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, MessageDeleteForbiddenError

# ==================== CẤU HÌNH HỆ THỐNG ANH KHÔI ====================
API_ID = int(os.environ.get("API_ID", 32906102))
API_HASH = os.environ.get("API_HASH", "9fc3add5b6bf34cc5335a85388f34a0f")

DEFAULT_SESSION = "1BVtsOIIBuxPBTJcjHmwH5MpU1DO068XwGFkdO2mxIdbqKtMt_-u3_jQkzaUUDCLtD_-HOZ2NTkXI0cDQistaYUm13b3uR-K_vRgXK168mNbiYd7selpS9nUa4NGQSfZSVu_LuhFmYmJK1kmcXJUD41QdOjuV4Otw-_-CZNk_hL-WiDIe4kX4_7hPdPuis1gm4ysRUsVokf0lBwlhXIwVEggOUTcQ8WAFzzQhDZFxZ6Xqqc74837vt05JS9PnLIRDG-dliqgNC4JRXioFTap8rczjaMYTKmcIk47Rb9M59vzjTCc1CwwqhE5tix0HbBElSdY_R7OFC2jMbCwykCnI__U7OsmUhNs="
SESSION_STRING = os.environ.get("SESSION_STRING", "").strip() or DEFAULT_SESSION

PORT = int(os.environ.get("PORT", 8080))
PREFIX = "."  # Tiền tố lệnh

# Cấu hình Tường Lửa Ghost-Shield v5
SYSTEM_CONFIG = {
    "delay": 0.5,          # Tốc độ siêu nhanh 0.5s mặc định
    "use_icons": True,     # Bật icon chọc tức độc dị
    "batch_rest": 12,      # Cứ 12 tin nghỉ xả nhiệt
    "rest_time": 5.0,      # Thời gian nghỉ xả nhiệt (giây)
    "typing_sim": True     # Giả lập gõ phím
}

RUNNING_TASKS = {}
MY_ID = None

# Kho Icon Meme Khinh Bỉ + Cyber Warlord + Bát Quái
MEME_ICONS = ["🤡", "🫵", "💀", "🤫", "🧏‍♂️", "💩", "🐸", "😹", "🤪", "👌", "👻", "😈", "🦴", "🚮", "🥱", "🖕"]
CYBER_ICONS = ["亗", "𖤍", "🜲", "𒆜", "☬", "⚡", "𒀱", "𓊈☠︎𓊉", "☣", "𖤐", "⚜", "𖣘", "☯", "☸"]
BATQUAI_SYMBOLS = ["☰", "☱", "☲", "☳", "☴", "☵", "☶", "☷"]

# Ký tự vô hình & Đổi hướng chống thuật toán quét Hash
INVISIBLE_CHARS = ["\u200b", "\u200c", "\u200d", "\ufeff", "\u2060", "\u200e", "\u200f"]

# Bảng dấu Zalgo Unicode Combining siêu nặng làm lag khung hình render
ZALGO_UP = [chr(i) for i in range(0x0300, 0x0315)]
ZALGO_DOWN = [chr(i) for i in range(0x0316, 0x0330)]
ZALGO_MID = [chr(i) for i in range(0x0334, 0x0339)]

def make_zalgo(text: str, intensity: int = 3) -> str:
    """Bơm ký tự ma quái Zalgo vào từng chữ cái gây quá tải render"""
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
    """Tạo mã Hash duy nhất từng tin nhắn bằng Zero-Width Entropy Injection"""
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
    """Tự động phân loại số thứ tự đầu dòng (1., 2), 3-...), sắp xếp và cắt số"""
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

async def safe_edit_or_reply(event, text):
    """Sửa tin nhắn của chính mình, nếu nhóm cấm sửa thì reply"""
    try:
        await event.edit(text)
    except Exception:
        try:
            await event.reply(text)
        except Exception:
            pass

# ==================== MÁY CHỦ WEB CHO RENDER ====================
async def handle_health(request):
    return web.Response(
        text="ANH KHOI PRO MAX BAT QUAI TRAN\nSPEED: 0.5S TURBO\nFIREWALL: ULTRA ACTIVE 24/7",
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
    print(f"[*] Web Server đã kích hoạt trên Port {PORT}")

# ==================== KHỞI TẠO TELETHON CLIENT ====================
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== BỘ ĐIỀU PHỐI TIN NHẮN TẬP TRUNG ====================
@client.on(events.NewMessage)
async def central_handler(event):
    global MY_ID

    try:
        # 1. Tự động lưu file .txt khi gửi vào chat
        if (event.out or event.sender_id == MY_ID) and event.message.file:
            fname = getattr(event.message.file, "name", None)
            if fname and str(fname).lower().endswith(".txt"):
                save_path = await event.message.download_media(file=fname)
                print(f"[*] Tự động nhận file: {save_path}")
                return

        # 2. Chỉ nhận lệnh từ chính chủ
        if not event.out and event.sender_id != MY_ID:
            return

        raw_text = (event.message.message or "").strip()
        if not raw_text.startswith(PREFIX):
            return

        parts = raw_text.split()
        cmd = parts[0].lower()
        args = parts[1:]
        chat_id = event.chat_id

        # --- LỆNH: .ping ---
        if cmd == f"{PREFIX}ping":
            await safe_edit_or_reply(
                event,
                f"⚡ **ANH KHÔI BÁT QUÁI TRẬN – PRO MAX 2026!** 🤡🫵\n"
                f"🛡️ **Firewall Anti-Ban:** `GHOST-SHIELD V5 ULTRA`\n"
                f"⏱️ **Tốc độ xung trận:** `{SYSTEM_CONFIG['delay']}s/đòn`\n"
                f"🎭 **Icon Chọc Tức:** `{'BẬT 🔥' if SYSTEM_CONFIG['use_icons'] else 'TẮT ⚪'}`\n"
                f"🌐 **Server:** `Online 24/7 Render`"
            )
            return

        # --- LỆNH: .help / .lenh ---
        if cmd in [f"{PREFIX}help", f"{PREFIX}lenh"]:
            menu = (
                "👑 **HỆ THỐNG BÁT QUÁI TRẬN - ANH KHÔI 2026** 🤪👌\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "**📁 QUẢN LÝ FILE:**\n"
                f"• Gửi file `.txt` vào chat -> Máy chủ tự lưu ngay\n"
                f"• `{PREFIX}luufile [tên]` (Reply file) : Tải và đổi tên\n"
                f"• `{PREFIX}dsfile` : Xem danh sách file hiện có\n"
                f"• `{PREFIX}xemfile <tên>` : Đọc trước nội dung file\n"
                f"• `{PREFIX}xoafile <tên>` : Xóa file khỏi máy chủ\n\n"
                "**🔥 HỎA LỰC 0.5S & TREO NGÔN BÁT QUÁI:**\n"
                f"• `{PREFIX}xaf <tên_file>` : Xả đòn 0.5s theo thứ tự file\n"
                f"• `{PREFIX}treongon <tên_file>` : Treo ngôn vô tận xoay vòng 24/7\n"
                f"• `{PREFIX}xalap <nội dung> [số]` : Xả liên thanh 1 câu cực nhanh\n"
                f"• `{PREFIX}dung` : Đình chỉ mọi luồng xả / treo lập tức\n\n"
                "**🌀 MA QUÁI & HIỆU ỨNG LAG MÁY:**\n"
                f"• `{PREFIX}batquai <nội dung>` : Trận pháp xoay vần 8 quẻ Kinh Dịch\n"
                f"• `{PREFIX}glitch <nội dung>` : Bơm Zalgo ma quái giật khung hình\n"
                f"• `{PREFIX}type <văn bản>` : Gõ phím ma quái từng ký tự\n\n"
                "**🛡️ ANTI-BAN & ĐIỀU TỐC:**\n"
                f"• `{PREFIX}delay <giây>` : Chỉnh giây (Xuống tới `0.5s`)\n"
                f"• `{PREFIX}icon` : Bật/Tắt dàn icon chọc tức 🤡🫵💀\n\n"
                "**🧹 THANH TRỪNG TIN NHẮN:**\n"
                f"• `{PREFIX}del [số]` : Xóa tin nhắn của chính mình\n"
                f"• `{PREFIX}xoahet` (Reply tin) : Quét sạch tin từ điểm reply"
            )
            await safe_edit_or_reply(event, menu)
            return

        # --- LỆNH: .delay (HỖ TRỢ XUỐNG 0.5s) ---
        if cmd == f"{PREFIX}delay":
            if not args:
                return await safe_edit_or_reply(event, f"⏱️️ Delay hiện tại: `{SYSTEM_CONFIG['delay']}s/đòn`")
            try:
                val = float(args[0])
                if val < 0.3:
                    return await safe_edit_or_reply(event, "⚠️ **Firewall chặn:** Giới hạn an toàn tối thiểu là `0.3s - 0.5s` để tránh ăn gậy từ Telegram!")
                SYSTEM_CONFIG["delay"] = val
                await safe_edit_or_reply(event, f"🛡️ Đã thiết lập vận tốc siêu tốc: `{val}s/đòn` ⚡")
            except Exception:
                await safe_edit_or_reply(event, "❌ Số giây không hợp lệ!")
            return

        # --- LỆNH: .icon ---
        if cmd == f"{PREFIX}icon":
            SYSTEM_CONFIG["use_icons"] = not SYSTEM_CONFIG["use_icons"]
            st = "BẬT 🤡🫵💀" if SYSTEM_CONFIG["use_icons"] else "TẮT ⚪"
            await safe_edit_or_reply(event, f"𖤍 Dàn Icon chọc tức: **{st}**")
            return

        # --- LỆNH: .batquai (TRẬN PHÁP 8 QUẺ KINH DỊCH) ---
        if cmd == f"{PREFIX}batquai":
            if not args:
                return await safe_edit_or_reply(event, f"💡 Cú pháp: `{PREFIX}batquai <nội dung>`")
            content = " ".join(args)
            for i in range(8):
                q = BATQUAI_SYMBOLS[i % len(BATQUAI_SYMBOLS)]
                glitch_mark = random.choice(MEME_ICONS)
                display = f"☯ 亗 [ BÁT QUÁI TRẬN: {q} ] 亗 ☯\n👉 {content} 👈\n{glitch_mark} {BATQUAI_SYMBOLS[(i+2)%8]} ANH KHÔI ĐỘC TÔN {BATQUAI_SYMBOLS[(i+4)%8]} {glitch_mark}"
                try:
                    await event.edit(display)
                    await asyncio.sleep(0.12)
                except Exception:
                    pass
            return

        # --- LỆNH: .glitch / .lagma (BƠM ZALGO MA QUÁI NẶNG RENDER) ---
        if cmd in [f"{PREFIX}glitch", f"{PREFIX}lagma"]:
            if not args:
                return await safe_edit_or_reply(event, f"💡 Cú pháp: `{PREFIX}glitch <nội dung>`")
            raw_text = " ".join(args)
            # Tạo 3 tầng Zalgo cực mạnh
            heavy_zalgo = make_zalgo(raw_text, intensity=4)
            stealth_payload = generate_stealth_text(heavy_zalgo)
            await safe_edit_or_reply(event, f"☠︎ 𖤍 {stealth_payload} 𖤍 ☠︎")
            return

        # --- LỆNH: .type ---
        if cmd == f"{PREFIX}type":
            if not args:
                return
            text_to_type = generate_stealth_text(" ".join(args))
            typing_symbol = "▌"
            current_text = ""
            for char in text_to_type:
                current_text += char
                try:
                    await event.edit(current_text + typing_symbol)
                    await asyncio.sleep(random.uniform(0.03, 0.06))
                except Exception:
                    pass
            try:
                await event.edit(current_text)
            except Exception:
                pass
            return

        # --- LỆNH: .dsfile, .luufile, .xemfile, .xoafile ---
        if cmd == f"{PREFIX}dsfile":
            files = [f for f in os.listdir(".") if os.path.isfile(f)]
            if not files:
                return await safe_edit_or_reply(event, "📁 Server chưa có file nào.")
            ds = "\n".join([f"• `{f}` ({os.path.getsize(f)} bytes)" for f in files[:35]])
            await safe_edit_or_reply(event, f"📁 **DANH SÁCH FILE TRÊN SERVER:**\n{ds}")
            return

        if cmd == f"{PREFIX}luufile":
            reply = await event.get_reply_message()
            target_msg = reply if (reply and reply.media) else event.message
            if not target_msg.media:
                return await safe_edit_or_reply(event, "❌ Hãy gửi kèm file hoặc Reply vào tin nhắn chứa file!")
            custom_name = args[0] if args else ""
            await safe_edit_or_reply(event, "⏳ Đang tải file về máy chủ...")
            saved_path = await target_msg.download_media(file=custom_name or "")
            if saved_path:
                fname = os.path.basename(saved_path)
                await safe_edit_or_reply(event, f"✅ **ĐÃ LƯU FILE!**\n📁 Tên: `{fname}`\n👉 Bắt đầu xả: `{PREFIX}xaf {fname}`")
            else:
                await safe_edit_or_reply(event, "❌ Lưu file thất bại!")
            return

        if cmd == f"{PREFIX}xemfile":
            if not args:
                return await safe_edit_or_reply(event, f"💡 Cú pháp: `{PREFIX}xemfile <tên_file>`")
            fname = args[0]
            if not os.path.exists(fname):
                return await safe_edit_or_reply(event, f"❌ Không tìm thấy file `{fname}`!")
            try:
                with open(fname, "r", encoding="utf-8", errors="ignore") as f:
                    data = f.read(3000)
                await safe_edit_or_reply(event, f"📄 **NỘI DUNG `{fname}`:**\n```\n{data}\n```")
            except Exception as e:
                await safe_edit_or_reply(event, f"❌ Lỗi đọc file: {e}")
            return

        if cmd == f"{PREFIX}xoafile":
            if not args:
                return await safe_edit_or_reply(event, f"💡 Cú pháp: `{PREFIX}xoafile <tên_file>`")
            fname = args[0]
            if fname in ["main.py", "requirements.txt"]:
                return await safe_edit_or_reply(event, "⚠️ Không được xóa file gốc hệ thống!")
            if not os.path.exists(fname):
                return await safe_edit_or_reply(event, f"❌ File `{fname}` không tồn tại.")
            try:
                os.remove(fname)
                await safe_edit_or_reply(event, f"🗑️ Đã xóa file `{fname}` thành công!")
            except Exception as e:
                await safe_edit_or_reply(event, f"❌ Lỗi: {e}")
            return

        # --- LỆNH: .dung / .stop ---
        if cmd in [f"{PREFIX}dung", f"{PREFIX}stop"]:
            if RUNNING_TASKS.get(chat_id):
                RUNNING_TASKS[chat_id] = False
                await safe_edit_or_reply(event, "🛑 **ĐÃ THU HỒI TRẬN PHÁP – TOÀN BỘ LUỒNG ĐÃ DỪNG!**")
            else:
                await safe_edit_or_reply(event, "⚠️ Không có tác vụ nào đang chạy tại đoạn chat này.")
            return

        # --- LỆNH: .xaf (TỐC ĐỘ 0.5S SIÊU TỐC) ---
        if cmd == f"{PREFIX}xaf":
            if not args:
                return await safe_edit_or_reply(event, f"💡 Cú pháp: `{PREFIX}xaf <tên_file>`")
            fname = args[0]
            if not os.path.exists(fname):
                return await safe_edit_or_reply(event, f"❌ Không tìm thấy file `{fname}`! Hãy gửi file vào chat để bot lưu.")
            try:
                with open(fname, "r", encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
            except Exception as e:
                return await safe_edit_or_reply(event, f"❌ Lỗi đọc file: {e}")

            lines = parse_and_sort_file(raw)
            if not lines:
                return await safe_edit_or_reply(event, "⚠️ File không có nội dung hợp lệ!")

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
                        if SYSTEM_CONFIG["typing_sim"]:
                            async with client.action(chat_id, "typing"):
                                await asyncio.sleep(0.08)
                        await client.send_message(chat_id, final_msg)
                        sent = True
                        count += 1
                    except FloodWaitError as e:
                        print(f"[FIREWALL] Bắt gặp FloodWait! Ngủ {e.seconds}s bảo toàn tài khoản...")
                        await asyncio.sleep(e.seconds + 2)
                    except Exception as e:
                        print(f"[LỖI GỬI]: {e}")
                        await asyncio.sleep(0.5)
                        break

                # Xả nhiệt định kỳ
                if count % SYSTEM_CONFIG["batch_rest"] == 0 and RUNNING_TASKS.get(chat_id):
                    await asyncio.sleep(SYSTEM_CONFIG["rest_time"])

                # Jitter ngẫu nhiên giữ nhịp an toàn ở tốc độ cao
                jitter = random.uniform(0.05, 0.15)
                await asyncio.sleep(SYSTEM_CONFIG["delay"] + jitter)

            RUNNING_TASKS[chat_id] = False
            return

        # --- LỆNH: .treongon (XOAY VÒNG 24/7) ---
        if cmd == f"{PREFIX}treongon":
            if not args:
                return await safe_edit_or_reply(event, f"💡 Cú pháp: `{PREFIX}treongon <tên_file>`")
            fname = args[0]
            if not os.path.exists(fname):
                return await safe_edit_or_reply(event, f"❌ File `{fname}` không tồn tại!")
            try:
                with open(fname, "r", encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
            except Exception as e:
                return await safe_edit_or_reply(event, f"❌ Lỗi đọc file: {e}")

            lines = parse_and_sort_file(raw)
            if not lines:
                return await safe_edit_or_reply(event, "⚠️ File rỗng!")

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
                        if SYSTEM_CONFIG["typing_sim"]:
                            async with client.action(chat_id, "typing"):
                                await asyncio.sleep(0.08)
                        await client.send_message(chat_id, final_msg)
                        sent = True
                        count += 1
                    except FloodWaitError as e:
                        await asyncio.sleep(e.seconds + 2)
                    except Exception:
                        await asyncio.sleep(0.8)
                        break

                idx = (idx + 1) % total_lines
                if count % SYSTEM_CONFIG["batch_rest"] == 0 and RUNNING_TASKS.get(chat_id):
                    await asyncio.sleep(SYSTEM_CONFIG["rest_time"])

                jitter = random.uniform(0.05, 0.2)
                await asyncio.sleep(SYSTEM_CONFIG["delay"] + jitter)

            RUNNING_TASKS[chat_id] = False
            return

        # --- LỆNH: .xalap ---
        if cmd == f"{PREFIX}xalap":
            if not args:
                return await safe_edit_or_reply(event, f"💡 Cú pháp: `{PREFIX}xalap <nội dung> [số lần]`")
            times = 20
            if args[-1].isdigit():
                times = int(args[-1])
                content = " ".join(args[:-1])
            else:
                content = " ".join(args)

            try:
                await event.delete()
            except Exception:
                pass

            RUNNING_TASKS[chat_id] = True
            for i in range(times):
                if not RUNNING_TASKS.get(chat_id):
                    break
                final_msg = generate_stealth_text(content)
                sent = False
                while not sent and RUNNING_TASKS.get(chat_id):
                    try:
                        if SYSTEM_CONFIG["typing_sim"]:
                            async with client.action(chat_id, "typing"):
                                await asyncio.sleep(0.05)
                        await client.send_message(chat_id, final_msg)
                        sent = True
                    except FloodWaitError as e:
                        await asyncio.sleep(e.seconds + 2)
                    except Exception:
                        await asyncio.sleep(0.5)
                        break

                if (i + 1) % SYSTEM_CONFIG["batch_rest"] == 0 and RUNNING_TASKS.get(chat_id):
                    await asyncio.sleep(SYSTEM_CONFIG["rest_time"])

                jitter = random.uniform(0.05, 0.15)
                await asyncio.sleep(SYSTEM_CONFIG["delay"] + jitter)

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
                    await asyncio.sleep(0.05)
                except Exception:
                    pass
            return

        # --- LỆNH: .xoahet / .purge ---
        if cmd in [f"{PREFIX}xoahet", f"{PREFIX}purge"]:
            reply = await event.get_reply_message()
            if not reply:
                return await safe_edit_or_reply(event, "💡 Hãy **Reply** vào tin nhắn bắt đầu muốn xóa rồi gõ `.xoahet`")
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
                        await asyncio.sleep(0.12)
                    except MessageDeleteForbiddenError:
                        pass
            return

    except Exception as e:
        print(f"[LỖI XỬ LÝ SỰ KIỆN]: {e}")

# ==================== KHỞI ĐỘNG HỆ THỐNG ====================
async def main():
    global MY_ID
    await start_web_server()
    await client.start()

    me = await client.get_me()
    MY_ID = me.id
    print("=" * 60)
    print(f"[*] BÁT QUÁI TRẬN ANH KHÔI ĐÃ SẴN SÀNG CHIẾN ĐẤU!")
    print(f"[*] Tài khoản: {me.first_name} | @{me.username} | ID: {me.id}")
    print(f"[*] Tốc độ xung trận: {SYSTEM_CONFIG['delay']}s/đòn | Ghost-Shield v5: BẬT")
    print("=" * 60)

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
