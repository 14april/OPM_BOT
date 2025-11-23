import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
import asyncio
import config
import database
import localization

# Hàm kiểm tra Owner cứng
def is_owner_check(interaction: discord.Interaction) -> bool:
    return interaction.user.id == config.OWNER_ID

class AdminCommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- LỆNH 1: BUFF TIỀN ẢO TRONG DISCORD ---
    @app_commands.command(name="buff", description="[OWNER] Cộng Fund/Coupon cho thành viên Discord.")
    @app_commands.guilds(config.GUILD_ID)
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(is_owner_check)
    @app_commands.describe(target="Người nhận", currency="Loại tiền", amount="Số lượng")
    @app_commands.choices(currency=config.CURRENCY_CHOICES)
    async def buff(self, interaction: discord.Interaction, target: discord.Member, currency: app_commands.Choice[str], amount: int):
        await interaction.response.defer(ephemeral=True)
        
        data = await database.get_user_data(target.id)
        if not data: # Nếu user chưa có trong DB thì tạo mới
             data = {'discord_id': str(target.id)}
        
        key = currency.value # 'fund' hoặc 'coupon'
        data[key] = data.get(key, 0) + amount
        
        await database.save_user_data(target.id, data)
        
        emoji = config.ROLE_IDS['FUND_EMOJI'] if key == 'fund' else config.ROLE_IDS['COUPON_EMOJI']
        await interaction.followup.send(f"✅ Đã buff **+{amount:,}** {emoji} cho {target.mention}.", ephemeral=True)

    # --- LỆNH 2: CỘNG TIỀN CHO USER WEB ---
    @app_commands.command(name="web_add_fund", description="[OWNER] Nạp tiền thật cho user trên Website")
    @app_commands.guilds(config.GUILD_ID)
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(is_owner_check)
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
            await interaction.followup.send("❌ Lỗi hệ thống.")

    # --- LỆNH 3: MUA GÓI API ---
    @app_commands.command(name="agency_order", description="[OWNER] Đặt đơn hàng qua API")
    @app_commands.guilds(config.GUILD_ID)
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(is_owner_check)
    @app_commands.choices(deduct_mode=[
        app_commands.Choice(name="⛔ Không trừ tiền", value=0),
        app_commands.Choice(name="💸 Trừ tiền Web", value=1)
    ])
    async def agency_order(self, interaction: discord.Interaction, uid: str, sid: str, quantity: int, deduct_mode: int, web_username: str = None):
        await interaction.response.defer(ephemeral=True)
        price_per_pack = 14000
        total_cost = quantity * price_per_pack

        # Trừ tiền web
        if deduct_mode == 1:
            if not web_username: return await interaction.followup.send("❌ Vui lòng nhập web_username.")
            user = await database.get_web_user(web_username)
            if not user or user['balance'] < total_cost: return await interaction.followup.send("❌ User không tồn tại hoặc không đủ tiền.")
            await database.update_web_balance(web_username, -total_cost)
            await interaction.followup.send(f"💸 Đã trừ **{total_cost:,}** của **{web_username}**.")

        # Chạy API
        success_count = 0
        logs = []
        async with aiohttp.ClientSession() as session:
            for i in range(1, quantity + 1):
                payload = {'target_product_code': 'OPM_6', 'id': uid, 'server': sid}
                headers = {'Authorization': f'Bearer {config.API_KEY}', 'Signature': config.SECRET_KEY, 'Content-Type': 'application/json'}
                try:
                    async with session.post(config.API_URL_ORDER, json=payload, headers=headers) as resp:
                        res = json.loads(await resp.text())
                        status = res.get('data', {}).get('status')
                        if str(status) in ['1', 'Pending', 'Success', 'success']:
                            success_count += 1
                            logs.append(f"✅ Gói {i}: OK")
                            if i < quantity: await asyncio.sleep(15)
                        else:
                            logs.append(f"❌ Gói {i}: Lỗi ({res.get('message')})")
                except Exception as e:
                    logs.append(f"❌ Gói {i}: Lỗi kết nối")

        final_msg = f"📦 **Kết quả:** {success_count}/{quantity}\n" + "\n".join(logs)
        
        # Hoàn tiền nếu lỗi
        if deduct_mode == 1 and success_count < quantity:
            refund = (quantity - success_count) * price_per_pack
            await database.update_web_balance(web_username, refund)
            final_msg += f"\n⚠️ Đã hoàn **{refund:,}** cho gói lỗi."
            
        await interaction.followup.send(final_msg[:1900], ephemeral=True)

    @buff.error
    @web_add_fund.error
    @agency_order.error
    async def error_handler(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await interaction.response.send_message("⛔ Bạn không phải là Owner của Bot.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommandsCog(bot))
