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

    # --- 1. LỆNH PROFILE ---
    @app_commands.command(name="profile", description="Xem thông tin tài khoản của bạn")
    async def profile(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        await interaction.response.defer()
        
        data = await database.get_user_data(target.id)
        if not data:
            data = {'level': 1, 'xp': 0, 'fund': 0, 'coupon': 0, 'role_group': 'Chưa chọn', 'language': 'vi'}

        rank_name = "Novice"
        if data.get('role_group'):
            tiers = config.LEVEL_TIERS.get(data['role_group'], {})
            current_lv = data.get('level', 1)
            found_key = None
            for lvl_req in sorted(tiers.keys()):
                if current_lv >= lvl_req:
                    found_key = tiers[lvl_req]
                else:
                    break
            if found_key: rank_name = found_key

        embed = discord.Embed(title=f"Hồ sơ: {target.display_name}", color=discord.Color.blue())
        embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
        embed.add_field(name="🏆 Cấp độ", value=f"Lv. {data.get('level', 1)}", inline=True)
        embed.add_field(name="✨ XP", value=f"{data.get('xp', 0):,}", inline=True)
        embed.add_field(name="🔰 Phe phái", value=f"{data.get('role_group', 'Chưa chọn')}", inline=True)
        embed.add_field(name="🏅 Rank", value=rank_name, inline=True)
        
        fund_emoji = config.ROLE_IDS.get('FUND_EMOJI', '💰')
        coupon_emoji = config.ROLE_IDS.get('COUPON_EMOJI', '🎫')
        
        embed.add_field(name=f"{fund_emoji} Fund", value=f"{data.get('fund', 0):,}", inline=True)
        embed.add_field(name=f"{coupon_emoji} Coupon", value=f"{data.get('coupon', 0):,}", inline=True)

        await interaction.followup.send(embed=embed)

    # --- 2. LỆNH DAILY ---
    @app_commands.command(name="daily", description="Nhận quà điểm danh hàng ngày")
    async def daily(self, interaction: discord.Interaction):
        data = await database.get_user_data(interaction.user.id)
        if not data: data = {'discord_id': str(interaction.user.id)}

        user_lang = data.get('language', 'vi')
        last_daily = data.get('last_daily')
        
        if last_daily and last_daily.date() == datetime.now().date():
            msg = localization.get_string(user_lang, 'daily_already') or "⛔ Bạn đã nhận quà hôm nay rồi!"
            return await interaction.response.send_message(msg, ephemeral=True)

        fund_reward = random.randint(5000, 10000)
        coupon_reward = random.randint(5000, 10000)

        data['fund'] = data.get('fund', 0) + fund_reward
        data['coupon'] = data.get('coupon', 0) + coupon_reward
        data['last_daily'] = datetime.now()
        
        await database.save_user_data(interaction.user.id, data)
        
        fund_emoji = config.ROLE_IDS.get('FUND_EMOJI', '💰')
        coupon_emoji = config.ROLE_IDS.get('COUPON_EMOJI', '🎫')

        msg = localization.get_string(user_lang, 'daily_success', 
                fund_reward=fund_reward, fund_emoji=fund_emoji, 
                coupon_reward=coupon_reward, coupon_emoji=coupon_emoji)
        
        if not msg: msg = f"✅ Điểm danh thành công!\nBạn nhận được: **+{fund_reward:,} {fund_emoji}** và **+{coupon_reward:,} {coupon_emoji}**"

        await interaction.response.send_message(msg)

    # --- 3. LỆNH EXCHANGE ---
    @app_commands.command(name="exchange", description="Đổi Coupon sang Fund (1:1)")
    @app_commands.describe(amount="Số lượng Coupon")
    async def exchange(self, interaction: discord.Interaction, amount: int):
        if amount <= 0: return await interaction.response.send_message("❌ Số lượng > 0", ephemeral=True)
        data = await database.get_user_data(interaction.user.id)
        if not data: return await interaction.response.send_message("❌ Chưa có tài khoản", ephemeral=True)
        if data.get('coupon', 0) < amount: return await interaction.response.send_message("❌ Không đủ Coupon", ephemeral=True)

        data['coupon'] -= amount
        data['fund'] = data.get('fund', 0) + amount
        await database.save_user_data(interaction.user.id, data)
        
        fund_emoji = config.ROLE_IDS.get('FUND_EMOJI', '💰')
        coupon_emoji = config.ROLE_IDS.get('COUPON_EMOJI', '🎫')
        await interaction.response.send_message(f"✅ Đã đổi **{amount:,} {coupon_emoji}** lấy **{amount:,} {fund_emoji}**.")

    # --- 4. LỆNH TRANSFER ---
    @app_commands.command(name="transfer", description="Chuyển tiền")
    @app_commands.describe(receiver="Người nhận", currency="Loại tiền", amount="Số tiền")
    @app_commands.choices(currency=config.CURRENCY_CHOICES)
    async def transfer(self, interaction: discord.Interaction, receiver: discord.Member, currency: app_commands.Choice[str], amount: int):
        if amount <= 0: return await interaction.response.send_message("❌ Số tiền > 0", ephemeral=True)
        if receiver.bot or receiver.id == interaction.user.id: return await interaction.response.send_message("❌ Người nhận không hợp lệ", ephemeral=True)

        await interaction.response.defer()
        sender_data = await database.get_user_data(interaction.user.id)
        if not sender_data: return await interaction.followup.send("❌ Chưa có tài khoản")

        key = currency.value
        if sender_data.get(key, 0) < amount: return await interaction.followup.send("❌ Số dư không đủ")

        receiver_data = await database.get_user_data(receiver.id)
        if not receiver_data: receiver_data = {'discord_id': str(receiver.id), 'fund': 0, 'coupon': 0, 'xp': 0, 'level': 1}

        sender_data[key] -= amount
        receiver_data[key] = receiver_data.get(key, 0) + amount

        await database.save_user_data(interaction.user.id, sender_data)
        await database.save_user_data(receiver.id, receiver_data)

        emoji = config.ROLE_IDS.get('FUND_EMOJI') if key == 'fund' else config.ROLE_IDS.get('COUPON_EMOJI')
        await interaction.followup.send(f"✅ Đã chuyển **{amount:,} {emoji}** cho {receiver.mention}.")

    # --- 5. LỆNH ALL-IN (LOGIC MỚI: 80% VỐN & ANIMATION DÀI) ---
    @app_commands.command(name="allin", description="Cược 80% tài sản! (Quay số: x2, x3, x5)")
    @app_commands.describe(currency="Loại tiền cược")
    @app_commands.choices(currency=config.CURRENCY_CHOICES)
    async def allin(self, interaction: discord.Interaction, currency: app_commands.Choice[str]):
        # 1. Kiểm tra tiền
        data = await database.get_user_data(interaction.user.id)
        if not data: return await interaction.response.send_message("❌ Chưa có tài khoản.", ephemeral=True)

        key = currency.value
        total_balance = data.get(key, 0)
        
        # Lấy Emoji từ Config
        fund_emoji = config.ROLE_IDS.get('FUND_EMOJI', '💰')
        coupon_emoji = config.ROLE_IDS.get('COUPON_EMOJI', '🎫')
        bet_emoji = fund_emoji if key == 'fund' else coupon_emoji

        # --- LOGIC 80% TÀI SẢN ---
        bet_amount = int(total_balance * 0.8) # Chỉ lấy 80%
        safe_amount = total_balance - bet_amount # 20% còn lại an toàn

        if bet_amount <= 0:
            return await interaction.response.send_message(f"❌ Số dư quá ít để cược! Cần ít nhất để cược 1 {bet_emoji}.", ephemeral=True)

        # 2. Gửi tin nhắn chờ
        await interaction.response.send_message(f"🎰 **{interaction.user.display_name}** chơi lớn **80%** vốn!\nĐang cược: **{bet_amount:,} {bet_emoji}** (Giữ lại: {safe_amount:,})\n\n**[ 🔄 | 🔄 | 🔄 ]**")
        msg = await interaction.original_response()

        # 3. Backend Logic (Tính kết quả dựa trên số tiền cược 80%)
        is_win = random.choice([True, False])
        multiplier = 0
        symbols = []

        if is_win:
            roll = random.randint(1, 100)
            if roll <= 80:     # 80% Win: x2
                multiplier = 2
                result_title = "CHIẾN THẮNG! (x2)"
                color = discord.Color.green()
            elif roll <= 97:   # 17% Win: x3
                multiplier = 3
                result_title = "QUÁ DỮ! (x3)"
                color = discord.Color.gold()
            else:              # 3% Win: x5
                multiplier = 5
                result_title = "JACKPOT!!! (x5)"
                color = discord.Color.purple()
            
            symbols = [bet_emoji, bet_emoji, bet_emoji]
            
            winnings = int(bet_amount * multiplier) # Tiền thắng tính trên 80% cược
            profit = winnings - bet_amount
            new_balance = safe_amount + winnings # Tổng mới = Phần giữ lại + Tiền thắng
            data[key] = new_balance
        else:
            # Thua: Mất 80% đã cược
            pool = [fund_emoji, coupon_emoji, "💣", "👻", "❌", "💢"]
            s1 = random.choice(pool)
            s2 = random.choice(pool)
            s3 = random.choice(pool)
            while s1 == s2 == s3: s3 = random.choice(pool) # Tránh trùng
            symbols = [s1, s2, s3]
            
            result_title = "THẤT BẠI..."
            color = discord.Color.red()
            winnings = 0
            profit = -bet_amount
            new_balance = safe_amount # Chỉ còn lại phần giữ lại
            data[key] = new_balance

        # 4. Lưu Database
        await database.save_user_data(interaction.user.id, data)

        # 5. Animation (Chạy ít nhất 4 bước như yêu cầu)
        # Pool icon rác để làm hiệu ứng quay
        anim_pool = [fund_emoji, coupon_emoji, "🍒", "🍋", "🔔", "💎", "7️⃣", "🍇"]
        
        def get_rand_row():
            return f"[ {random.choice(anim_pool)} | {random.choice(anim_pool)} | {random.choice(anim_pool)} ]"

        # Bước 1: Quay ngẫu nhiên (0.5s)
        await asyncio.sleep(0.5)
        await msg.edit(content=f"🎰 **{interaction.user.display_name}** đang quay...\nCược: **{bet_amount:,} {bet_emoji}**\n\n**{get_rand_row()}**")
        
        # Bước 2: Quay ngẫu nhiên tiếp (0.5s)
        await asyncio.sleep(0.5)
        await msg.edit(content=f"🎰 **{interaction.user.display_name}** đang quay...\nCược: **{bet_amount:,} {bet_emoji}**\n\n**{get_rand_row()}**")

        # Bước 3: Chốt ô 1 (0.5s)
        await asyncio.sleep(0.5)
        await msg.edit(content=f"🎰 **{interaction.user.display_name}** đang quay...\nCược: **{bet_amount:,} {bet_emoji}**\n\n**[ {symbols[0]} | {random.choice(anim_pool)} | {random.choice(anim_pool)} ]**")

        # Bước 4: Chốt ô 2 (0.5s)
        await asyncio.sleep(0.5)
        await msg.edit(content=f"🎰 **{interaction.user.display_name}** đang quay...\nCược: **{bet_amount:,} {bet_emoji}**\n\n**[ {symbols[0]} | {symbols[1]} | {random.choice(anim_pool)} ]**")

        # Bước 5: Kết quả cuối cùng (0.5s)
        await asyncio.sleep(0.5)
        
        embed = discord.Embed(title=f"🎰 {result_title}", color=color)
        embed.description = f"# {symbols[0]} | {symbols[1]} | {symbols[2]}"
        
        embed.add_field(name="Người chơi", value=interaction.user.mention, inline=True)
        embed.add_field(name="Tiền cược (80%)", value=f"{bet_amount:,} {bet_emoji}", inline=True)
        
        if is_win:
            embed.add_field(name="Kết quả", value=f"**Thắng x{multiplier}**", inline=True)
            embed.add_field(name="Lãi nhận được", value=f"+{profit:,} {bet_emoji}", inline=False)
        else:
            embed.add_field(name="Kết quả", value="**Thua cược**", inline=True)
            embed.add_field(name="Mất", value=f"-{bet_amount:,} {bet_emoji}", inline=False)
            
        embed.add_field(name="Số dư mới", value=f"**{new_balance:,} {bet_emoji}**", inline=False)
        embed.set_footer(text=f"Game All-in | {datetime.now().strftime('%H:%M:%S')}")

        await msg.edit(content=None, embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(UserCommandsCog(bot))
