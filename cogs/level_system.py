import discord
from discord.ext import commands
from datetime import datetime, timedelta
import random
import config
import database
import localization

def get_required_xp(level):
    return int(config.BASE_XP_TO_LEVEL * (level + 1) ** config.XP_SCALING)

class LevelSystemCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id
        data = await database.get_user_data(user_id)
        
        # Kiểm tra cooldown
        last_xp = data.get('last_xp_message')
        if last_xp and (datetime.now() - last_xp < timedelta(seconds=config.XP_COOLDOWN_SECONDS)):
            return

        # Cộng XP
        xp_gain = random.randint(15, 25)
        data['xp'] = data.get('xp', 0) + xp_gain
        data['last_xp_message'] = datetime.now()

        # Xử lý Level Up
        current_level = data.get('level', 1)
        required_xp = get_required_xp(current_level)
        
        if data['xp'] >= required_xp:
            data['xp'] -= required_xp
            data['level'] = current_level + 1
            
            # Thưởng tiền
            fund_reward = random.randint(5000, 10000)
            data['fund'] = data.get('fund', 0) + fund_reward
            
            user_lang = data.get('language', 'vi')
            try:
                await message.author.send(
                    localization.get_string(user_lang, 'level_up_dm', 
                    mention=message.author.mention, new_level=data['level'], 
                    reward_fund=fund_reward, fund_emoji=config.ROLE_IDS['FUND_EMOJI'], 
                    reward_coupon=0, coupon_emoji="")
                )
            except: pass

        await database.save_user_data(user_id, data)

async def setup(bot: commands.Bot):
    await bot.add_cog(LevelSystemCog(bot))
