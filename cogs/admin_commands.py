import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
import asyncio
import config
import database
import localization

# Hàm kiểm tra: Chỉ cho phép ID của bạn sử dụng
def is_owner_check(interaction: discord.Interaction) -> bool:
    return interaction.user.id == config.OWNER_ID

class AdminCommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- LỆNH 1: CỘNG TIỀN CHO USER WEB ---
    @app_commands.command(name="web_add_fund", description="[ADMIN] Nạp tiền cho user trên Website")
    @app_commands.guilds(config.GUILD_ID)                  # Chỉ hiện trong server của bạn
    @app_commands.default_permissions(administrator=True)  # Ẩn với member thường
    @app_commands.check(is_owner_check)                    # Chỉ ID của bạn mới dùng được
    @app_commands.describe(username="Username tài khoản Web", amount="Số tiền muốn cộng (VNĐ)")
    async def web_add_fund(self, interaction: discord.Interaction, username: str, amount: int):
        await interaction.response.defer(ephemeral=True)
        
        user = await database.get_web_user(username)
        if not user:
            return await interaction.followup.send(f"❌ Không tìm thấy tài khoản web: **{username}**")

        success = await database.update_web_balance(username, amount)
        if success:
            new_bal = user['balance'] + amount
            await interaction.followup.send(f"✅ Đã cộng **{amount:,}** vào user **{username}**.\n💰 Số dư mới: **{new_bal:,} VNĐ**")
        else:
            await interaction.followup.send("❌ Lỗi hệ thống khi cập nhật số dư.")

    # --- LỆNH 2: MUA GÓI API (KHÔNG CẦN LOGIN WEB) ---
    @app_commands.command(name="agency_order", description="[ADMIN] Đặt đơn hàng qua API Tokowendigg")
    @app_commands.guilds(config.GUILD_ID)                  # Chỉ hiện trong server của bạn
    @app_commands.default_permissions(administrator=True)  # Ẩn với member thường
    @app_commands.check(is_owner_check)                    # Chỉ ID của bạn mới dùng được
    @app_commands.describe(
        uid="UID Game", sid="Server ID", quantity="Số lượng gói",
        deduct_mode="Chế độ trừ tiền", web_username="Username Web (nếu chọn trừ tiền)"
    )
    @app_commands.choices(deduct_mode=[
        app_commands.Choice(name="⛔ Không trừ tiền (Khách ck ngoài/Admin tặng)", value=0),
        app_commands.Choice(name="💸 Trừ tiền tài khoản Web", value=1)
    ])
    async def agency_order(self, interaction: discord.Interaction, uid: str, sid: str, quantity: int, deduct_mode: int, web_username: str = None):
        await interaction.response.defer(ephemeral=True)

        price_per_pack = 14000
        total_cost = quantity * price_per_pack

        # Bước 1: Xử lý trừ tiền (Nếu chọn)
        if deduct_mode == 1:
            if not web_username:
                return await interaction.followup.send("❌ Bạn chọn 'Trừ tiền Web' thì phải nhập `web_username`.")
            
            user = await database.get_web_user(web_username)
            if not user:
                return await interaction.followup.send(f"❌ User **{web_username}** không tồn tại.")
            
            if user['balance'] < total_cost:
                return await interaction.followup.send(f"❌ User không đủ tiền.\nCần: **{total_cost:,}**\nCó: **{user['balance']:,}**")
            
            # Trừ tiền trước
            await database.update_web_balance(web_username, -total_cost)
            await interaction.followup.send(f"💸 Đã trừ **{total_cost:,} VNĐ** của **{web_username}**. Bắt đầu chạy đơn...")

        # Bước 2: Gọi API Mua hàng
        success_count = 0
        logs = []
        
        async with aiohttp.ClientSession() as session:
            for i in range(1, quantity + 1):
                payload = {'target_product_code': 'OPM_6', 'id': uid, 'server': sid}
                headers = {
                    'Authorization': f'Bearer {config.API_KEY}',
                    'Signature': config.SECRET_KEY,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                }

                try:
                    async with session.post(config.API_URL_ORDER, json=payload, headers=headers) as resp:
                        resp_text = await resp.text()
                        result = json.loads(resp_text)
                        
                        is_ok = False
                        if result and 'data' in result:
                            status = result['data'].get('status')
                            if str(status) in ['1', 'Pending', 'Success', 'success']:
                                is_ok = True

                        if is_ok:
                            success_count += 1
                            ref = result['data'].get('reference', 'NoRef')
                            logs.append(f"✅ Gói {i}: OK ({ref})")
                            
                            if i < quantity:
                                await interaction.followup.send(f"⏳ Xong gói {i}. Đợi 15s...", ephemeral=True)
                                await asyncio.sleep(15)
                        else:
                            msg = result.get('message', 'Unknown')
                            logs.append(f"❌ Gói {i}: Lỗi ({msg})")
                            
                except Exception as e:
                     logs.append(f"❌ Gói {i}: Lỗi kết nối ({e})")

        # Bước 3: Tổng kết & Hoàn tiền nếu lỗi
        summary = "\n".join(logs)
        if len(summary) > 1500: summary = summary[:1500] + "\n...(Log quá dài)..."
        
        final_msg = f"📦 **KẾT QUẢ ORDER ({uid} | {sid})**\nThành công: **{success_count}/{quantity}**\n\n{summary}"
        
        if deduct_mode == 1 and success_count < quantity:
            fail_count = quantity - success_count
            refund_amount = fail_count * price_per_pack
            await database.update_web_balance(web_username, refund_amount)
            final_msg += f"\n\n⚠️ **Đã hoàn lại {refund_amount:,} VNĐ** vào web cho {fail_count} gói lỗi."

        await interaction.followup.send(final_msg, ephemeral=True)

    # Xử lý lỗi khi người khác cố tình dùng lệnh
    @web_add_fund.error
    @agency_order.error
    async def admin_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("⛔ Lệnh này chỉ dành riêng cho Owner Bot.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Lỗi: {error}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommandsCog(bot))
