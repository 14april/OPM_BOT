import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import random
import config
import database
import localization

class UserCommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_lang(self, interaction):
        data = await database.get_user_data(interaction.user.id)
        return data.get('language', 'vi') if data else 'vi'

    # --- 1. LỆNH PROFILE (XEM THÔNG TIN) ---
    @app_commands.command(name="profile", description="Xem thông tin tài khoản của bạn")
    async def profile(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        await interaction.response.defer()
        
        data = await database.get_user_data(target.id)
        if not data:
            # Nếu user chưa có data, tạo data ảo để hiển thị
            data = {
                'level': 1, 'xp': 0, 'fund': 0, 'coupon': 0, 
                'role_group': 'Chưa chọn', 'language': 'vi'
            }

        # Tính toán Rank hiển thị
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

        embed = discord.Embed(
            title=f"Hồ sơ anh hùng: {target.display_name}",
            color=discord.Color.blue()
        )
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

    # --- 2. LỆNH DAILY (ĐIỂM DANH) ---
    @app_commands.command(name="daily", description="Nhận quà điểm danh hàng ngày")
    async def daily(self, interaction: discord.Interaction):
        data = await database.get_user_data(interaction.user.id)
        if not data: data = {'discord_id': str(interaction.user.id)}

        user_lang = data.get('language', 'vi')
        last_daily = data.get('last_daily')
        
        if last_daily and last_daily.date() == datetime.now().date():
            msg = localization.get_string(user_lang, 'daily_already')
            if not msg: msg = "⛔ Bạn đã nhận quà hôm nay rồi! Hãy quay lại ngày mai."
            return await interaction.response.send_message(msg, ephemeral=True)

        # Random phần thưởng (5k - 10k)
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

    # --- 3. LỆNH EXCHANGE (ĐỔI TIỀN) ---
    @app_commands.command(name="exchange", description="Đổi Coupon sang Fund (Tỷ lệ 1 Coupon = 1 Fund)")
    @app_commands.describe(amount="Số lượng Coupon muốn đổi")
    async def exchange(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ Số lượng phải lớn hơn 0.", ephemeral=True)

        data = await database.get_user_data(interaction.user.id)
        if not data: return await interaction.response.send_message("❌ Bạn chưa có tài khoản.", ephemeral=True)

        current_coupon = data.get('coupon', 0)
        if current_coupon < amount:
            return await interaction.response.send_message(f"❌ Bạn không đủ Coupon. Hiện có: {current_coupon:,}", ephemeral=True)

        data['coupon'] -= amount
        data['fund'] = data.get('fund', 0) + amount
        
        await database.save_user_data(interaction.user.id, data)
        
        fund_emoji = config.ROLE_IDS.get('FUND_EMOJI', '💰')
        coupon_emoji = config.ROLE_IDS.get('COUPON_EMOJI', '🎫')
        
        await interaction.response.send_message(f"✅ Đã đổi **{amount:,} {coupon_emoji}** lấy **{amount:,} {fund_emoji}**.")

    # --- 4. LỆNH TRANSFER (CHUYỂN TIỀN) ---
    @app_commands.command(name="transfer", description="Chuyển tiền cho người khác")
    @app_commands.describe(receiver="Người nhận", currency="Loại tiền", amount="Số tiền")
    @app_commands.choices(currency=config.CURRENCY_CHOICES)
    async def transfer(self, interaction: discord.Interaction, receiver: discord.Member, currency: app_commands.Choice[str], amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ Số tiền phải lớn hơn 0.", ephemeral=True)
        if receiver.id == interaction.user.id:
            return await interaction.response.send_message("❌ Không thể tự chuyển cho chính mình.", ephemeral=True)
        if receiver.bot:
            return await interaction.response.send_message("❌ Không thể chuyển tiền cho Bot.", ephemeral=True)

        await interaction.response.defer()

        sender_data = await database.get_user_data(interaction.user.id)
        if not sender_data: return await interaction.followup.send("❌ Bạn chưa có tài khoản.")

        key = currency.value
        sender_bal = sender_data.get(key, 0)

        if sender_bal < amount:
            return await interaction.followup.send(f"❌ Số dư không đủ. Bạn có: {sender_bal:,}")

        receiver_data = await database.get_user_data(receiver.id)
        if not receiver_data: 
            receiver_data = {'discord_id': str(receiver.id), 'fund': 0, 'coupon': 0, 'xp': 0, 'level': 1}

        sender_data[key] -= amount
        receiver_data[key] = receiver_data.get(key, 0) + amount

        await database.save_user_data(interaction.user.id, sender_data)
        await database.save_user_data(receiver.id, receiver_data)

        emoji = config.ROLE_IDS.get('FUND_EMOJI') if key == 'fund' else config.ROLE_IDS.get('COUPON_EMOJI')
        await interaction.followup.send(f"✅ Đã chuyển **{amount:,} {emoji}** cho {receiver.mention}.")

    # --- 5. LỆNH ALL-IN (CÁ CƯỢC CẬP NHẬT) ---
    @app_commands.command(name="allin", description="Cược tất tay! (Cơ hội x2, x3, x5)")
    @app_commands.describe(currency="Loại tiền muốn cược")
    @app_commands.choices(currency=config.CURRENCY_CHOICES)
    async def allin(self, interaction: discord.Interaction, currency: app_commands.Choice[str]):
        data = await database.get_user_data(interaction.user.id)
        if not data: return await interaction.response.send_message("❌ Bạn chưa có tài khoản.", ephemeral=True)

        key = currency.value
        balance = data.get(key, 0)

        if balance <= 0:
            return await interaction.response.send_message("❌ Bạn đã hết tiền (" + key + ") để cược!", ephemeral=True)

        # Logic Game: 50% Thắng, 50% Thua
        is_win = random.choice([True, False])
        
        emoji = config.ROLE_IDS.get('FUND_EMOJI') if key == 'fund' else config.ROLE_IDS.get('COUPON_EMOJI')

        if is_win:
            # Random tỉ lệ thắng (Khi đã thắng)
            roll = random.randint(1, 100)
            
            if roll <= 80:
                # 80% cơ hội: x2
                multiplier = 2
                msg_header = "🎰 **THẮNG!** Bạn đã nhân đôi tài sản!"
                color = discord.Color.green()
            elif roll <= 97:
                # 17% cơ hội (từ 81 đến 97): x3
                multiplier = 3
                msg_header = "🎉 **MAY MẮN!** Bạn đã nhân 3 tài sản!"
                color = discord.Color.gold()
            else:
                # 3% cơ hội (từ 98 đến 100): x5
                multiplier = 5
                msg_header = "💎 **JACKPOT!** NHÂN 5 TÀI SẢN!!!"
                color = discord.Color.purple()

            new_balance = int(balance * multiplier)
            data[key] = new_balance
            
            msg = f"{msg_header}\nSố dư cũ: {balance:,}\nSố dư mới: **{new_balance:,} {emoji}** (x{multiplier})"
        else:
            # Thua: Mất hết (Về 0)
            data[key] = 0
            msg = f"💀 **R.I.P!** Bạn đã mất tất cả **{balance:,} {emoji}**..."
            color = discord.Color.red()

        await database.save_user_data(interaction.user.id, data)
        
        embed = discord.Embed(description=msg, color=color)
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(UserCommandsCog(bot))
