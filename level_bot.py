import os
import asyncio
import discord
from discord.ext import commands
import database
import config

# Token lấy trực tiếp từ biến môi trường hoặc điền thẳng vào đây nếu test local
TOKEN = "TOKEN_DISCORD_CUA_BAN" # <--- Nhớ điền Token nếu chạy trên máy tính

intents = discord.Intents.default()
intents.members = True 
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Danh sách Cogs
INITIAL_EXTENSIONS = [
    'cogs.level_system',
    'cogs.user_commands',
    'cogs.leaderboard',
    'cogs.reaction_roles',
    'cogs.admin_commands',
    'cogs.language_command',
    'cogs.voucher_calc',
]

@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {bot.user}")
    
    # Kiểm tra kết nối DB
    conn = database.get_connection()
    if conn:
        print("✅ Kết nối MySQL: OK")
        conn.close()
    else:
        print("❌ Kết nối MySQL: THẤT BẠI (Kiểm tra config.py)")

    # Sync lệnh Slash
    if config.GUILD_ID:
        guild = discord.Object(id=config.GUILD_ID)
        try:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            print(f"🔁 Đã đồng bộ lệnh cho Server ID: {config.GUILD_ID}")
        except Exception as e:
            print(f"❌ Lỗi sync command: {e}")

async def main():
    for extension in INITIAL_EXTENSIONS:
        try:
            await bot.load_extension(extension)
        except Exception as e:
            print(f"❌ Lỗi tải Cog {extension}: {e}")

    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
