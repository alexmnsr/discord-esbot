import datetime

import nextcord
from nextcord.ext import commands

from utils.classes.actions import ActionType
from utils.classes.bot import EsBot
from utils.neccessary import string_to_seconds, add_role, checking_presence, restricted_command


class Punishments(commands.Cog):
    def __init__(self, bot: EsBot) -> None:
        self.bot = bot
        self.handler = bot.db.punishments_handler
        self.client = self.handler.client

    @commands.Cog.listener()
    async def on_ready(self):
        await checking_presence(self.bot)
        await self.handler.reload()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        mutes = await self.handler.mutes.user_muted(member.id, member.guild.id)

        async def give_role(role_name, action_id):
            await member.add_roles(nextcord.utils.get(member.guild.roles, name=role_name),
                                   reason=f'Rejoin. Action ID: {action_id}')

        for mute in mutes:
            if mute['type'] == 'full':
                await give_role('Mute » Text', mute['action_id'])
                await give_role('Mute » Voice', mute['action_id'])
            elif mute['type'] == 'text':
                await give_role('Mute » Text', mute['action_id'])
            elif mute['type'] == 'voice':
                await give_role('Mute » Voice', mute['action_id'])

    @commands.Cog.listener()
    async def on_member_join(self, member):
        mutes = await self.handler.database.get_mutes()

        if not mutes or member.guild.id != mutes[0]['guild_id']:
            return

        role_type = mutes[0]['type']
        role_name = f'Mute » {role_type.capitalize()}' if role_type in ['voice', 'text'] else 'Mute » Full'

        if role_name == 'Mute » Full':
            role_name = ['Mute » Text', 'Mute » Voice']
        await add_role(self.client, member.id, member.guild.id, mutes[0]['action_id'], role_name)
        await self.handler.mutes.wait_mute(mutes[0]['action_id'], mutes[0]['duration'], role_name)

    @nextcord.slash_command(name='mute')
    @restricted_command(1)
    async def mute_group(self, interaction):
        ...

    async def give_mute(self, interaction, user, duration, reason, role_name):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.', ephemeral=True)

        mute_seconds = string_to_seconds(duration)
        if not mute_seconds:
            return await interaction.send('Неверный формат длительности мута.', ephemeral=True)
        get, give, remove = self.handler.mutes.mute_info(role_name)
        if await get(user_id=user.id, guild_id=interaction.guild.id):
            return await interaction.send('У пользователя уже есть мут.', ephemeral=True)
        embed = ((nextcord.Embed(title='Выдача наказания', color=nextcord.Color.red())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Нарушитель', value=f'<@{user.id}>', inline=True)
                 .add_field(name='Причина', value=reason, inline=True)
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url))
        await interaction.send(embed=embed, ephemeral=True)

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

    @nextcord.slash_command(name='unmute', description="Снять мут с пользователя.")
    @restricted_command(1)
    async def unmute(self, interaction):
        ...

    async def remove_mute(self, interaction, user, role_name):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.', ephemeral=True)

        if not await self.handler.mutes.remove_mute(user.id, interaction.guild.id, role_name, interaction.user):
            return await interaction.send('У пользователя нет мута.', ephemeral=True)

        embed = nextcord.Embed(
            title='Снятие наказания',
            description=f'У пользователя {user.mention} снят мут.')
        await interaction.send(embed=embed, ephemeral=True)

    @unmute.subcommand(name='text', description="Снять текстовый мут с пользователя.")
    async def unmute_text(self, interaction,
                          user: str = nextcord.SlashOption('пользователь',
                                                           description='Пользователь, у которого вы хотите снять мут.',
                                                           required=True)):
        await self.remove_mute(interaction, user, 'Mute » Text')

    @unmute.subcommand(name='voice', description="Снять голосовой мут с пользователя.")
    async def unmute_voice(self, interaction,
                           user: str = nextcord.SlashOption('пользователь',
                                                            description='Пользователь, у которого вы хотите снять мут.',
                                                            required=True)):
        await self.remove_mute(interaction, user, 'Mute » Voice')

    @unmute.subcommand(name='full', description="Снять полный мут с пользователя.")
    async def unmute_full(self, interaction,
                          user: str = nextcord.SlashOption('пользователь',
                                                           description='Пользователь, у которого вы хотите снять мут.',
                                                           required=True)):
        await self.remove_mute(interaction, user, 'Mute » Full')

    @nextcord.slash_command(name='ban', description="Заблокировать пользователя на сервере")
    @restricted_command(4)
    async def ban(self, interaction,
                  user: str = nextcord.SlashOption('пользователь',
                                                   description='Пользователь, которому вы хотите выдать блокировку.',
                                                   required=True),
                  duration: int = nextcord.SlashOption('длительность',
                                                       description='Длительность блокировки. Пример: 5 = 5 дней. -1 = навсегда.',
                                                       required=True, min_value=-1, max_value=30),
                  reason: str = nextcord.SlashOption('причина', description='Причина блокировки.', required=True)):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.', ephemeral=True)

        embed = ((nextcord.Embed(title='Выдача бана', color=nextcord.Color.red())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Нарушитель', value=f'<@{user.id}>', inline=True)
                 .add_field(name='Длительность', value=f'{duration} дней' if duration != -1 else 'Навсегда',
                            inline=True)
                 .add_field(name='Причина', value=reason, inline=True)
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url))
        await interaction.send(embed=embed, ephemeral=True)

        await self.handler.bans.give_ban(ActionType.BAN_LOCAL, user=user, guild=interaction.guild,
                                         moderator=interaction.user, reason=reason, duration=duration)

    @nextcord.slash_command(name='gban', description="Заблокировать пользователя на всех серверах",
                            default_member_permissions=nextcord.Permissions(administrator=True))
    async def gban(self, interaction,
                   user: str = nextcord.SlashOption('пользователь',
                                                    description='Пользователь, которому вы хотите выдать блокировку.',
                                                    required=True),
                   duration: str = nextcord.SlashOption('длительность',
                                                        description='Длительность блокировки. Пример: 5 = 5 дней. -1 = навсегда.',
                                                        required=True),
                   reason: str = nextcord.SlashOption('причина', description='Причина блокировки.', required=True)):

        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.', ephemeral=True)

        embed = ((nextcord.Embed(title='Выдача бана на всех серверах', color=nextcord.Color.red())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Нарушитель', value=f'<@{user.id}>', inline=True)
                 .add_field(name='Длительность', value=f'{duration} дней' if duration != -1 else 'Навсегда',
                            inline=True)
                 .add_field(name='Причина', value=reason, inline=True)
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url))
        await interaction.send(embed=embed, ephemeral=True)

        await self.handler.bans.give_ban(ActionType.BAN_GLOBAL, user_id=user, guild=interaction.guild.id,
                                         moderator=interaction.user.id, reason=reason, duration=duration)

    @nextcord.slash_command(name='alist', description="Проверить /alist пользователя",
                            default_member_permissions=nextcord.Permissions(administrator=True))
    @restricted_command(5)
    async def alist(self, interaction,
                    user: str = nextcord.SlashOption('пользователь',
                                                     description='Пользователь, чей список наказаний вы хотите посмотреть.',
                                                     required=True),
                    type_punishment: str = nextcord.SlashOption('тип', description='Тип наказания', choices=['MUTE_TEXT', 'MUTE_VOICE', 'MUTE_FULL', 'BAN_LOCAL', 'BAN_GLOBAL'], default='FULL'),
                    server: str = nextcord.SlashOption('сервер',
                                                       description='Тот на котором запрашиваете (по умолчанию).',
                                                       default=1)):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.', ephemeral=True)
        if server == 1:
            server = interaction.guild.id
        list = await self.handler.database.actions.get_punishments(user_id=user.id, guild_id=server,
                                                                   type_punishment=type_punishment)
        embed = (
            nextcord.Embed(title=f'Список наказаний пользователя {user.display_name}', color=nextcord.Color.red())
            .set_author(name=user.display_name, icon_url=user.display_avatar.url)
            .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url))

        for items in list:
            embed.add_field(name=f'Наказание №{items["_id"]}',
                            value=f'Модератор: <@{items["moderator_id"]}>\n'
                                  f'Тип наказания: {items["action_type"].split(".")[-1]}\n'
                                  f'Причина: {items["payload"]["reason"]}\n',
                            inline=False)

        await interaction.send(embed=embed, ephemeral=True)


def setup(bot: EsBot) -> None:
    bot.add_cog(Punishments(bot))
