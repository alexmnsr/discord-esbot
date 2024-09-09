import datetime
import os
from typing import Any
import nextcord
from dotenv import load_dotenv
from nextcord.ext import commands

from connect_database import check_database_connection
from utils.classes.bot import EsBot
from utils.classes.vk.bot import BotStatus
from utils.neccessary import is_date_valid, date_autocomplete, restricted_command

load_dotenv()


class Online(commands.Cog):
    def __init__(self, bot: EsBot) -> None:
        self.bot = bot
        self.handler = bot.db.online_handler

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: nextcord.Member,
                                    before: nextcord.VoiceState,
                                    after: nextcord.VoiceState) -> None:
        # Ничего не изменять, если пользователь остался в том же канале
        if before.channel == after.channel:
            return

        guild = member.guild

        # Проверка, был ли пользователь отключен другим участником
        if before.channel is not None and after.channel is None:
            # Получаем последние записи журнала аудита
            audit_logs = await guild.audit_logs(limit=1, action=nextcord.AuditLogAction.member_disconnect).flatten()
            for log in audit_logs:
                # Проверка, что событие относится к пользователю и оно недавно
                if log.target == member and (nextcord.utils.utcnow() - log.created_at).total_seconds() < 5:
                    # Пользователя отключил другой участник
                    responsible_user = log.user
                    try:
                        required_roles = ["GMD", "SMD", "MD", "AD", "DS"]

                        # Проверяем, содержит ли ник пользователя одну из необходимых строк
                        if not any(role in member.display_name for role in required_roles):
                            return  # Прекращаем выполнение, если ник не содержит нужных параметров
                        await self.bot.vk.nt_error(
                            f'Сервер: {member.guild.name}\n'
                            f'Пользователь {responsible_user.display_name} отключил пользователя {member.display_name}.\n'
                            f'Возможен блат (отключение пользователей качающих онлайн)')
                    except:
                        pass
                    await self.handler.leave(member, before.channel, by=responsible_user)
                    return

        # Если прошлого канала нет, записывать заход в канал
        if before.channel is None:
            await self.handler.join(member, after.channel)
        # Если следующего канала нет, записывать выход с канала
        elif after.channel is None:
            await self.handler.leave(member, before.channel)
        # Переход в другой канал
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
        embed.add_field(name='Предыдущий канал',
                        value=f'{before.channel.name} ({before.channel.jump_url})\nID: {before.channel.id}',
                        inline=True)
        embed.add_field(name='Канал', value=f'{after.channel.name} ({after.channel.jump_url})\nID: {after.channel.id}',
                        inline=True)
        embed.set_author(name=member.display_name, icon_url=member.avatar.url)
        embed.set_footer(text=f'ID участника: {member.id} | {datetime.datetime.now().strftime("%H:%M:%S")}',
                         icon_url=member.avatar.url)
        log_channel = [channel for channel in member.guild.channels if "логи-голосовых-esbot" in channel.name][0]
        return log_channel, embed

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # Инициализируем статус
        bot_status = BotStatus(self.bot.vk)
        status_message = ""
        try:
            # Проверка подключения к базе данных
            if check_database_connection():
                status_message += "Подключение к базе данных: Успешно ✅\n"
            else:
                status_message += "Подключение к базе данных: Не удалось 🚫\n"

            # Обновление кнопок
            if await self.handler.reload(self.bot.get_all_channels()):
                status_message += "Обновление онлайна: Успешно ✅\n"
            else:
                status_message += "Обновление онлайна: Не удалось 🚫\n"

            await bot_status.send_status(status_message, BotStatus.SUCCESS)

        except Exception as e:
            error_message = f"Ошибка при запуске бота: {e} 🚫"
            await bot_status.send_status(error_message, BotStatus.ERROR)
            print(f"Ошибка при запуске бота: {e}")

    @nextcord.slash_command(name='online', description='Показать онлайн пользователя',
                            dm_permission=False)
    @restricted_command(1)
    async def online(self, interaction: nextcord.Interaction,
                     user: nextcord.Member = nextcord.SlashOption('пользователь',
                                                                  description='Пользователь, чей онлайн вы хотите проверить',
                                                                  required=False),
                     date: str = nextcord.SlashOption('дата', description="Дата в формате dd.mm.YYYY", required=False,
                                                      autocomplete_callback=date_autocomplete),
                     is_open_channels: bool = nextcord.SlashOption('открытые-каналы',
                                                          description="Подсчитывать онлайн только в открытых каналах.",
                                                          default=True)) -> Any:
        date = date or datetime.datetime.now().strftime('%d.%m.%Y')
        if not is_date_valid(date):
            await interaction.send(
                'Неверный формат даты. Формат: dd.mm.YYYY.\nПример: 07.07.2077',
                ephemeral=True
            )
            return

        user = user or interaction.user
        info = await self.handler.get_info(is_open_channels, user_id=user.id, guild_id=interaction.guild.id, date=date)

        embed = ((nextcord.Embed(title=f'💎 Онлайн за {date}', color=nextcord.Color.dark_purple())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Общее время', value=info.total_time)
                 .add_field(name='Каналы', value='Открытые' if is_open_channels else 'Все')
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url)
                 .set_footer(text=f'ID: {user.id}'))

        if info.channels:
            embed.add_field(name='Время в каналах', value=str(info), inline=False)

        await interaction.send(embed=embed)


def setup(bot: EsBot) -> None:
    bot.add_cog(Online(bot))
