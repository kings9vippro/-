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

# Chuỗi phiên bản quyền bảo mật
DEFAULT_SESSION = "1BVtsOIIBuxPBTJcjHmwH5MpU1DO068XwGFkdO2mxIdbqKtMt_-u3_jQkzaUUDCLtD_-HOZ2NTkXI0cDQistaYUm13b3uR-K_vRgXK168mNbiYd7selpS9nUa4NGQSfZSVu_LuhFmYmJK1kmcXJUD41QdOjuV4Otw-_-CZNk_hL-WiDIe4kX4_7hPdPuis1gm4ysRUsVokf0lBwlhXIwVEggOUTcQ8WAFzzQhDZFxZ6Xqqc74837vt05JS9PnLIRDG-dliqgNC4JRXioFTap8rczjaMYTKmcIk47Rb9M59vzjTCc1CwwqhE5tix0HbBElSdY_R7OFC2jMbCwykCnI__U7OsmUhNs="
SESSION_STRING = os.environ.get("SESSION_STRING", "").strip() or DEFAULT_SESSION

PORT = int(os.environ.get("PORT", 8080))
PREFIX = "."  # Tiền tố lệnh

# ==================== TƯỜNG LỬA & ANTI-BAN CẤP CAO ====================
SYSTEM_CONFIG = {
    "delay": 1.2,          # Delay an toàn giữa các tin (giây)
    "use_icons": True,     # Bật icon chọc tức
    "batch_rest": 10,      # Cứ sau 10 tin sẽ kích hoạt hạ nhiệt
    "rest_time": 6.5,      # Thời gian nghỉ xả nhiệt (giây)
    "typing_sim": True     # Mô phỏng trạng thái typing như người thật
}

RUNNING_TASKS = {}  # Quản lý luồng theo chat_id

# Bảng icon kết hợp Meme chọc tức + Cyber Gothic
MEME_ICONS = ["🤪", "👌", "👻", "😹", "🤡", "💀", "🫵", "🔥", "🤫", "🧏‍♂️", "💩", "🐸", "😈", "🦴", "🚮"]
CYBER_ICONS = ["亗", "𖤍", "🜲", "𒆜", "☬", "⚡", "𒀱", "𓊈☠︎𓊉", "☣", "𖤐", "⚜", "𖣘"]
INVISIBLE_CHARS = ["\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"]

def generate_stealth_text(text: str) -> str:
    """Đột biến mã Hash chống thuật toán bắt trùng nội dung của Telegram"""
    # 1. Trộn ngẫu nhiên ký tự vô hình vào giữa các từ
    words = text.split(" ")
    salted_words = []
    for w in words:
        salt = "".join(random.choices(INVISIBLE_CHARS, k=random.randint(1, 3)))
        salted_words.append(f"{w}{salt}")
    core_text = " ".join(salted_words)

    # 2. Bọc icon chọc tức hai đầu
    if SYSTEM_CONFIG["use_icons"]:
        ic_left = f"{random.choice(CYBER_ICONS)} {random.choice(MEME_ICONS)}"
        ic_right = f"{random.choice(MEME_ICONS)} {random.choice(CYBER_ICONS)}"
        return f"{ic_left} {core_text} {ic_right}"
    return core_text

def parse_and_sort_file(content: str) -> list:
    """Tự động nhận biết số thứ tự đầu dòng (1., 2), 3-...), sắp xếp chuẩn và loại bỏ số"""
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

