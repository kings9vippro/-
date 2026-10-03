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

# ==================== TƯỜNG LỬA & ANTI-BAN CỰC HẠN ====================
SYSTEM_CONFIG = {
    "delay": 1.2,          # Delay an toàn giữa các tin (giây)
    "use_icons": True,     # Bật icon chọc tức
    "batch_rest": 10,      # Cứ sau 10 tin sẽ giải nhiệt
    "rest_time": 2.0,      # Thời gian nghỉ giải nhiệt (giây)
    "typing_sim": True     # Mô phỏng gõ phím như người thật
}

RUNNING_TASKS = {}
MY_ID = None  # Sẽ tự gán khi bot kết nối

MEME_ICONS = ["🤪", "👌", "👻", "😹", "🤡", "💀", "🫵", "🔥", "🤫", "🧏‍♂️", "💩", "🐸", "😈", "🦴", "🚮"]
CYBER_ICONS = ["亗", "𖤍", "🜲", "𒆜", "☬", "⚡", "𒀱", "𓊈☠︎𓊉", "☣", "𖤐", "⚜", "𖣘"]
INVISIBLE_CHARS = ["\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"]

def generate_stealth_text(text: str) -> str:
    """Bơm ký tự tàng hình biến đổi mã Hash + Icon chọc tức"""
    words = text.split(" ")
    salted = []
    for w in words:
        salt = "".join(random.choices(INVISIBLE_CHARS, k=random.randint(1, 3)))
        salted.append(f"{w}{salt}")
    core = " ".join(salted)

    if SYSTEM_CONFIG["use_icons"]:
        ic_l = f"{random.choice(CYBER_ICONS)} {random.choice(MEME_ICONS)}"
        ic_r = f"{random.choice(MEME_ICONS)} {random.choice(CYBER_ICONS)}"
        return f"{ic_l} {core} {ic_r}"
    return core

def parse_and_sort_file(content: str) -> list:
    """Tự động phát hiện số thứ tự đầu dòng, sắp xếp từ nhỏ đến lớn và xóa số"""
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
    """An toàn: Thử sửa tin nhắn của mình, nếu nhóm cấm sửa thì chuyển sang reply"""
    try:
        await event.edit(text)
    except Exception:
        try:
            await event.reply(text)
        except Exception as e:
            print(f"[!] Không thể phản hồi tin nhắn: {e}")

