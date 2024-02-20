from disnake.ext import commands
from disnake import Embed, Color
from database import execute_operation
from datetime import datetime as dt


class OnlineCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='access')
    async def access(self, ctx, cmd, user_id, sys=None):
        if self.is_access_command(ctx, cmd):
            user = await self.bot.fetch_user(user_id)
            if sys == '-d':
                execute_operation('discord-esbot', 'delete', table_name='personal_access_cmd',
                                  where=f'`cmd` = "{cmd}" AND `id_user` = {user_id} AND `server_id` = {ctx.guild.id}',
                                  commit=True)
                embed = Embed(
                    title=f'Снятие личного доступа',
                    description=f'Команда: /{cmd}\n↳ Пользователь: {user.name} (ID: {user_id})',
                    color=Color.red())
                await ctx.send(embed=embed)
            else:
                values = {
                    'cmd': cmd,
                    'id_user': user_id,
                    'server_id': ctx.guild.id
                }
                execute_operation('discord-esbot', 'insert', 'personal_access_cmd', values=values,
                                  commit=True)
                embed = Embed(
                    title=f'Выдача личного доступа',
                    description=f'Команда: /{cmd}\n↳ Пользователь: {user.name} (ID: {user_id})',
                    color=Color.red())
                await ctx.send(embed=embed)
        else:
            await ctx.send('Вы не имеете доступа к данной команде.')

    def is_access_command(self, ctx, cmd):
        role_access = execute_operation('discord-esbot', 'select', 'access_roles', columns='role',
                                        where=f'`server_id`={ctx.guild.id}')
        personal_access = execute_operation('discord-esbot', 'select', 'personal_access_cmd', columns='*',
                                            where=f'`cmd`="{cmd}" AND `id_user`={ctx.author.id}')
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

    @commands.command(name='access_roles')
    async def access_role(self, ctx, cmd, *, role, sys=None):
        if ctx.author.id == 479244541858152449:
            if sys == '-d':
                execute_operation('discord-esbot', 'delete', 'access_roles',
                                  where=f'`role`="{role}" AND `server_id`={ctx.guild.id} AND `cmd`="{cmd}"',
                                  commit=True)
                embed = Embed(
                    title=f'Снятие доступа по роли',
                    description=f'Команда: /{cmd}\n↳ Роль: {role}',
                    color=Color.red())
                await ctx.send(embed=embed)
            else:
                values = {
                    'role': role,
                    'server_id': ctx.guild.id,
                    'cmd': cmd
                }
                execute_operation('discord-esbot', 'insert', 'access_roles', values=values,
                                  commit=True)
                embed = Embed(
                    title=f'Выдача доступа по роли',
                    description=f'Команда: /{cmd}\n↳ Роль: {role}',
                    color=Color.red())
                await ctx.send(embed=embed)
        else:
            await ctx.send('Вы не имеете доступа к данной команде.')

    @commands.command(name='stats')
    async def add_exception(self, ctx, user_id=None, date=None):
        if self.is_access_command(ctx, cmd='stats'):
            if user_id is None:
                user_id = ctx.author.id
                date = dt.now().strftime("%d-%m-%Y")
            query = execute_operation('discord-esbot', 'select', 'logs_users_time_on_voice',
                                      columns='*',
                                      where=f'`user_id`={user_id} AND `date` = \'{date}\' AND `id_server`={ctx.guild.id}')

            query_exception = execute_operation('discord-esbot', 'select', 'servers_exceptions', columns='id',
                                                where=f'`id_server` = {ctx.guild.id}')

            if not query:
                await ctx.send(f'Нет статистики за {date} для пользователя (ID: {user_id})')
                return

            channel_stats = {}
            total_time = 0

            for info_user in query:
                if info_user['id_channel'] not in [exc['id'] for exc in query_exception]:
                    real = info_user['time_leave_voice'] - info_user['time_start']
                    total_time += real

                    channel_name = info_user["name_channel"]
                    channel_stats[channel_name] = channel_stats.get(channel_name, 0) + real

            embed = Embed(title=f'Статистика {query[0]["user_name"]} за {date}', color=Color.green())

            for channel, channel_time in channel_stats.items():
                embed.add_field(name=f'В канале "{channel}":',
                                value=f'{dt.utcfromtimestamp(channel_time).strftime("%H ч. %M м. %S с.")}',
                                inline=False)

            embed.add_field(name='Итоговое время в каналах:',
                            value=f'{dt.utcfromtimestamp(total_time).strftime("%H ч. %M м. %S с.")}', inline=False)

            await ctx.send(embed=embed)
        else:
            print("Не имеете доступа к данной команде")
