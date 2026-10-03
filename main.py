import os
import sys
import re
import random
import asyncio
from aiohttp import web
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, MessageDeleteForbiddenError

# ==================== CẤU HÌNH HỆ THỐNG ====================
API_ID = int(os.environ.get("API_ID", 32906102))
API_HASH = os.environ.get("API_HASH", "9fc3add5b6bf34cc5335a85388f34a0f")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
PORT = int(os.environ.get("PORT", 8080))

PREFIX = "."  # Tiền tố lệnh (VD: .xaf, .delay, .ping, .xoahet)

# Cấu hình Firewall & Delay mặc định
SYSTEM_CONFIG = {
    "delay": 1.2,          # Delay an toàn mặc định (giây)
    "use_icons": True,     # Tự động gắn icon chọc tức
    "batch_rest": 15,      # Cứ sau 15 tin nhắn thì nghỉ giải nhiệt
    "rest_time": 8.0       # Thời gian giải nhiệt (giây)
}

# Quản lý tác vụ spam đang chạy theo Chat ID
RUNNING_SPAM = {}

# ==================== KHO ICON CHỌC TỨC CYBER / GOTHIC ====================
TOXIC_ICONS = [
    "亗", "𖤍", "🜲", "𒆜", "☬", "⚡",
    "𓆩✧𓆪", "𒀱", "𓊈☠︎𓊉", "☣", "𖤐", "⚜", "𖣘"
]

def wrap_toxic(text: str) -> str:
    """Gắn icon chọc tức ngẫu nhiên ở 2 đầu câu"""
    if not SYSTEM_CONFIG["use_icons"]:
        return text
    i1 = random.choice(TOXIC_ICONS)
    i2 = random.choice(TOXIC_ICONS)
    return f"{i1} {text} {i2}"

def parse_and_sort_file(content: str) -> list:
    """
    Phân tích file:
    - Nhận biết số thứ tự đầu dòng (1., 2), 3-, 4: ...)
    - Sắp xếp chuẩn từ 1 đến hết
    - Tự động cắt bỏ số thứ tự, chỉ giữ lại nội dung
    """
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    parsed = []

    for idx, line in enumerate(lines):
        # Regex bắt: số ở đầu + dấu ngăn cách (., ), -, :, khoảng trắng) + nội dung
        match = re.match(r"^(\d+)[\.\)\:\-\s]+(.*)$", line)
        if match:
            order_num = int(match.group(1))
            clean_text = match.group(2).strip()
            # Nếu nội dung sau số bị rỗng thì giữ nguyên dòng
            clean_text = clean_text if clean_text else line
            parsed.append((order_num, clean_text))
        else:
            # Dòng không có số thứ tự: gán vị trí mặc định theo thứ tự tự nhiên
            parsed.append((idx + 100000, line))

    # Sắp xếp theo số thứ tự tăng dần
    parsed.sort(key=lambda x: x[0])
    return [item[1] for item in parsed]

# ==================== WEB SERVER CHO RENDER LIVE 24/7 ====================
async def handle_health(request):
    return web.Response(
        text="ANH KHOI USERBOT CORE V12\nSTATUS: ONLINE 24/7 ON RENDER\nFIREWALL: ACTIVE",
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
    print(f"[*] Máy chủ Render đã mở Port {PORT}")

# ==================== KHỞI TẠO TELETHON CLIENT ====================
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== CÁC LỆNH USERBOT CHÍNH ====================

# 1. KIỂM TRA BOT
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}ping$"))
async def cmd_ping(event):
    await event.edit(f"⚡ **ANH KHÔI USERBOT ĐANG ONLINE!**\n🛡️ **Firewall Delay:** `{SYSTEM_CONFIG['delay']}s` | **Icons:** `{'BẬT' if SYSTEM_CONFIG['use_icons'] else 'TẮT'}`")

