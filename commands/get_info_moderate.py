from disnake.ext import commands
from disnake import Embed, Color
from database import execute_operation


class GetInfoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='moderators')
    async def get_moderators(self, ctx):
        if self.is_access_command(ctx, 'moderators'):
            try:
                moderators_info = execute_operation('discord-esbot', 'select', 'moderator_servers',
                                                    columns='id_user, nickname_user, role_user',
                                                    where=f'`id_server`={ctx.guild.id}')
                embed = Embed(title=f'Список модераторов {ctx.guild.name} (ID: {ctx.guild.id}):\n',
                              color=Color.green())
                for info_moder in moderators_info:
                    embed.add_field(name=f'Модератор {info_moder["nickname_user"]} (ID: {info_moder["id_user"]}):',
                                    value=f'↳ Роль: {info_moder["role_user"]}',
                                    inline=False)
                await ctx.send(embed=embed)
            except:
                await ctx.send("Ошибка")
        else:
            await ctx.send('Вы не имеете доступа к данной команде.')

    @commands.command(name='exceptions_voice')
    async def exceptions_voice(self, ctx):
        try:
            if self.is_access_command(ctx, 'exceptions_voice'):
                embed_content = ''
                i_len = 0
                exceptions = execute_operation('discord-esbot', 'select', 'servers_exceptions',
                                               columns='id, name_channel',
                                               where=f'`id_server`={ctx.guild.id}')
                embed = Embed(title=f'Список исключений на {ctx.guild.name} (ID: {ctx.guild.id}):\n', color=Color.green())
                for exceptions_id in exceptions:
                    embed_content += f'Канал {exceptions_id["name_channel"]} (ID: {exceptions_id["id"]})\n'
                    i_len += 1
                embed.add_field(name=f'{embed_content}',
                                value=f'Общее количество закрытых каналов {i_len}',
                                inline=False)
                await ctx.send(embed=embed)
        except:
            await ctx.send('Ошибка')
        else:
            await ctx.send('Вы не имеете доступа к данной команде.')

    def is_access_command(self, ctx, cmd):
        role_access = execute_operation('discord-esbot', 'select', 'access_roles', columns='role',
                                        where=f'`server_id`={ctx.guild.id}')
        personal_access = execute_operation('discord-esbot', 'select', 'personal_access_cmd', columns='*',
                                            where=f'`cmd`="{cmd}" AND `id_user`={ctx.author.id}')
        moderators_info = execute_operation('discord-esbot', 'select', 'moderator_servers',
                                            columns='id_user, role_user',
                                            where=f'`id_server`={ctx.guild.id}')
        for sys_admin in moderators_info:
            if sys_admin == ctx.author.id:
                return True
        if personal_access and personal_access[0]['id_user'] == ctx.author.id:
            return True
        elif role_access and isinstance(role_access, list):
            if personal_access and personal_access[0]['id_user'] == ctx.author.id:
                return True
            user_roles = set(role.name for role in ctx.author.roles)
            db_roles = set(entry.get('role') for entry in role_access)
            return bool(user_roles.intersection(db_roles))
        else:
            return False
