import discord
from discord.ext import commands
from datetime import datetime, timedelta
import random
import config
import database
import localization

def get_required_xp(level):
    return int(config.BASE_XP_TO_LEVEL * (level + 1) ** config.XP_SCALING)

# --- HÀM QUAN TRỌNG CHO REACTION ROLES ---
def get_current_rank_role(data):
    group = data.get('role_group')
    level = data.get('level', 0)
    if not group or level == 0: return None
    tiers = config.LEVEL_TIERS.get(group)
    if not tiers: return None
    current_rank_key = None
    for lvl in sorted(tiers.keys()):
        if level >= lvl:
            current_rank_key = tiers[lvl]
        else:
            break
    return config.ROLE_IDS.get(current_rank_key) if current_rank_key else None

async def update_user_level_and_roles(member: discord.Member, data: dict):
    """Hàm cập nhật Role dựa trên Level và Group (Dùng chung cho cả Level Up và Reaction Role)"""
    guild = member.guild
    if not data.get('role_group'): return # Nếu chưa chọn phe thì bỏ qua

    # 1. Tính toán Role Rank mới
    new_role_id = get_current_rank_role(data)
    if new_role_id:
        new_role = guild.get_role(new_role_id)
        if not new_role: return

        # 2. Xóa Role Rank cũ (của cả Hero và Monster để tránh lỗi phe)
        group_prefix = 'HERO' if data['role_group'] == 'HERO' else 'M_'
        # Lấy tất cả ID rank có thể có
        all_rank_ids = []
        for key, val in config.ROLE_IDS.items():
            # Lọc các key rank (bỏ qua key GROUP)
            if (key.startswith("HERO_") or key.startswith("M_")) and not key.endswith("_GROUP"):
                all_rank_ids.append(val)
        
        roles_to_remove = [r for r in member.roles if r.id in all_rank_ids and r.id != new_role.id]

        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason="Auto Rank Update")
        
        # 3. Thêm Role mới
        if new_role not in member.roles:
            await member.add_roles(new_role, reason="Level Up / Change Group")
            try:
                user_lang = data.get('language', 'vi')
                await member.send(localization.get_string(user_lang, 'rank_up_dm', new_role_name=new_role.name))
            except: pass

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
        
        # Loop để phòng trường hợp cộng nhiều XP một lúc (ví dụ lệnh admin buff)
        level_up_occured = False
        while True:
            required_xp = get_required_xp(current_level)
            if data['xp'] >= required_xp:
                data['xp'] -= required_xp
                current_level += 1
                data['level'] = current_level
                level_up_occured = True
                
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
            else:
                break
        
        # Lưu DB và Cập nhật Role
        await database.save_user_data(user_id, data)
        if level_up_occured:
            await update_user_level_and_roles(message.author, data)

async def setup(bot: commands.Bot):
    await bot.add_cog(LevelSystemCog(bot))
