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

    @nextcord.slash_command(name='mute', default_member_permissions=nextcord.Permissions(administrator=True))
    async def mute_group(self, interaction):
        ...

    @mute_group.subcommand(name='text', description="Выдать мут пользователю в текстовых каналах.")
    async def mute_text(self, interaction,
                        user: str = nextcord.SlashOption('пользователь',
                                                         description='Пользователь, которому вы хотите выдать мут.',
                                                         required=True),
                        duration: str = nextcord.SlashOption('длительность',
                                                             description='Длительность мута. Пример: 10м - 10 минут, 5д - 5 дней. Просто 10 - 10 минут.',
                                                             required=True),
                        reason: str = nextcord.SlashOption('причина', description='Причина мута.', required=True)):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.', ephemeral=True)

        mute_seconds = string_to_seconds(duration)
        if not mute_seconds:
            return await interaction.send('Неверный формат длительности мута.', ephemeral=True)

        await self.handler.give_text_mute(user=user, guild=interaction.guild, moderator=interaction.user, reason=reason,
                                          duration=mute_seconds)

        embed = ((nextcord.Embed(title='Выдача наказания', color=nextcord.Color.red())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Модератор', value=f'<@{interaction.user.id}>', inline=False)
                 .add_field(name='Нарушитель', value=f'<@{user.id}>', inline=True)
                 .add_field(name='Причина', value=reason, inline=True)
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url))
        await interaction.send(embed=embed)

    @mute_group.subcommand(name='voice', description="Выдать мут пользователю в голосовых каналах.")
    async def mute_voice(self, interaction,
                         user: str = nextcord.SlashOption('пользователь',
                                                          description='Пользователь которому вы хотите выдать мут.',
                                                          required=True),
                         duration: str = nextcord.SlashOption('длительность',
                                                              description='Длительность мута. Пример: 10м - 10 минут, 5д - 5 дней. Просто 10 - 10 минут.',
                                                              required=True),
                         reason: str = nextcord.SlashOption('причина', description='Причина мута.', required=True)):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.', ephemeral=True)

        mute_seconds = string_to_seconds(duration)
        if not mute_seconds:
            return await interaction.send('Неверный формат длительности мута.', ephemeral=True)

        await self.handler.give_voice_mute(user=user, guild=interaction.guild, moderator=interaction.user,
                                           reason=reason,
                                           duration=mute_seconds)

        embed = ((nextcord.Embed(title='Выдача наказания', color=nextcord.Color.red())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Модератор', value=f'<@{interaction.user.id}>', inline=False)
                 .add_field(name='Нарушитель', value=f'<@{user.id}>', inline=True)
                 .add_field(name='Причина', value=reason, inline=True)
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url))
        await interaction.send(embed=embed)

    @mute_group.subcommand(name='full', description="Выдать полный мут пользователю.")
    async def mute_full(self, interaction):
        ...

    @nextcord.slash_command(name='unmute', description="Снять мут с пользователя.",
                            default_member_permissions=nextcord.Permissions(administrator=True))
    async def unmute(self, interaction):
        ...

    @unmute.subcommand(name='text', description="Снять текстовый мут с пользователя.")
    async def unmute_text(self, interaction, user: str = nextcord.SlashOption('пользователь',
                                                                              description='Пользователь, у которого вы хотите снять мут.',
                                                                              required=True)):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.', ephemeral=True)

        if not await self.handler.remove_mute(user.id, interaction.guild.id, 'Mute » Text'):
            return await interaction.send('У пользователя нет текстового мута.', ephemeral=True)

        embed = nextcord.Embed(
            title='Снятие наказания',
            description=f'У пользователя {user.mention} снят текстовый мут.')
        await interaction.send(embed=embed)

    @unmute.subcommand(name='voice', description="Снять голосовой мут с пользователя.")
    async def unmute_voice(self, interaction, user: str = nextcord.SlashOption('пользователь',
                                                                               description='Пользователь, у которого вы хотите снять мут.',
                                                                               required=True)):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.', ephemeral=True)

        if not await self.handler.remove_mute(user.id, interaction.guild.id, 'Mute » Voice'):
            return await interaction.send('У пользователя нет голосового мута.', ephemeral=True)

        embed = nextcord.Embed(
            title='Снятие наказания',
            description=f'У пользователя {user.mention} снят голосовой мут.')
        await interaction.send(embed=embed)


def setup(bot: EsBot) -> None:
    bot.add_cog(Punishments(bot))
