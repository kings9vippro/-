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

# Đã gán sẵn chuỗi Session của bạn để chống lỗi thiếu biến môi trường
DEFAULT_SESSION = "1BVtsOIIBuxPBTJcjHmwH5MpU1DO068XwGFkdO2mxIdbqKtMt_-u3_jQkzaUUDCLtD_-HOZ2NTkXI0cDQistaYUm13b3uR-K_vRgXK168mNbiYd7selpS9nUa4NGQSfZSVu_LuhFmYmJK1kmcXJUD41QdOjuV4Otw-_-CZNk_hL-WiDIe4kX4_7hPdPuis1gm4ysRUsVokf0lBwlhXIwVEggOUTcQ8WAFzzQhDZFxZ6Xqqc74837vt05JS9PnLIRDG-dliqgNC4JRXioFTap8rczjaMYTKmcIk47Rb9M59vzjTCc1CwwqhE5tix0HbBElSdY_R7OFC2jMbCwykCnI__U7OsmUhNs="
SESSION_STRING = os.environ.get("SESSION_STRING", "").strip() or DEFAULT_SESSION

PORT = int(os.environ.get("PORT", 8080))
PREFIX = "."  # Tiền tố lệnh (VD: .xaf, .luufile, .dung)

# Cấu hình Firewall & Anti-Ban
SYSTEM_CONFIG = {
    "delay": 1.2,          # Delay an toàn giữa các tin (giây)
    "use_icons": True,     # Bật icon chọc tức
    "batch_rest": 12,      # Cứ sau 12 tin sẽ nghỉ giải nhiệt
    "rest_time": 7.0       # Thời gian giải nhiệt (giây)
}

RUNNING_SPAM = {}

# ==================== DÀN ICON CHỌC TỨC & KÝ TỰ VÔ HÌNH ====================
TOXIC_ICONS = ["🤪", "👌", "👻", "😹", "🤡", "💀", "🫵", "🔥", "😈", "🐸", "🤫", "亗", "𖤍"]
INVISIBLE_CHARS = ["\u200b", "\u200c", "\u200d", "\ufeff"]

def anti_ban_payload(text: str) -> str:
    """Bơm icon chọc tức + ký tự tàng hình phá vỡ thuật toán quét Spam của Telegram"""
    # 1. Chèn ký tự tàng hình ngẫu nhiên vào giữa câu để tạo mã hash tin nhắn duy nhất
    salt = "".join(random.choices(INVISIBLE_CHARS, k=random.randint(2, 5)))
    body = f"{salt}{text}{salt}"

    # 2. Gắn icon chọc tức vào 2 đầu
    if SYSTEM_CONFIG["use_icons"]:
        ic1 = random.choice(TOXIC_ICONS)
        ic2 = random.choice(TOXIC_ICONS)
        return f"{ic1} {body} {ic2}"
    return body

def parse_and_sort_file(content: str) -> list:
    """Tự nhận số thứ tự đầu dòng, sắp xếp từ nhỏ đến lớn, tự cắt bỏ số"""
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

# ==================== WEB SERVER GIỮ RENDER 24/7 ====================
async def handle_health(request):
    return web.Response(
        text="ANH KHOI PRO USERBOT\nSTATUS: ONLINE 24/7\nFIREWALL: ULTRA ACTIVE",
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
    print(f"[*] Web Server đã kích hoạt trên cổng {PORT}")

# ==================== KHỞI TẠO CLIENT ====================
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== BỘ TỰ ĐỘNG BẮT FILE & LỆNH ====================

# 1. TỰ ĐỘNG BẮT FILE KHI BẠN GỬI TẬP TIN .TXT
@client.on(events.NewMessage(outgoing=True))
async def auto_catch_file(event):
    if event.message.file and event.message.file.name:
        fname = event.message.file.name
        # Tự động lưu nếu gửi file .txt
        if fname.lower().endswith(".txt"):
            save_path = await event.message.download_media(file=fname)
            print(f"[*] Đã tự động nhận và lưu file: {save_path}")

# 2. LỆNH LƯU FILE BẰNG TAY HOẶC REPLY (.luufile [tên])
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
        await event.edit(f"✅ **ĐÃ LƯU FILE THÀNH CÔNG!**\n📁 Tên file: `{fname}`\n📦 Dung lượng: `{sz} bytes`\n👉 Sẵn sàng xả đòn: `{PREFIX}xaf {fname}`")
    else:
        await event.edit("❌ Tải file thất bại!")

# 3. KIỂM TRA TRẠNG THÁI (.ping)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}ping$"))
async def cmd_ping(event):
    await event.edit(
        f"⚡ **USERBOT ANH KHÔI ĐANG ONLINE!** 🤪👌\n"
        f"🛡️ **Firewall Anti-Ban:** `BẬT CỰC HẠN`\n"
        f"⏱️ **Độ trễ:** `{SYSTEM_CONFIG['delay']}s` | **Icons:** `{'BẬT 👻' if SYSTEM_CONFIG['use_icons'] else 'TẮT'}`"
    )

# 4. DANH SÁCH LỆNH (.help / .lenh)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}(help|lenh)$"))
async def cmd_help(event):
    text = (
        "👑 **BẢNG ĐIỀU KHIỂN USERBOT VIP - PHẠM ANH KHÔI** 🤪👌\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "**📁 QUẢN LÝ FILE (KHÔNG LO LAG MÁY):**\n"
        f"• Gửi thẳng file `.txt` vào chat -> Bot tự tải về lưu luôn!\n"
        f"• `{PREFIX}luufile [tên]` (Reply file) : Tải file về server\n"
        f"• `{PREFIX}dsfile` : Xem toàn bộ file hiện có\n"
        f"• `{PREFIX}xemfile <tên>` : Đọc trước nội dung file\n"
        f"• `{PREFIX}xoafile <tên>` : Xóa file khỏi máy chủ\n\n"
        "**🔥 XẢ HỎA LỰC THEO FILE:**\n"
        f"• `{PREFIX}xaf <tên_file>` : Tự lọc thứ tự & xả đòn\n"
        f"• `{PREFIX}dung` : Dừng ngay lập tức chiến dịch\n\n"
        "**🛡️ FIREWALL & TÙY CHỈNH:**\n"
        f"• `{PREFIX}delay <giây>` : Chỉnh giây an toàn (VD: `{PREFIX}delay 1.0`)\n"
        f"• `{PREFIX}icon` : Bật/Tắt dàn icon 🤪👌👻😹\n\n"
        "**🧹 QUÉT SẠCH TIN NHẮN:**\n"
        f"• `{PREFIX}del [số]` : Xóa tin nhắn của mình\n"
        f"• `{PREFIX}xoahet` (Reply tin) : Quét sạch từ tin đó trở đi"
    )
    await event.edit(text)

# 5. XEM & XÓA FILE
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

# 6. THIẾT LẬP DELAY & ICON
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}delay\s*(\S+)?"))
async def cmd_delay(event):
    v = event.pattern_match.group(1)
    if not v:
        return await event.edit(f"⏱️ Delay hiện tại: `{SYSTEM_CONFIG['delay']}s/tin`")
    try:
        val = float(v)
        if val < 0.2:
            return await event.edit("⚠️ Firewall chặn: Không thể đặt dưới `0.2s` để tránh ban số!")
        SYSTEM_CONFIG["delay"] = val
        await event.edit(f"🛡️ Đã cài Delay: `{val}s/tin`")
    except:
        await event.edit("❌ Giá trị không hợp lệ!")

