import os
import sys
import asyncio
from aiohttp import web
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ==================== CẤU HÌNH HỆ THỐNG ====================
API_ID = int(os.environ.get("API_ID", 32906102))
API_HASH = os.environ.get("API_HASH", "9fc3add5b6bf34cc5335a85388f34a0f")
# Chuỗi Session lấy từ script đăng nhập (xem hướng dẫn bên dưới)
SESSION_STRING = os.environ.get("SESSION_STRING", "1BVtsOIIBuxPBTJcjHmwH5MpU1DO068XwGFkdO2mxIdbqKtMt_-u3_jQkzaUUDCLtD_-HOZ2NTkXI0cDQistaYUm13b3uR-K_vRgXK168mNbiYd7selpS9nUa4NGQSfZSVu_LuhFmYmJK1kmcXJUD41QdOjuV4Otw-_-CZNk_hL-WiDIe4kX4_7hPdPuis1gm4ysRUsVokf0lBwlhXIwVEggOUTcQ8WAFzzQhDZFxZ6Xqqc74837vt05JS9PnLIRDG-dliqgNC4JRXioFTap8rczjaMYTKmcIk47Rb9M59vzjTCc1CwwqhE5tix0HbBElSdY_R7OFC2jMbCwykCnI__U7OsmUhNs=")
PORT = int(os.environ.get("PORT", 8080))

PREFIX = "."  # Tiền tố lệnh, ví dụ: .ping, .themfile

# ==================== WEB SERVER CHO RENDER ====================
async def handle_health(request):
    return web.Response(
        text="USERBOT RUNNING 24/7 ON RENDER\nAUTHOR: PHAM ANH KHOI",
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
    print(f"[*] Web Server đã mở tại cổng {PORT}")

# ==================== KHỞI TẠO TELETHON CLIENT ====================
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== XỬ LÝ LỆNH USERBOT ====================

# 1. Lệnh kiểm tra hoạt động (.ping)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{PREFIX}ping$"))
async def cmd_ping(event):
    await event.edit("⚡ **Userbot đang hoạt động trực tuyến 24/7!**")

# 2. Xem danh sách lệnh (.help hoặc .lenh)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{PREFIX}(help|lenh)$"))
async def cmd_help(event):
    text = (
        "👑 **BẢNG ĐIỀU KHIỂN USERBOT - PHẠM ANH KHÔI**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "• `.ping` : Kiểm tra trạng thái Userbot\n"
        "• `.dsfile` : Liệt kê tất cả file trên thư mục máy chủ\n"
        "• `.themfile <tên_file> <nội dung>` : Tạo hoặc ghi đè file\n"
        "• `.xemfile <tên_file>` : Đọc nội dung file trực tiếp\n"
        "• `.xoafile <tên_file>` : Xóa file khỏi máy chủ\n"
        "• `.del [số lượng]` : Xóa nhanh tin nhắn vừa gửi"
    )
    await event.edit(text)

# 3. Liệt kê danh sách file (.dsfile)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{PREFIX}dsfile$"))
async def cmd_list_files(event):
    files = [f for f in os.listdir(".") if os.path.isfile(f)]
    if not files:
        await event.edit("📁 Thư mục hiện tại chưa có file nào.")
        return
    
    file_list = "\n".join([f"• `{f}` ({os.path.getsize(f)} bytes)" for f in files[:30]])
    await event.edit(f"📁 **DANH SÁCH FILE TRÊN SERVER:**\n{file_list}")

# 4. Thêm / Ghi nội dung vào file (.themfile <tên> <nội dung>)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{PREFIX}themfile\s+(\S+)(?:\s+([\s\S]+))?"))
async def cmd_add_file(event):
    filename = event.pattern_match.group(1)
    content = event.pattern_match.group(2) or ""

    # Ngăn chặn ghi đè vào file hệ thống cốt lõi
    if filename in ["main.py", "requirements.txt", "generate_session.py"]:
        await event.edit(f"⚠️ Không được phép ghi đè file hệ thống: `{filename}`")
        return

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        await event.edit(f"✅ Đã tạo/lưu file `{filename}` thành công ({len(content)} ký tự)!")
    except Exception as e:
        await event.edit(f"❌ Lỗi khi tạo file: `{e}`")

# 5. Xem nội dung file (.xemfile <tên>)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{PREFIX}xemfile\s+(\S+)"))
async def cmd_view_file(event):
    filename = event.pattern_match.group(1)
    if not os.path.exists(filename):
        await event.edit(f"❌ Không tìm thấy file `{filename}`!")
        return

    try:
        with open(filename, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read(3000)  # Đọc tối đa 3000 ký tự tránh tràn giới hạn tin nhắn
        await event.edit(f"📄 **NỘI DUNG FILE `{filename}`:**\n```\n{data}\n```")
    except Exception as e:
        await event.edit(f"❌ Lỗi khi đọc file: `{e}`")

# 6. Xóa file (.xoafile <tên>)
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{PREFIX}xoafile\s+(\S+)"))
async def cmd_delete_file(event):
    filename = event.pattern_match.group(1)

    if filename in ["main.py", "requirements.txt"]:
        await event.edit(f"⚠️ Không thể xóa file vận hành chính: `{filename}`")
        return

    if not os.path.exists(filename):
        await event.edit(f"❌ File `{filename}` không tồn tại.")
        return

    try:
        os.remove(filename)
        await event.edit(f"🗑️ Đã xóa file `{filename}` thành công khỏi máy chủ!")
    except Exception as e:
        await event.edit(f"❌ Lỗi khi xóa file: `{e}`")

# 7. Xóa tin nhắn tự động (.del [số])
@client.on(events.NewMessage(outgoing=True, pattern=rf"^{PREFIX}del(?:\s+(\d+))?"))
async def cmd_purge_self(event):
    count = int(event.pattern_match.group(1) or 1)
    chat = await event.get_input_chat()
    deleted = 0
    async for msg in client.iter_messages(chat, from_user="me", limit=count + 1):
        await msg.delete()
        deleted += 1
        await asyncio.sleep(0.1)

# ==================== ENTRYPOINT ====================
async def main():
    if not SESSION_STRING:
        print("[!] LỖI: Chưa cấu hình SESSION_STRING trong biến môi trường!")
        sys.exit(1)

    await start_web_server()
    await client.start()
    print("[*] Userbot đã kết nối và bắt đầu lắng nghe lệnh outgoing!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