# 2. XEM BẢNG LỆNH
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}(help|lenh)$"))
async def cmd_help(event):
    text = (
        "👑 **BẢNG ĐIỀU KHIỂN USERBOT CAO CẤP - PHẠM ANH KHÔI**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "**📁 QUẢN LÝ FILE:**\n"
        f"• `{PREFIX}dsfile` : Xem danh sách file trên server\n"
        f"• `{PREFIX}themfile <tên> <nội dung>` : Tạo hoặc ghi đè file\n"
        f"• `{PREFIX}xemfile <tên>` : Đọc nội dung file\n"
        f"• `{PREFIX}xoafile <tên>` : Xóa file khỏi server\n\n"
        "**⚡ HỎA LỰC TỰ ĐỘNG THEO FILE:**\n"
        f"• `{PREFIX}xaf <tên_file>` : Tự đọc & xả đòn theo thứ tự dòng\n"
        f"• `{PREFIX}dung` : Dừng ngay lập tức chiến dịch đang xả\n\n"
        "**🛡️ FIREWALL & CHỐNG BAN:**\n"
        f"• `{PREFIX}delay <giây>` : Cài đặt giây delay an toàn (VD: `{PREFIX}delay 1.5`)\n"
        f"• `{PREFIX}icon` : Bật/Tắt gắn icon chọc tức hai đầu chữ\n\n"
        "**🧹 THANH TRỪNG TIN NHẮN:**\n"
        f"• `{PREFIX}del [số]` : Xóa tin nhắn của chính mình\n"
        f"• `{PREFIX}xoahet` (reply tin) : Xóa sạch toàn bộ tin nhắn từ tin đó"
    )
    await event.edit(text)

# 3. QUẢN LÝ FILE
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}dsfile$"))
async def cmd_dsfile(event):
    files = [f for f in os.listdir(".") if os.path.isfile(f)]
    if not files:
        return await event.edit("📁 Server chưa có file nào.")
    ds = "\n".join([f"• `{f}` ({os.path.getsize(f)} bytes)" for f in files[:35]])
    await event.edit(f"📁 **DANH SÁCH FILE HIỆN CÓ:**\n{ds}")

@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}themfile\s+(\S+)(?:\s+([\s\S]+))?"))
async def cmd_themfile(event):
    filename = event.pattern_match.group(1)
    content = event.pattern_match.group(2) or ""

    if filename in ["main.py", "requirements.txt"]:
        return await event.edit(f"⚠️ Không thể can thiệp file hệ thống: `{filename}`")

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        lines_count = len(content.splitlines())
        await event.edit(f"✅ Đã lưu file `{filename}` thành công ({lines_count} dòng, {len(content)} ký tự)!")
    except Exception as e:
        await event.edit(f"❌ Lỗi ghi file: `{e}`")

@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}xemfile\s+(\S+)"))
async def cmd_xemfile(event):
    filename = event.pattern_match.group(1)
    if not os.path.exists(filename):
        return await event.edit(f"❌ Không tìm thấy file `{filename}`!")
    try:
        with open(filename, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read(3500)
        await event.edit(f"📄 **NỘI DUNG `{filename}`:**\n```\n{data}\n```")
    except Exception as e:
        await event.edit(f"❌ Lỗi: `{e}`")

@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}xoafile\s+(\S+)"))
async def cmd_xoafile(event):
    filename = event.pattern_match.group(1)
    if filename in ["main.py", "requirements.txt"]:
        return await event.edit(f"⚠️ Không thể xóa file gốc `{filename}`")
    if not os.path.exists(filename):
        return await event.edit(f"❌ File `{filename}` không tồn tại.")
    try:
        os.remove(filename)
        await event.edit(f"🗑️ Đã xóa file `{filename}` khỏi server!")
    except Exception as e:
        await event.edit(f"❌ Lỗi: `{e}`")

# 4. THIẾT LẬP DELAY & TƯỜNG LỬA CHỐNG BAN
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}delay\s*(\S+)?"))
async def cmd_setdelay(event):
    val_str = event.pattern_match.group(1)
    if not val_str:
        return await event.edit(f"⏱️ Delay hiện tại: `{SYSTEM_CONFIG['delay']}s/tin`\nĐổi tốc độ: `{PREFIX}delay 1.5`")
    try:
        val = float(val_str)
        if val < 0.2:
            return await event.edit("⚠️ **Cảnh báo Firewall:** Không được set dưới `0.2s` để tránh bị Telegram quét ban số!")
        SYSTEM_CONFIG["delay"] = val
        await event.edit(f"🛡️ **Đã thiết lập Delay an toàn:** `{val}s/tin`")
    except:
        await event.edit("❌ Số giây không hợp lệ!")

@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}icon$"))
async def cmd_toggle_icon(event):
    SYSTEM_CONFIG["use_icons"] = not SYSTEM_CONFIG["use_icons"]
    st = "BẬT 🔥" if SYSTEM_CONFIG["use_icons"] else "TẮT ⚪"
    await event.edit(f"𖤍 **Chế độ gắn Icon chọc tức:** {st}")

