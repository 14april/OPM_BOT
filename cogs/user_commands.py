import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import random
import asyncio
import config
import database
import localization

class UserCommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_lang(self, interaction):
        data = await database.get_user_data(interaction.user.id)
        return data.get('language', 'vi') if data else 'vi'

    @app_commands.command(name="daily", description="Điểm danh nhận quà hàng ngày")
    async def daily(self, interaction: discord.Interaction):
        data = await database.get_user_data(interaction.user.id)
        if not data: data = {'discord_id': str(interaction.user.id)} # Fix lỗi nếu chưa có data
        
        user_lang = data.get('language', 'vi')
        last_daily = data.get('last_daily')
        
        if last_daily and last_daily.date() == datetime.now().date():
            return await interaction.response.send_message(localization.get_string(user_lang, 'daily_already'), ephemeral=True)

        # --- CHỈNH SỬA LẠM PHÁT Ở ĐÂY ---
        fund_reward = random.randint(5000, 10000)     # Trước đây là 10 tỷ
        coupon_reward = random.randint(5000, 10000)   # Trước đây là 10 tỷ
        # --------------------------------

        data['fund'] = data.get('fund', 0) + fund_reward
        data['coupon'] = data.get('coupon', 0) + coupon_reward
        data['last_daily'] = datetime.now()
        
        await database.save_user_data(interaction.user.id, data)
        
        await interaction.response.send_message(
            localization.get_string(user_lang, 'daily_success', 
                fund_reward=fund_reward, fund_emoji=config.ROLE_IDS['FUND_EMOJI'], 
                coupon_reward=coupon_reward, coupon_emoji=config.ROLE_IDS['COUPON_EMOJI']),
            ephemeral=True
        )

    # ... (Các lệnh profile, exchange, all_in, transfer giữ nguyên như cũ) ...
    # Bạn chỉ cần copy phần daily ở trên đè vào file cũ là được.

    # (Để tiết kiệm không gian, tôi không paste lại toàn bộ file user_commands nếu các lệnh kia không đổi)
    # Nếu bạn cần full file user_commands.py thì bảo tôi nhé.

async def setup(bot: commands.Bot):
    await bot.add_cog(UserCommandsCog(bot))
