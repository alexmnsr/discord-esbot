import nextcord
from nextcord.ext import commands

from utils.button_state.views.Roles import RoleRequest
from utils.classes.actions import ActionType
from utils.classes.bot import EsBot
from utils.neccessary import nick_without_tag, restricted_command, load_buttons
from utils.roles.role_info import role_info


def command_mention(app_command, guild_id):
    command_id = app_command.command_ids.get(guild_id)

    if not command_id:
        command_id = app_command.command_ids.get(None)

    return f'</{app_command.name}:{command_id}>'


class Roles(commands.Cog):
    def __init__(self, bot: EsBot) -> None:
        self.bot = bot
        self.handler = bot.db.roles_handler
        self.buttons = bot.db.state_buttons

    async def rang_callback(self, interaction: nextcord.Interaction, rang):
        for option in interaction.data.get('options', []):
            if option['name'] == "роль":
                role = role_info.get(option['value'])
                break
        else:
            return await interaction.response.send_autocomplete([])

        if rang and len(role.rangs) >= rang >= 1:
            enumerated_rangs = [(rang, role.rangs[rang - 1])]
        else:
            enumerated_rangs = enumerate(role.rangs, 1)

        options = {f'[{v}] {k}': v for v, k in enumerated_rangs}
        await interaction.response.send_autocomplete(options)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await self.reload()

    @nextcord.slash_command(name='role', description='Подать заявление на роль.')
    async def request_role(self, interaction: nextcord.Interaction,
                           nickname: str = nextcord.SlashOption(name='никнейм',
                                                                max_length=32,
                                                                description='Ваш никнейм на сервере. В формате Name_Surname.'),
                           role: str = nextcord.SlashOption(name='роль',
                                                            description='Роль, которую вы запрашиваете.',
                                                            choices=role_info.keys()),
                           rang: int = nextcord.SlashOption(name='ранг',
                                                            description='Ваш ранг во фракции.',
                                                            min_value=1,
                                                            max_value=8,
                                                            autocomplete_callback=rang_callback),
                           statistics: nextcord.Attachment = nextcord.SlashOption(name='статистика',
                                                                                  description='Скриншот вашей статистики (M в игре) с /c 60.'),
                           statistics_hassle: nextcord.Attachment = nextcord.SlashOption(name='дополнение-к-статистике',
                                                                                         description='Дополнение к скриншоту статистики [/c 60] (только если играете с Hassle).',
                                                                                         required=False)):
        if not self.handler.check_nickname(nickname):
            return await interaction.response.send_message('Никнейм должен быть в формате Name_Surname.',
                                                           ephemeral=True)
        if statistics.content_type not in ['image/png', 'image/jpeg'] or (
                statistics_hassle and statistics_hassle.content_type not in ['image/png', 'image/jpeg']):
            return await interaction.response.send_message('Статистика должна быть в формате изображения.',
                                                           ephemeral=True)
        if rang > 4 and role == 'Федеральная Служба Исполнения Наказаний':
            return await interaction.response.send_message('Ранг не может быть выше 4 для этой роли.', ephemeral=True)

        statistics = await statistics.to_file()
        if statistics_hassle:
            statistics_hassle = await statistics_hassle.to_file()

        request = RoleRequest(interaction.user, interaction.guild, nickname, rang, role_info[role], statistics,
                              statistics_hassle)
        if request.already_roled:
            await interaction.user.edit(nick=request.must_nick)
            await self.handler.remove_request(interaction.user, interaction.guild, False, False)
            return await interaction.send('Ваш ранг изменён.', ephemeral=True)

        if await self.handler.request_role(interaction.user, interaction.guild):
            message = await interaction.send('Заявление обрабатывается.')
            async for channel_message in interaction.channel.history(limit=5):
                if channel_message.content and channel_message.content.startswith('## Используйте'):
                    await channel_message.delete()
                    break
            await interaction.channel.send(
                f"## Используйте {command_mention(interaction.application_command, interaction.guild_id)} для подачи заявления")
        else:
            return await interaction.send("Вы уже подавали на роль.", ephemeral=True)

        embed = nextcord.Embed(
            colour=nextcord.Color.dark_green(),
            title='✅ Вы подали заявление на роль.'
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name='ℹ️ Информация о заявлении', value=f'Никнейм: {nickname.replace("_", " ")}\n'
                                                                f'Роль: {role}\n'
                                                                f'Ранг: {rang}', inline=False)

        await message.edit('', embed=embed)
        await request.send(user_id=interaction.user.id, guild_id=interaction.guild.id)

        if role := request.in_organization:
            if (wo_tag := nick_without_tag(request.user.display_name)) != request.user.display_name:
                try:
                    await interaction.user.edit(nick=wo_tag)
                except:
                    pass
            await interaction.user.remove_roles(role, reason=f'Заявление на роль.')

    @nextcord.user_command('Снять роль фракции')
    @restricted_command(2)
    async def remove_roles_moder(self, interaction: nextcord.Interaction, member: nextcord.Member):
        roles = []
        for key, value in role_info.items():
            for roles_member in member.roles:
                if value.role_names[0] in roles_member.name or value.role_names[1] in roles_member.name:
                    role = roles_member
                    roles.append(role)
        if not roles:
            return await interaction.send('У пользователя нет гос.ролей.', ephemeral=True)

        action_id = await self.handler.actions.add_action(
            user_id=member.id,
            guild_id=member.guild.id,
            moderator_id=interaction.user.id,
            action_type=ActionType.ROLE_REMOVE,
            payload={
                'role': roles[0].name
            }
        )
        await member.remove_roles(*roles, reason=f'Action ID: {action_id}')

        await interaction.send(f'Роль {roles[0].mention} была снята.', ephemeral=True)

    @nextcord.user_command('Удалить заявку на выдачу роли')
    @restricted_command(1)
    async def remove_role_database(self, interaction: nextcord.Interaction, member: nextcord.Member):
        await self.handler.remove_request(member, interaction.guild, False, False)
        await interaction.send(f'Заявка пользователя на роль была удалена', ephemeral=True)

    async def reload(self):
        await load_buttons(self.handler.client, self.buttons, type_buttons='Roles')


def setup(bot: EsBot) -> None:
    bot.add_cog(Roles(bot))
