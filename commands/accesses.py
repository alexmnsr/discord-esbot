from database import execute_operation


def access_commands(ctx, cmd):
    role_access = execute_operation('discord-esbot', 'select', 'access_roles', columns='role',
                                    where=f'`server_id`={ctx.guild.id}')
    personal_access = execute_operation('discord-esbot', 'select', 'personal_access_cmd', columns='*',
                                        where=f'`cmd`="{cmd}" AND `id_user`={ctx.author.id}')
    moderators_info = execute_operation('discord-esbot', 'select', 'moderator_servers',
                                        columns='role_user',
                                        where=f'`id_user`={ctx.author.id}')
    for sys_admin in moderators_info:
        if sys_admin['role_user'] == "SYS":
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
