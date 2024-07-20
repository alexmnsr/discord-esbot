import datetime
import platform
import psutil

import nextcord
from nextcord.ext import commands

from utils.classes.bot import EsBot


class SysCommand(commands.Cog):
    def __init__(self, bot: EsBot) -> None:
        self.bot = bot
        self.handler = bot.db.online_handler

    @nextcord.slash_command(name='sys', description="Системные настройки и информация")
    async def sys(self, interaction: nextcord.Interaction):
        if interaction.user.id != 479244541858152449:
            return await interaction.send('Вы не имеете доступа к данной команде', ephemeral=True)
        uname = platform.uname()
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        embed = nextcord.Embed(title="Информация о системе", color=nextcord.Color.dark_purple())
        embed.add_field(name="Система", value=uname.system, inline=False)
        embed.add_field(name="Версия", value=uname.version, inline=False)
        embed.add_field(name="Архитектура", value=uname.machine, inline=False)
        embed.add_field(name="Время загрузки", value=boot_time.strftime('%Y-%m-%d %H:%M:%S'), inline=False)
        embed.add_field(name="Использование CPU", value=f"{cpu_usage}%", inline=False)

        memory_info = (
            f"Всего: {self.get_size(memory.total)}\n"
            f"Доступно: {self.get_size(memory.available)}\n"
            f"Использовано: {self.get_size(memory.used)}\n"
            f"Процент использования: {memory.percent}%"
        )
        embed.add_field(name="Информация о памяти", value=memory_info, inline=False)

        embed.add_field(name="Текущее время", value=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inline=False)

        await interaction.send(embed=embed, ephemeral=True)

    def get_size(self, bytes: int, suffix="B") -> str:
        """
        Преобразование байтов в удобочитаемый формат
        например:
            1253656 => '1.20MB'
            1253656678 => '1.17GB'
        """
        factor = 1024
        for unit in ["", "K", "M", "G", "T", "P"]:
            if bytes < factor:
                return f"{bytes:.2f}{unit}{suffix}"
            bytes /= factor


def setup(bot: EsBot) -> None:
    bot.add_cog(SysCommand(bot))
