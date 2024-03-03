import nextcord
from nextcord.ext import commands

from utils.classes.bot import EsBot
from utils.neccessary import string_to_seconds


class Punishments(commands.Cog):
    def __init__(self, bot: EsBot) -> None:
        self.bot = bot
        self.handler = bot.db.punishments_handler

    @commands.Cog.listener()
    async def on_ready(self):
        await self.handler.reload()

    @nextcord.slash_command(name='mute')
    async def mute_group(self, interaction):
        ...

    @mute_group.subcommand(name='text', description="Выдать мут пользователю в текстовых каналах.")
    async def mute_text(self, interaction,
                        user: str = nextcord.SlashOption('пользователь', description='Пользователь, которому вы хотите выдать мут.', required=True),
                        reason: str = nextcord.SlashOption('причина', description='Причина мута.', required=True),
                        duration: str = nextcord.SlashOption('длительность', description='Длительность мута. Пример: 10м - 10 минут, 5д - 5 дней. Просто 10 - 10 минут.', required=True)):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.', ephemeral=True)

        mute_seconds = string_to_seconds(duration)
        if not mute_seconds:
            return await interaction.send('Неверный формат длительности мута.', ephemeral=True)
        embed = nextcord.Embed(
            title='Выдан текстовый мут',
            description=f'Пользователю {user.mention} выдан текстовый мут на {duration} по причине: {reason}')
        await interaction.send(embed=embed)

        await self.handler.give_text_mute(user=user, guild=interaction.guild, moderator=interaction.user, reason=reason, duration=mute_seconds)

    @mute_group.subcommand(name='voice', description="Выдать мут пользователю в голосовых каналах.")
    async def mute_voice(self, interaction):
        ...

    @mute_group.subcommand(name='full', description="Выдать полный мут пользователю.")
    async def mute_full(self, interaction):
        ...

    @nextcord.slash_command(name='unmute', description="Снять мут с пользователя.")
    async def unmute(self, interaction):
        ...

    @unmute.subcommand(name='text', description="Снять текстовый мут с пользователя.")
    async def unmute_text(self, interaction, user: str = nextcord.SlashOption('пользователь', description='Пользователь, у которого вы хотите снять мут.', required=True)):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.', ephemeral=True)

        if not await self.handler.remove_mute(user.id, interaction.guild.id):
            return await interaction.send('У пользователя нет текстового мута.', ephemeral=True)

        embed = nextcord.Embed(
            title='Снят текстовый мут',
            description=f'У пользователя {user.mention} снят текстовый мут.')
        await interaction.send(embed=embed)


def setup(bot: EsBot) -> None:
    bot.add_cog(Punishments(bot))