# ==================== MÁY CHỦ GIỮ RENDER 24/7 ====================
async def handle_health(request):
    return web.Response(
        text="ANH KHOI PRO USERBOT 2026\nSTATUS: ONLINE 24/7 ON RENDER\nULTRA FIREWALL: ACTIVE",
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

# ==================== TỰ ĐỘNG BẮT FILE & LƯU ====================
@client.on(events.NewMessage(outgoing=True))
async def auto_catch_file(event):
    if event.message.file and event.message.file.name:
        fname = event.message.file.name
        if fname.lower().endswith(".txt"):
            save_path = await event.message.download_media(file=fname)
            print(f"[*] Đã nhận diện và lưu file tự động: {save_path}")

# ==================== CÁC LỆNH ĐIỀU KHIỂN ====================

# 1. KIỂM TRA TRẠNG THÁI (.ping)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}ping$"))
async def cmd_ping(event):
    await event.edit(
        f"⚡ **ANH KHÔI USERBOT PRO VIP ĐANG ONLINE!** 🤡🫵\n"
        f"🛡️ **Ultra Anti-Ban:** `BẬT CỰC HẠN`\n"
        f"⏱️ **Độ trễ:** `{SYSTEM_CONFIG['delay']}s` | **Icon Chọc Tức:** `{'BẬT 🔥' if SYSTEM_CONFIG['use_icons'] else 'TẮT ⚪'}`\n"
        f"🌐 **Server:** `Render 24/7 Active`"
    )

# 2. XEM BẢNG LỆNH (.help / .lenh)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}(help|lenh)$"))
async def cmd_help(event):
    menu = (
        "👑 **BẢNG ĐIỀU KHIỂN PRO VIP 2026 - PHẠM ANH KHÔI** 🤪👌\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "**📁 QUẢN LÝ FILE TIỆN LỢI:**\n"
        f"• Gửi file `.txt` vào chat -> Server tự tải lưu ngay lập tức\n"
        f"• `{PREFIX}luufile [tên]` (Reply file) : Tải và đổi tên file\n"
        f"• `{PREFIX}dsfile` : Danh sách toàn bộ file trên host\n"
        f"• `{PREFIX}xemfile <tên>` : Đọc trước nội dung file\n"
        f"• `{PREFIX}xoafile <tên>` : Xóa file khỏi máy chủ\n\n"
        "**🔥 HỎA LỰC XẢ GÕ & TREO NGÔN:**\n"
        f"• `{PREFIX}xaf <tên_file>` : Xả một lượt theo thứ tự file\n"
        f"• `{PREFIX}treongon <tên_file>` : Treo ngôn xoay vòng vô tận\n"
        f"• `{PREFIX}xalap <nội dung> [số]` : Xả lặp lại 1 câu nhiều lần\n"
        f"• `{PREFIX}type <văn bản>` : Hiệu ứng gõ phím từng ký tự\n"
        f"• `{PREFIX}dung` : Dừng lập tức mọi luồng xả / treo\n\n"
        "**🛡️ ANTI-BAN & GIAO DIỆN:**\n"
        f"• `{PREFIX}delay <giây>` : Chỉnh giây an toàn (VD: `{PREFIX}delay 1.0`)\n"
        f"• `{PREFIX}icon` : Bật/Tắt dàn icon 🤡🫵💀\n\n"
        "**🧹 QUÉT SẠCH TIN NHẮN:**\n"
        f"• `{PREFIX}del [số]` : Xóa tin nhắn chính mình\n"
        f"• `{PREFIX}xoahet` (Reply tin) : Quét sạch tin nhắn từ điểm reply"
    )
    await event.edit(menu)

# 3. LƯU, XEM & XÓA FILE
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}luufile(?:\s+(\S+))?"))
async def cmd_luufile(event):
    reply = await event.get_reply_message()
    target_msg = reply if (reply and reply.media) else event.message
    if not target_msg.media:
        return await event.edit("❌ Hãy gửi kèm file hoặc Reply vào tin nhắn chứa file!")

    custom_name = event.pattern_match.group(1)
    await event.edit("⏳ Đang tải file về máy chủ...")
    saved_path = await target_msg.download_media(file=custom_name or "")
    if saved_path:
        fname = os.path.basename(saved_path)
        sz = os.path.getsize(saved_path)
        await event.edit(f"✅ **ĐÃ LƯU FILE THÀNH CÔNG!**\n📁 Tên: `{fname}` ({sz} bytes)\n👉 Xả ngay: `{PREFIX}xaf {fname}`")
    else:
        await event.edit("❌ Lưu file thất bại!")

@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}dsfile$"))
async def cmd_dsfile(event):
    files = [f for f in os.listdir(".") if os.path.isfile(f)]
    if not files:
        return await event.edit("📁 Server chưa có file nào.")
    ds = "\n".join([f"• `{f}` ({os.path.getsize(f)} bytes)" for f in files[:35]])
    await event.edit(f"📁 **DANH SÁCH FILE TRÊN SERVER:**\n{ds}")

@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}xemfile\s+(\S+)"))
async def cmd_xemfile(event):
    fname = event.pattern_match.group(1)
    if not os.path.exists(fname):
        return await event.edit(f"❌ Không tìm thấy file `{fname}`!")
    try:
        with open(fname, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read(3000)
        await event.edit(f"📄 **NỘI DUNG `{fname}`:**\n```\n{data}\n```")
    except Exception as e:
        await event.edit(f"❌ Lỗi: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}xoafile\s+(\S+)"))
async def cmd_xoafile(event):
    fname = event.pattern_match.group(1)
    if fname in ["main.py", "requirements.txt"]:
        return await event.edit("⚠️ Không được xóa file gốc hệ thống!")
    if not os.path.exists(fname):
        return await event.edit(f"❌ File `{fname}` không tồn tại.")
    try:
        os.remove(fname)
        await event.edit(f"🗑️ Đã xóa file `{fname}` thành công!")
    except Exception as e:
        await event.edit(f"❌ Lỗi: {e}")

# 4. CÀI ĐẶT DELAY & BẬT/TẮT ICON
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}delay\s*(\S+)?"))
async def cmd_delay(event):
    v = event.pattern_match.group(1)
    if not v:
        return await event.edit(f"⏱️ Delay hiện tại: `{SYSTEM_CONFIG['delay']}s/tin`")
    try:
        val = float(v)
        if val < 0.2:
            return await event.edit("⚠️ **Firewall chặn:** Không chỉnh dưới `0.2s` để bảo vệ nick không bị ban số!")
        SYSTEM_CONFIG["delay"] = val
        await event.edit(f"🛡️ Đã cài Delay: `{val}s/tin`")
    except:
        await event.edit("❌ Giá trị không hợp lệ!")