# ==================== MÁY CHỦ WEB CHO RENDER ====================
async def handle_health(request):
    return web.Response(
        text="ANH KHOI PRO USERBOT V12\nSTATUS: ONLINE 24/7\nFIREWALL: ULTRA ACTIVE",
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
    print(f"[*] Web Server đã mở Port {PORT}")

# ==================== KHỞI TẠO TELETHON CLIENT ====================
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== BỘ ĐIỀU PHỐI TIN NHẮN TẬP TRUNG ====================
@client.on(events.NewMessage)
async def central_message_handler(event):
    global MY_ID
    
    # 1. Bắt file gửi tự động nếu là file .txt
    if (event.out or event.sender_id == MY_ID) and event.message.file and event.message.file.name:
        fname = event.message.file.name
        if fname.lower().endswith(".txt"):
            save_path = await event.message.download_media(file=fname)
            print(f"[*] Tự động tải và lưu file: {save_path}")
            return

    # 2. Kiểm tra quyền chính chủ (chấp nhận cả tin từ điện thoại / máy tính)
    if not event.out and event.sender_id != MY_ID:
        return

    raw_text = (event.raw_text or "").strip()
    if not raw_text.startswith(PREFIX):
        return

    # Tách lệnh và tham số (không bị lỗi bởi dấu cách hay chữ hoa/thường)
    parts = raw_text.split()
    cmd = parts[0].lower()
    args = parts[1:]
    chat_id = event.chat_id

    print(f"[*] [NHẬN LỆNH]: {cmd} | Tham số: {args} | Tại Chat: {chat_id}")

    # --- LỆNH: .ping ---
    if cmd == f"{PREFIX}ping":
        await safe_edit_or_reply(
            event,
            f"⚡ **ANH KHÔI USERBOT ĐANG ONLINE!** 🤡🫵\n"
            f"🛡️️ **Anti-Ban:** `BẬT CỰC HẠN` | **Delay:** `{SYSTEM_CONFIG['delay']}s`\n"
            f"🎭 **Icon Chọc Tức:** `{'BẬT 🔥' if SYSTEM_CONFIG['use_icons'] else 'TẮT ⚪'}`"
        )
        return

    # --- LỆNH: .help / .lenh ---
    if cmd in [f"{PREFIX}help", f"{PREFIX}lenh"]:
        menu = (
            "👑 **BẢNG ĐIỀU KHIỂN PRO VIP 2026 - PHẠM ANH KHÔI** 🤪👌\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "**📁 QUẢN LÝ FILE:**\n"
            f"• Gửi file `.txt` vào chat -> Tự lưu về server\n"
            f"• `{PREFIX}luufile [tên]` (Reply file) : Lưu và đổi tên\n"
            f"• `{PREFIX}dsfile` : Danh sách file trên host\n"
            f"• `{PREFIX}xemfile <tên>` : Đọc trước file\n"
            f"• `{PREFIX}xoafile <tên>` : Xóa file trên máy chủ\n\n"
            "**🔥 HỎA LỰC XẢ GÕ & TREO NGÔN:**\n"
            f"• `{PREFIX}xaf <tên_file>` : Xả 1 lượt (tự xóa số thứ tự đầu dòng)\n"
            f"• `{PREFIX}treongon <tên_file>` : Treo xoay vòng vô tận\n"
            f"• `{PREFIX}xalap <nội dung> [số]` : Xả lặp lại 1 câu nhiều lần\n"
            f"• `{PREFIX}type <văn bản>` : Hiệu ứng gõ phím ma quái\n"
            f"• `{PREFIX}dung` : Dừng ngay lập tức mọi luồng xả\n\n"
            "**🛡️ FIREWALL & GIAO DIỆN:**\n"
            f"• `{PREFIX}delay <giây>` : Cài giây an toàn (VD: `{PREFIX}delay 1.0`)\n"
            f"• `{PREFIX}icon` : Bật/Tắt icon chọc tức 🤡🫵💀\n\n"
            "**🧹 DỌN DẸP TIN NHẮN:**\n"
            f"• `{PREFIX}del [số]` : Xóa tin nhắn của chính mình\n"
            f"• `{PREFIX}xoahet` (Reply tin) : Quét sạch từ tin reply đến nay"
        )
        await safe_edit_or_reply(event, menu)
        return

    # --- LỆNH: .dsfile ---
    if cmd == f"{PREFIX}dsfile":
        files = [f for f in os.listdir(".") if os.path.isfile(f)]
        if not files:
            return await safe_edit_or_reply(event, "📁 Server chưa có file nào.")
        ds = "\n".join([f"• `{f}` ({os.path.getsize(f)} bytes)" for f in files[:35]])
        await safe_edit_or_reply(event, f"📁 **DANH SÁCH FILE TRÊN SERVER:**\n{ds}")
        return

    # --- LỆNH: .luufile ---
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

    # --- LỆNH: .xemfile ---
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
            await safe_edit_or_reply(event, f"❌ Lỗi: {e}")
        return

    # --- LỆNH: .xoafile ---
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

    # --- LỆNH: .delay ---
    if cmd == f"{PREFIX}delay":
        if not args:
            return await safe_edit_or_reply(event, f"⏱️ Delay hiện tại: `{SYSTEM_CONFIG['delay']}s/tin`")
        try:
            val = float(args[0])
            if val < 0.2:
                return await safe_edit_or_reply(event, "⚠️ **Firewall chặn:** Không chỉnh dưới `0.2s` để tránh bị ban!")
            SYSTEM_CONFIG["delay"] = val
            await safe_edit_or_reply(event, f"🛡️ Đã cài Delay mới: `{val}s/tin`")
        except:
            await safe_edit_or_reply(event, "❌ Số giây không hợp lệ!")
        return

    # --- LỆNH: .icon ---
    if cmd == f"{PREFIX}icon":
        SYSTEM_CONFIG["use_icons"] = not SYSTEM_CONFIG["use_icons"]
        st = "BẬT 🤡🫵💀" if SYSTEM_CONFIG["use_icons"] else "TẮT ⚪"
        await safe_edit_or_reply(event, f"𖤍 Dàn Icon chọc tức: **{st}**")
        return

    # --- LỆNH: .dung / .stop ---
    if cmd in [f"{PREFIX}dung", f"{PREFIX}stop"]:
        if RUNNING_TASKS.get(chat_id):
            RUNNING_TASKS[chat_id] = False
            await safe_edit_or_reply(event, "🛑 **ĐÃ ĐÌNH CHỈ TOÀN BỘ LUỒNG TẠI ĐÂY!**")
        else:
            await safe_edit_or_reply(event, "⚠️️ Không có tác vụ xả/treo nào đang chạy.")
        return

    # --- LỆNH: .xaf ---
    if cmd == f"{PREFIX}xaf":
        if not args:
            return await safe_edit_or_reply(event, f"💡 Cú pháp: `{PREFIX}xaf <tên_file>`")
        fname = args[0]
        if not os.path.exists(fname):
            return await safe_edit_or_reply(event, f"❌ Không tìm thấy file `{fname}`! Hãy gửi file vào chat để server lưu.")
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
                            await asyncio.sleep(0.18)
                    await client.send_message(chat_id, final_msg)
                    sent = True
                    count += 1
                except FloodWaitError as e:
                    print(f"[FIREWALL] Bắt gặp FloodWait! Ngủ {e.seconds}s...")
                    await asyncio.sleep(e.seconds + 2)
                except Exception as e:
                    print(f"[LỖI GỬI]: {e}")
                    await asyncio.sleep(1)
                    break

            if count % SYSTEM_CONFIG["batch_rest"] == 0 and RUNNING_TASKS.get(chat_id):
                await asyncio.sleep(SYSTEM_CONFIG["rest_time"])

            jitter = random.uniform(0.1, 0.35)
            await asyncio.sleep(SYSTEM_CONFIG["delay"] + jitter)

        RUNNING_TASKS[chat_id] = False
        return

    # --- LỆNH: .treongon ---
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
                            await asyncio.sleep(0.2)
                    await client.send_message(chat_id, final_msg)
                    sent = True
                    count += 1
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds + 2)
                except Exception:
                    await asyncio.sleep(1.2)
                    break

            idx = (idx + 1) % total_lines
            if count % SYSTEM_CONFIG["batch_rest"] == 0 and RUNNING_TASKS.get(chat_id):
                await asyncio.sleep(SYSTEM_CONFIG["rest_time"])

            jitter = random.uniform(0.15, 0.4)
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
                            await asyncio.sleep(0.15)
                    await client.send_message(chat_id, final_msg)
                    sent = True
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds + 2)
                except Exception:
                    await asyncio.sleep(1)
                    break

            if (i + 1) % SYSTEM_CONFIG["batch_rest"] == 0 and RUNNING_TASKS.get(chat_id):
                await asyncio.sleep(SYSTEM_CONFIG["rest_time"])

            jitter = random.uniform(0.1, 0.3)
            await asyncio.sleep(SYSTEM_CONFIG["delay"] + jitter)

        RUNNING_TASKS[chat_id] = False
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
                await asyncio.sleep(random.uniform(0.04, 0.08))
            except Exception:
                pass
        try:
            await event.edit(current_text)
        except Exception:
            pass
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
                await asyncio.sleep(0.08)
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
                    await asyncio.sleep(0.15)
                except MessageDeleteForbiddenError:
                    pass
        return

# ==================== ENTRYPOINT ====================
async def main():
    global MY_ID
    await start_web_server()
    await client.connect()
    
    if not await client.is_user_authorized():
        print("[!] LỖI: Chuỗi SESSION_STRING không hợp lệ hoặc đã bị đăng xuất!")
        return

    me = await client.get_me()
    MY_ID = me.id
    print("=" * 55)
    print(f"[*] USERBOT ANH KHÔI KHỞI ĐỘNG THÀNH CÔNG!")
    print(f"[*] Tài khoản: {me.first_name} | @{me.username} | ID: {me.id}")
    print("=" * 55)

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