@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}icon$"))
async def cmd_icon(event):
    SYSTEM_CONFIG["use_icons"] = not SYSTEM_CONFIG["use_icons"]
    st = "BẬT 🤪👌👻😹" if SYSTEM_CONFIG["use_icons"] else "TẮT ⚪"
    await event.edit(f"𖤍 Chế độ gắn Icon chọc tức: **{st}**")

# 7. ENGINE XẢ FILE ANTI-BAN SIÊU CẤP (.xaf)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}xaf\s+(\S+)"))
async def cmd_xaf(event):
    fname = event.pattern_match.group(1)
    chat_id = event.chat_id

    if not os.path.exists(fname):
        return await event.edit(f"❌ Không tìm thấy file `{fname}`! Hãy gửi file vào chat để bot tự lưu.")

    try:
        with open(fname, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
    except Exception as e:
        return await event.edit(f"❌ Lỗi đọc file: {e}")

    lines = parse_and_sort_file(raw)
    if not lines:
        return await event.edit("⚠️ File không có dòng nội dung nào!")

    await event.delete()
    RUNNING_SPAM[chat_id] = True
    count = 0

    for line in lines:
        if not RUNNING_SPAM.get(chat_id):
            break

        # Bơm payload chống quét mã + icon chọc tức
        final_msg = anti_ban_payload(line)

        sent = False
        while not sent and RUNNING_SPAM.get(chat_id):
            try:
                # Mô phỏng trạng thái typing như người thật
                async with client.action(chat_id, "typing"):
                    await asyncio.sleep(0.15)

                await client.send_message(chat_id, final_msg)
                sent = True
                count += 1
            except FloodWaitError as e:
                # Gặp giới hạn tần suất -> tự động ngủ đúng số giây yêu cầu
                print(f"[FIREWALL] Kích hoạt chế độ ngủ chống ban trong {e.seconds}s...")
                await asyncio.sleep(e.seconds + 2)
            except Exception as e:
                print(f"[LỖI] {e}")
                await asyncio.sleep(1)
                break

        # Hồi mana định kỳ (cứ 12 tin thì nghỉ 7s)
        if count % SYSTEM_CONFIG["batch_rest"] == 0 and RUNNING_SPAM.get(chat_id):
            await asyncio.sleep(SYSTEM_CONFIG["rest_time"])

        # Delay an toàn kết hợp dao động ngẫu nhiên (Jitter)
        jitter = random.uniform(0.1, 0.4)
        await asyncio.sleep(SYSTEM_CONFIG["delay"] + jitter)

    RUNNING_SPAM[chat_id] = False

# 8. DỪNG XẢ
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{re.escape(PREFIX)}(dung|stop)$"))
async def cmd_dung(event):
    chat_id = event.chat_id
    if RUNNING_SPAM.get(chat_id):
        RUNNING_SPAM[chat_id] = False
        await event.edit("🛑 **ĐÃ DỪNG TẤT CẢ CHIẾN DỊCH TẠI ĐÂY!**")
    else:
        await event.edit("⚠️ Không có chiến dịch nào đang chạy.")

# 9. THANH TRỪNG TIN NHẮN (.del & .xoahet)
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
        except:
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

# ==================== KHỞI CHẠY ====================
async def main():
    await start_web_server()
    await client.start()
    print("[*] USERBOT ANH KHÔI ĐÃ SẴN SÀNG HOẠT ĐỘNG TRỰC TUYẾN!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
