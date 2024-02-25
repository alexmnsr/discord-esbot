from disnake.ext import commands
from disnake import Embed, Color
from database import execute_operation
from commands.accesses import access_commands as is_access_command


class GetInfoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name='moderators', description='список модерации')
    async def moderators(self, ctx):
        if is_access_command(ctx, 'moderators'):
            try:
                moderators_info = execute_operation('discord-esbot', 'select', 'moderator_servers',
                                                    columns='id_user, nickname_user, role_user',
                                                    where=f'`id_server`={ctx.guild.id}')
                admin_roles = {
                    'SYS': [],
                    'GMD': [],
                    'DS': [],
                    'K': [],
                    'Jr.D': [],
                    'A': [],
                    'SMD': [],
                    'MD': []
                }

                for info_moder in moderators_info:
                    role = info_moder["role_user"]
                    if role in admin_roles:
                        admin_roles[role].append(info_moder)

                embed = Embed(title=f'Информация о модераторах {ctx.guild.name} (ID: {ctx.guild.id}):\n',
                              color=Color.green())

                for role, admins in admin_roles.items():
                    if admins:
                        embed.add_field(name=f'Роль "{role}":', value='', inline=False)
                        for info_moder in admins:
                            name = info_moder["nickname_user"]
                            id_user = info_moder["id_user"]
                            embed.add_field(name=f'– {name} (id: {id_user})', value='', inline=False)

                await ctx.send(embed=embed)
            except Exception as e:
                print(e)
                await ctx.send("Произошла ошибка при выполнении команды.")
        else:
            await ctx.send('У вас нет доступа к данной команде.')

    @commands.slash_command(name='exceptions', description='исключения по каналам')
    async def exceptions(self, ctx):
        try:
            if is_access_command(ctx, 'exceptions'):
                embed_content = ''
                i_len = 0
                exceptions = execute_operation('discord-esbot', 'select', 'servers_exceptions',
                                               columns='id, name_channel',
                                               where=f'`id_server`={ctx.guild.id}')
                embed = Embed(title=f'Список исключений на {ctx.guild.name} (ID: {ctx.guild.id}):\n',
                              color=Color.green())
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


async def get_user_info(ctx, user_id):
    """id: member.id, nick_user: member.name, ник на сервере: member.display_name"""
    member = await ctx.guild.fetch_member(user_id)
    return member
