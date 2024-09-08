# Importamos el módulo 'admin' de Django, que nos permite personalizar y registrar modelos para el panel de administración.
from django.contrib import admin

# Importamos el modelo 'CustomUser' desde el archivo models.py. Este modelo representa una versión personalizada del modelo de usuario de Django.
from .models import CustomUser

# Registramos el modelo 'CustomUser' en el sitio de administración de Django. Esto permite que el modelo sea gestionado desde el panel de administración, 
# lo que facilita la creación, edición y eliminación de usuarios personalizados.
admin.site.register(CustomUser)
