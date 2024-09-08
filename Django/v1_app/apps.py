# Import the AppConfig class from django.apps module
from django.apps import AppConfig

# Define a new configuration class for the 'v1_app' application
class V1AppConfig(AppConfig):
    # Specify the default field type for automatically created primary keys in models
    default_auto_field = "django.db.models.BigAutoField"
    
    # Set the name of the application as 'v1_app'
    name = "v1_app"
