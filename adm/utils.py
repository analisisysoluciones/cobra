def es_admin(user):
    return user.is_superuser or user.groups.filter(
        name__in=["Administradores", "Capturistas"]
    ).exists()