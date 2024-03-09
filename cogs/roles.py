import nextcord
from nextcord.ext import commands

from utils.classes.actions import ActionType
from utils.classes.bot import EsBot
from utils.neccessary import string_to_seconds, nick_without_tag
from utils.roles.role_info import role_info, RoleRequest


class Roles(commands.Cog):
    def __init__(self, bot: EsBot) -> None:
        self.bot = bot
        self.handler = bot.db.roles_handler

    @nextcord.slash_command(name='role', description='Подать заявление на роль.', default_member_permissions=nextcord.Permissions(administrator=True))
    async def request_role(self, interaction: nextcord.Interaction,
                           nickname: str = nextcord.SlashOption(name='никнейм', description='Ваш никнейм на сервере. В формате Name_Surname.'),
                           role: str = nextcord.SlashOption(name='роль', description='Роль, которую вы запрашиваете.', choices=role_info.keys()),
                           rang: int = nextcord.SlashOption(name='ранг', description='Ваш ранг во фракции.', min_value=1, max_value=9),
                           statistics: nextcord.Attachment = nextcord.SlashOption(name='статистика', description='Скриншот вашей статистики (M в игре) с /c 60.'),
                           statistics_hassle: nextcord.Attachment = nextcord.SlashOption(name='дополнение-к-статистике', description='Дополнение к скриншоту статистики [/c 60] (только если играете с Hassle).', required=False)):
        if not self.handler.check_nickname(nickname):
            return await interaction.response.send_message('Никнейм должен быть в формате Name_Surname.', ephemeral=True)
        if statistics.content_type not in ['image/png', 'image/jpeg'] or (statistics_hassle and statistics_hassle.content_type not in ['image/png', 'image/jpeg']):
            return await interaction.response.send_message('Статистика должна быть в формате изображения.', ephemeral=True)
        if rang > 4 and role == 'Федеральная Служба Исполнения Наказаний':
            return await interaction.response.send_message('Ранг не может быть выше 4 для этой роли.', ephemeral=True)

        statistics = await statistics.to_file()
        if statistics_hassle:
            statistics_hassle = await statistics_hassle.to_file()

        request = RoleRequest(interaction.user, interaction.guild, nickname, rang, role_info[role], statistics, statistics_hassle)
        if request.already_roled:
            await interaction.user.edit(nick=request.must_nick)
            return await interaction.send('Ваш ранг изменён.', ephemeral=True)

        if role := request.in_organization:
            await interaction.user.edit(nick=nick_without_tag(request.user.display_name))
            await interaction.user.remove_roles(role, reason=f'Заявление на роль.')

        await interaction.send('Заявление отправлено.', ephemeral=True)
        await request.send()


def setup(bot: EsBot) -> None:
    bot.add_cog(Roles(bot))
