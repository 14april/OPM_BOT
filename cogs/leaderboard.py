import discord
from discord.ext import commands
from discord import app_commands
import config
import database
import localization

class LeaderboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    leaderboard_group = app_commands.Group(name="leaderboard", description="Xem bảng xếp hạng theo XP")

    async def get_lang(self, interaction):
        data = await database.get_user_data(interaction.user.id)
        return data.get('language', 'vi') if data else 'vi'

    async def show_leaderboard(self, interaction, role_group, title_key, desc_key, rank_name, color):
        await interaction.response.defer()
        user_lang = await self.get_lang(interaction)
        
        conn = database.get_connection()
        if not conn:
            return await interaction.followup.send(localization.get_string(user_lang, 'lb_db_not_ready'), ephemeral=True)

        try:
            cursor = conn.cursor(dictionary=True)
            # Lấy Top 10 người có role_group tương ứng, sắp xếp theo Level và XP
            sql = """
                SELECT discord_id, xp, level FROM discord_users 
                WHERE role_group = %s 
                ORDER BY level DESC, xp DESC 
                LIMIT 10
            """
            cursor.execute(sql, (role_group,))
            rows = cursor.fetchall()

            embed = discord.Embed(
                title=localization.get_string(user_lang, title_key, rank_name=rank_name),
                description=localization.get_string(user_lang, desc_key, rank_name=rank_name),
                color=color
            )

            if not rows:
                embed.description = localization.get_string(user_lang, 'lb_no_players')
            else:
                desc_text = ""
                for i, entry in enumerate(rows):
                    member_id = int(entry['discord_id'])
                    member = interaction.guild.get_member(member_id)
                    member_name = member.mention if member else localization.get_string(user_lang, 'lb_user_id', id=member_id)
                    desc_text += f"**{i+1}.** {member_name} - **Lv.{entry['level']}** - **{entry['xp']:,}** XP\n"
                embed.description = desc_text
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            print(f"Lỗi Leaderboard: {e}")
            await interaction.followup.send(localization.get_string(user_lang, 'lb_query_error'), ephemeral=True)
        finally:
            if conn.is_connected(): cursor.close(); conn.close()

    @leaderboard_group.command(name="hero", description="Bảng xếp hạng Hero")
    async def leaderboard_hero(self, interaction: discord.Interaction):
        # Để đơn giản, bảng xếp hạng hiện tại sẽ gom chung tất cả Hero. 
        # Nếu muốn lọc theo Rank A, B, C cụ thể thì cần lưu Rank vào DB.
        await self.show_leaderboard(
            interaction, 'HERO', 'lb_hero_title', 'lb_hero_desc', "All Class", discord.Color.gold()
        )

    @leaderboard_group.command(name="monster", description="Bảng xếp hạng Monster")
    async def leaderboard_monster(self, interaction: discord.Interaction):
        await self.show_leaderboard(
            interaction, 'MONSTER', 'lb_monster_title', 'lb_monster_desc', "All Class", discord.Color.purple()
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
