import nextcord

from utils.neccessary import user_visual


class RoleInfo:
    def __init__(self, role_names, tag):
        self.role_names = role_names
        self.tag = tag

    def find(self, guild_roles):
        for role in guild_roles:
            if role.name.lower() in [r.lower() for r in self.role_names]:
                return role
        return None


role_info = {
    'Правительство': RoleInfo(['Правительство', 'Пра-во'], 'Пра-во | {}'),
    'Министерство Обороны': RoleInfo(['Министерство Обороны', 'МО'], 'МО | {}'),
    'Министерство Здравоохранения': RoleInfo(['Министерство Здравоохранения', 'МЗ'], 'МЗ | {}'),
    'Теле-Радио Компания «Ритм»': RoleInfo(['Теле-Радио Компания «Ритм»', 'ТРК'], 'ТРК | {}'),
    'Министерство Внутренних Дел': RoleInfo(['Министерство Внутренних Дел', 'МВД'], 'МВД | {}'),
    'Федеральная Служба Исполнения Наказаний': RoleInfo(['Федеральная Служба Исполнения Наказаний', 'ФСИН'], 'ФСИН | {}')
}


class RoleRequest:
    def __init__(self, user, guild, nickname, rang, role_info_, statistics, statistics_hassle=None):
        self.user = user
        self.guild = guild
        self.nickname = nickname
        self.rang = rang
        self.role_info = role_info_
        self.statistics = statistics
        self.statistics_hassle = statistics_hassle

    @property
    def in_organization(self):
        for key, value in role_info.items():
            if role := value.find(self.user.roles):
                return role
        return

    @property
    def already_roled(self):
        if self.role_info.find(self.user.roles):
            return True

    @property
    def roles_channel(self):
        return [c for c in self.guild.channels if c.name in 'заявки-на-роли'][0]

    @property
    def check_embed(self):
        embed = nextcord.Embed(
            title='📘 Заявление на роль',
            color=nextcord.Color.dark_blue(),
        )
        embed.add_field(name='Никнейм', value=self.nickname)
        embed.add_field(name='Роль', value=self.role_info.find(self.guild.roles).mention, inline=False)
        embed.add_field(name='Ранг', value=self.rang, inline=False)
        embed.add_field(name='Пользователь', value=user_visual(self.user), inline=False)
        return embed

    @property
    def files(self):
        return [self.statistics, self.statistics_hassle] if self.statistics_hassle else [self.statistics]

    @property
    def must_nick(self):
        tag = f'[{self.role_info.tag.format(self.rang)}] '
        return tag + self.nickname

    async def send(self):
        await self.roles_channel.send(embed=self.check_embed, files=self.files)
