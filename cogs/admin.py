import discord
from discord.ext import commands

class ChannelSelectView(discord.ui.View):
    def __init__(self, bot, current_ids):
        super().__init__(timeout=120)
        self.bot = bot
        self.select = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            placeholder="SELECT HERE (max 3)...",
            min_values=1, max_values=3,
            default_values=[discord.Object(id=i) for i in current_ids]
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        # Update the isolated Log Database
        await self.bot.log_db.execute("DELETE FROM channel_logs WHERE guild_id = ?", (interaction.guild.id,))
        for channel in self.select.values:
            await self.bot.log_db.execute(
                "INSERT INTO channel_logs (guild_id, channel_id) VALUES (?, ?)", 
                (interaction.guild.id, channel.id)
            )
        await self.bot.log_db.commit()
        
        mentions = ", ".join([f"<#{c.id}>" for c in self.select.values])
        await interaction.response.send_message(f"<a:emoji_19:1503628162754543666>*** DONE !*** 'channel, {mentions} ''is now in action !``.", ephemeral=True)

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup_channel")
    @commands.has_permissions(administrator=True)
    async def setup_channel(self, ctx):
        # Fetch current IDs from the isolated database
        async with self.bot.log_db.execute("SELECT channel_id FROM channel_logs WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
            current_ids = [row[0] for row in await cursor.fetchall()]

        # Fixed: Only one embed and one view are sent now
        embed = discord.Embed(
            title="<:emoji_21:1503659921798074408> INTRECT CHANNEL SETUP",
            description="**Select the designated channel for all Goldie interaction, you can undone this setting** ..",
            color=0x000001
        )
        view = ChannelSelectView(self.bot, current_ids)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Admin(bot))