@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}icon$"))
async def cmd_icon(event):
    SYSTEM_CONFIG["use_icons"] = not SYSTEM_CONFIG["use_icons"]
    st = "BẬT 🤡🫵💀" if SYSTEM_CONFIG["use_icons"] else "TẮT ⚪"
    await event.edit(f"𖤍 Dàn Icon chọc tức: **{st}**")

# 5. XẢ FILE THEO THỨ TỰ (.xaf <tên_file>)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}xaf\s+(\S+)"))
async def cmd_xaf(event):
    fname = event.pattern_match.group(1)
    chat_id = event.chat_id

    if not os.path.exists(fname):
        return await event.edit(f"❌ Không tìm thấy file `{fname}`! Hãy gửi file để server tự lưu.")

    try:
        with open(fname, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
    except Exception as e:
        return await event.edit(f"❌ Lỗi đọc file: {e}")

    lines = parse_and_sort_file(raw)
    if not lines:
        return await event.edit("⚠️ File không có dòng nội dung hợp lệ nào!")

    await event.delete()
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
                print(f"[FIREWALL] Bắt gặp FloodWait! Ngủ {e.seconds}s để bảo vệ tài khoản...")
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

# 6. TREO NGÔN VÔ TẬN XOAY VÒNG (.treongon <tên_file>)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}treongon\s+(\S+)"))
async def cmd_treongon(event):
    fname = event.pattern_match.group(1)
    chat_id = event.chat_id

    if not os.path.exists(fname):
        return await event.edit(f"❌ File `{fname}` không tồn tại!")

    try:
        with open(fname, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
    except Exception as e:
        return await event.edit(f"❌ Lỗi đọc file: {e}")

    lines = parse_and_sort_file(raw)
    if not lines:
        return await event.edit("⚠️ File không có nội dung!")

    await event.delete()
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
            except Exception as e:
                await asyncio.sleep(1.2)
                break

        idx = (idx + 1) % total_lines

        if count % SYSTEM_CONFIG["batch_rest"] == 0 and RUNNING_TASKS.get(chat_id):
            await asyncio.sleep(SYSTEM_CONFIG["rest_time"])

        jitter = random.uniform(0.15, 0.4)
        await asyncio.sleep(SYSTEM_CONFIG["delay"] + jitter)

    RUNNING_TASKS[chat_id] = False

# 7. XẢ LẶP 1 CÂU LIÊN HOÀN (.xalap <câu> [số_lần])
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}xalap\s+(.+?)(?:\s+(\d+))?$"))
async def cmd_xalap(event):
    content = event.pattern_match.group(1).strip()
    times = int(event.pattern_match.group(2) or 20)
    chat_id = event.chat_id

    await event.delete()
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

# 8. HIỆU ỨNG GÕ PHÍM MA QUÁI (.type <nội dung>)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}type\s+([\s\S]+)"))
async def cmd_typewriter(event):
    raw_text = event.pattern_match.group(1)
    text_to_type = generate_stealth_text(raw_text)
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

# 9. DỪNG TẤT CẢ LUỒNG (.dung / .stop)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}(dung|stop)$"))
async def cmd_dung(event):
    chat_id = event.chat_id
    if RUNNING_TASKS.get(chat_id):
        RUNNING_TASKS[chat_id] = False
        await event.edit("🛑 **ĐÃ ĐÌNH CHỈ TOÀN BỘ LUỒNG TẠI ĐÂY!**")
    else:
        await event.edit("⚠️ Không có tác vụ xả/treo nào đang chạy.")

# 10. QUÉT DỌN TIN NHẮN (.del & .xoahet)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}del(?:\s+(\d+))?"))
async def cmd_del(event):
    count = int(event.pattern_match.group(1) or 1)
    await event.delete()
    deleted = 0
    async for msg in client.iter_messages(event.chat_id, from_user="me", limit=count + 5):
        if deleted >= count:
            break
        try:
            await msg.delete()
            deleted += 1
            await asyncio.sleep(0.08)
        except Exception:
            pass

@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}(xoahet|purge)$"))
async def cmd_xoahet(event):
    reply = await event.get_reply_message()
    if not reply:
        return await event.edit("💡 Hãy **Reply** vào tin nhắn bắt đầu muốn xóa rồi gõ `.xoahet`")

    start_id = reply.id
    end_id = event.id
    chat_id = event.chat_id
    await event.delete()

    msg_ids = []
    async for msg in client.iter_messages(chat_id, min_id=start_id - 1, max_id=end_id):
        msg_ids.append(msg.id)

    if not msg_ids:
        return

    for i in range(0, len(msg_ids), 100):
        batch = msg_ids[i:i + 100]
        try:
            await client.delete_messages(chat_id, batch)
            await asyncio.sleep(0.15)
        except MessageDeleteForbiddenError:
            pass

# ==================== ENTRYPOINT ====================
async def main():
    await start_web_server()
    await client.start()
    print("[*] ANH KHOI PRO VIP USERBOT ĐÃ SẴN SÀNG CHIẾN ĐẤU!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
