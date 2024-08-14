import datetime
import os
from typing import Any
import nextcord
from nextcord.ext import commands
from utils.classes.bot import EsBot
from utils.neccessary import is_date_valid, date_autocomplete, restricted_command


class Online(commands.Cog):
    def __init__(self, bot: EsBot) -> None:
        self.bot = bot
        self.handler = bot.db.online_handler

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: nextcord.Member,
                                    before: nextcord.VoiceState,
                                    after: nextcord.VoiceState) -> None:
        if before.channel == after.channel:
            return

        if before.channel is None:
            await self.handler.join(member, after.channel)
        elif after.channel is None:
            await self.handler.leave(member, before.channel)
        else:
            try:
                log_channel, embed = self.send_embed_online(member=member, after=after, before=before)
                await log_channel.send(embed=embed)
            except:
                pass
            await self.handler.leave(member, before.channel, transition=True)
            await self.handler.join(member, after.channel, transition=True)

    @staticmethod
    def send_embed_online(member: nextcord.Member, before: nextcord.VoiceState = None,
                          after: nextcord.VoiceState = None):
        embed = nextcord.Embed(title='Лог Онлайн', color=nextcord.Color.dark_purple())
        embed.add_field(name='', value='Участник перешел в другой канал', inline=False)
        embed.add_field(name='Предыдущий канал', value=f'{before.channel.name} ({before.channel.jump_url})\nID: {before.channel.id}', inline=True)
        embed.add_field(name='Канал', value=f'{after.channel.name} ({after.channel.jump_url})\nID: {after.channel.id}', inline=True)
        embed.set_author(name=member.display_name, icon_url=member.avatar.url)
        embed.set_footer(text=f'ID участника: {member.id} | {datetime.datetime.now().strftime("%H:%M:%S")}',
                         icon_url=member.avatar.url)
        log_channel = [channel for channel in member.guild.channels if "логи-голосовых-esbot" in channel.name][0]
        return log_channel, embed

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not os.getenv('DEBUG'):
            await self.bot.vk.send_message(123123, 'Вы запустили бота на хостинге. Началось обновление онлайна, наказаний, кнопок')
            await self.handler.reload(self.bot.get_all_channels())

    @nextcord.slash_command(name='online', description='Показать онлайн пользователя',
                            dm_permission=False)
    @restricted_command(1)
    async def online(self, interaction: nextcord.Interaction,
                     user: nextcord.Member = nextcord.SlashOption('пользователь',
                                                                  description='Пользователь, чей онлайн вы хотите проверить',
                                                                  required=False),
                     date: str = nextcord.SlashOption('дата', description="Дата в формате dd.mm.YYYY", required=False,
                                                      autocomplete_callback=date_autocomplete),
                     is_open: bool = nextcord.SlashOption('открытые-каналы',
                                                          description="Подсчитывать онлайн только в открытых каналах.",
                                                          default=True)) -> Any:
        if not date:
            date = datetime.datetime.now().strftime('%d.%m.%Y')
        elif not is_date_valid(date):
            return await interaction.send('Неверный формат даты. Формат: dd.mm.YYYY.\n'
                                          'Пример: 07.07.2077', ephemeral=True)

        if not user:
            user = interaction.user
        info = await self.handler.get_info(is_open, user_id=user.id, guild_id=interaction.guild.id, date=date)

        embed = ((nextcord.Embed(title=f'💎 Онлайн за {date}', color=nextcord.Color.dark_purple())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Общее время', value=info.total_time)
                 .add_field(name='Каналы', value='Открытые' if is_open else 'Все')
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url)
                 .set_footer(text=f'ID: {user.id}'))

        if info.channels:
            embed.add_field(name='Время в каналах', value=str(info), inline=False)

        await interaction.send(embed=embed)


def setup(bot: EsBot) -> None:
    bot.add_cog(Online(bot))
