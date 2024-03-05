import nextcord
from nextcord.ext import commands

from utils.classes.actions import ActionType
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

    async def give_mute(self, interaction, user, duration, reason, role_name):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.', ephemeral=True)

        mute_seconds = string_to_seconds(duration)
        if not mute_seconds:
            return await interaction.send('Неверный формат длительности мута.', ephemeral=True)

        embed = ((nextcord.Embed(title='Выдача наказания', color=nextcord.Color.red())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Модератор', value=f'<@{interaction.user.id}>', inline=False)
                 .add_field(name='Нарушитель', value=f'<@{user.id}>', inline=True)
                 .add_field(name='Причина', value=reason, inline=True)
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url))
        await interaction.send(embed=embed)

        await self.handler.mutes.give_mute(role_name, user=user, guild=interaction.guild, moderator=interaction.user,
                                           reason=reason,
                                           duration=mute_seconds)

    @mute_group.subcommand(name='text', description="Выдать мут пользователю в текстовых каналах.")
    async def mute_text(self, interaction,
                        user: str = nextcord.SlashOption('пользователь',
                                                         description='Пользователь, которому вы хотите выдать мут.',
                                                         required=True),
                        duration: str = nextcord.SlashOption('длительность',
                                                             description='Длительность мута. Пример: 10м - 10 минут, 5д - 5 дней. Просто 10 - 10 минут.',
                                                             required=True),
                        reason: str = nextcord.SlashOption('причина', description='Причина мута.', required=True)):
        await self.give_mute(interaction, user, duration, reason, 'Mute » Text')

    @mute_group.subcommand(name='voice', description="Выдать мут пользователю в голосовых каналах.")
    async def mute_voice(self, interaction,
                         user: str = nextcord.SlashOption('пользователь',
                                                          description='Пользователь которому вы хотите выдать мут.',
                                                          required=True),
                         duration: str = nextcord.SlashOption('длительность',
                                                              description='Длительность мута. Пример: 10м - 10 минут, 5д - 5 дней. Просто 10 - 10 минут.',
                                                              required=True),
                         reason: str = nextcord.SlashOption('причина', description='Причина мута.', required=True)):
        await self.give_mute(interaction, user, duration, reason, 'Mute » Voice')

    @mute_group.subcommand(name='full', description="Выдать полный мут пользователю.")
    async def mute_full(self, interaction,
                        user: str = nextcord.SlashOption('пользователь',
                                                         description='Пользователь, которому вы хотите выдать мут.',
                                                         required=True),
                        duration: str = nextcord.SlashOption('длительность',
                                                             description='Длительность мута. Пример: 10м - 10 минут, 5д - 5 дней. Просто 10 - 10 минут.',
                                                             required=True),
                        reason: str = nextcord.SlashOption('причина', description='Причина мута.', required=True)):
        await self.give_mute(interaction, user, duration, reason, 'Mute » Full')

    @nextcord.slash_command(name='unmute', description="Снять мут с пользователя.",
                            default_member_permissions=nextcord.Permissions(administrator=True))
    async def unmute(self, interaction):
        ...

    async def remove_mute(self, interaction, user, role_name):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.', ephemeral=True)

        if not await self.handler.mutes.remove_mute(user.id, interaction.guild.id, role_name):
            return await interaction.send('У пользователя нет мута.', ephemeral=True)

        embed = nextcord.Embed(
            title='Снятие наказания',
            description=f'У пользователя {user.mention} снят мут.')
        await interaction.send(embed=embed)

    @unmute.subcommand(name='text', description="Снять текстовый мут с пользователя.")
    async def unmute_text(self, interaction, user: str = nextcord.SlashOption('пользователь',
                                                                              description='Пользователь, у которого вы хотите снять мут.',
                                                                              required=True)):
        await self.remove_mute(interaction, user, 'Mute » Text')

    @unmute.subcommand(name='voice', description="Снять голосовой мут с пользователя.")
    async def unmute_voice(self, interaction, user: str = nextcord.SlashOption('пользователь',
                                                                               description='Пользователь, у которого вы хотите снять мут.',
                                                                               required=True)):
        await self.remove_mute(interaction, user, 'Mute » Voice')

    @unmute.subcommand(name='full', description="Снять полный мут с пользователя.")
    async def unmute_full(self, interaction, user: str = nextcord.SlashOption('пользователь',
                                                                              description='Пользователь, у которого вы хотите снять мут.',
                                                                              required=True)):
        await self.remove_mute(interaction, user, 'Mute » Full')

    @nextcord.slash_command(name='ban', description="Заблокировать пользователя",
                            default_member_permissions=nextcord.Permissions(administrator=True))
    async def bans_group(self, interaction):
        ...

    @bans_group.subcommand(name='ban', description="Заблокировать пользователя на сервере")
    async def ban(self, interaction,
                  user: str = nextcord.SlashOption('пользователь',
                                                   description='Пользователь, которому вы хотите выдать блокировку.',
                                                   required=True),
                  duration: str = nextcord.SlashOption('длительность',
                                                       description='Длительность блокировки. Пример: 5 = 5 дней. -1 = навсегда.',
                                                       required=True),
                  reason: str = nextcord.SlashOption('причина', description='Причина блокировки.', required=True)):
        await self.handler.bans.give_ban(ActionType.BAN_LOCAL, user_id=user, guild=interaction.guild, moderator=interaction.user, reason=reason, duration=duration)

    @bans_group.subcommand(name='gban', description="Заблокировать пользователя на всех серверах")
    async def gban(self, interaction,
                   user: str = nextcord.SlashOption('пользователь',
                                                    description='Пользователь, которому вы хотите выдать блокировку.',
                                                    required=True),
                   duration: str = nextcord.SlashOption('длительность',
                                                        description='Длительность блокировки. Пример: 5 = 5 дней. -1 = навсегда.',
                                                        required=True),
                   reason: str = nextcord.SlashOption('причина', description='Причина блокировки.', required=True)):
        ...
        await self.handler.bans.give_ban(ActionType.BAN_GLOBAL, user, interaction.guild.id, interaction.user.id, reason, duration)


def setup(bot: EsBot) -> None:
    bot.add_cog(Punishments(bot))