# 5. TỰ ĐỘNG NHẮN THEO FILE (CẮT SỐ THỨ TỰ, GẮN ICON, CHỐNG FLOOD)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}xaf\s+(\S+)"))
async def cmd_xaf(event):
    filename = event.pattern_match.group(1)
    chat_id = event.chat_id

    if not os.path.exists(filename):
        return await event.edit(f"❌ Không tìm thấy file `{filename}`! Dùng `{PREFIX}dsfile` để kiểm tra.")

    try:
        with open(filename, "r", encoding="utf-8", errors="ignore") as f:
            raw_content = f.read()
    except Exception as e:
        return await event.edit(f"❌ Không thể đọc file: `{e}`")

    # Xử lý lọc bỏ số thứ tự & sắp xếp
    clean_lines = parse_and_sort_file(raw_content)
    if not clean_lines:
        return await event.edit(f"⚠️ File `{filename}` rỗng hoặc không có dòng hợp lệ!")

    # Xóa tin nhắn lệnh để bắt đầu
    await event.delete()
    RUNNING_SPAM[chat_id] = True

    count = 0
    total = len(clean_lines)

    for line in clean_lines:
        if not RUNNING_SPAM.get(chat_id):
            break

        # Gắn icon chọc tức vào nội dung
        final_text = wrap_toxic(line)

        # Gửi tin nhắn có kèm bắt lỗi FloodWait bảo vệ acc
        sent = False
        while not sent and RUNNING_SPAM.get(chat_id):
            try:
                await client.send_message(chat_id, final_text)
                sent = True
                count += 1
            except FloodWaitError as e:
                # Firewall tự động kích hoạt ngủ đúng số giây yêu cầu + 2s
                print(f"[FIREWALL] Bị giới hạn FloodWait! Tự động chờ {e.seconds}s...")
                await asyncio.sleep(e.seconds + 2)
            except Exception as e:
                print(f"[ERROR] Gửi tin thất bại: {e}")
                await asyncio.sleep(1)
                break

        # Cơ chế giải nhiệt định kỳ (Anti-Overheat)
        if count % SYSTEM_CONFIG["batch_rest"] == 0 and RUNNING_SPAM.get(chat_id):
            await asyncio.sleep(SYSTEM_CONFIG["rest_time"])

        # Delay an toàn + Micro-Jitter (chống bot pattern)
        jitter = random.uniform(0.1, 0.35)
        await asyncio.sleep(SYSTEM_CONFIG["delay"] + jitter)

    RUNNING_SPAM[chat_id] = False

# 6. DỪNG TỰ ĐỘNG GỬI
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}(dung|stop)$"))
async def cmd_dung(event):
    chat_id = event.chat_id
    if RUNNING_SPAM.get(chat_id):
        RUNNING_SPAM[chat_id] = False
        await event.edit("🛑 **ĐÃ ĐÌNH CHỈ CHIẾN DỊCH TỰ ĐỘNG GỬI!**")
    else:
        await event.edit("⚠️ Không có chiến dịch nào đang chạy tại đoạn chat này.")

# 7. XÓA TIN NHẮN CHÍNH MÌNH (.del <số>)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}del(?:\s+(\d+))?"))
async def cmd_del_me(event):
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
        except:
            pass

# 8. THANH TRỪNG TOÀN BỘ TIN NHẮN TRONG CHAT (.xoahet HOẶC .purge)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}(xoahet|purge)$"))
async def cmd_purge_all(event):
    reply_msg = await event.get_reply_message()
    chat_id = event.chat_id

    if not reply_msg:
        return await event.edit("💡 **Cách dùng:** Hãy **Reply** vào tin nhắn bạn muốn bắt đầu xóa rồi gõ `.xoahet`")

    start_id = reply_msg.id
    end_id = event.id
    await event.delete()

    msg_ids = []
    # Thu thập tất cả id tin nhắn nằm giữa
    async for msg in client.iter_messages(chat_id, min_id=start_id - 1, max_id=end_id):
        msg_ids.append(msg.id)

    if not msg_ids:
        return

    # Xóa theo batch (mỗi lần 100 tin nhắn)
    total_del = 0
    for i in range(0, len(msg_ids), 100):
        batch = msg_ids[i:i + 100]
        try:
            await client.delete_messages(chat_id, batch)
            total_del += len(batch)
            await asyncio.sleep(0.15)
        except MessageDeleteForbiddenError:
            # Nếu không có quyền xóa tin của người khác trong group, chỉ lọc xóa tin của mình
            pass

# ==================== ENTRYPOINT ====================
async def main():
    if not SESSION_STRING:
        print("[!] LỖI: Chưa cấu hình SESSION_STRING trên Render!")
        sys.exit(1)

    await start_web_server()
    await client.start()
    print("[*] ANH KHOI USERBOT ĐÃ SẴN SÀNG CHIẾN ĐẤU!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
