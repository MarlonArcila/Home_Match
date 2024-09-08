from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import AbstractUser

# Extended user model to allow roles for landlord and tenant
class CustomUser(AbstractUser):
    # Define if the user is a landlord or a tenant
    USER_TYPE_CHOICES = (
        ('arrendador', 'Landlord'),
        ('arrendatario', 'Tenant'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    foto_perfil = models.ImageField(upload_to='profile_pics/', null=True, blank=True)  # Profile picture

    # Field to store the address of the Avalanche Core Wallet
    direccion_wallet = models.CharField(max_length=255, null=True, blank=True, help_text="Avalanche wallet address")
    
    def __str__(self):
        return self.username  # Return username as string representation of the user

# Model to store property information
class Inmueble(models.Model):
    # Basic property information
    nombre = models.CharField(max_length=255)  # Property name
    direccion = models.CharField(max_length=255)  # Property address
    descripcion = models.TextField()  # Description of the property
    precio_base = models.DecimalField(max_digits=10, decimal_places=2)  # Base price
    
    # Physical criteria of the property
    metros_cuadrados = models.DecimalField(max_digits=6, decimal_places=2)  # Square meters
    habitaciones = models.PositiveIntegerField()  # Number of rooms
    baños = models.PositiveIntegerField()  # Number of bathrooms
    estado_conservacion = models.CharField(max_length=255)  # Conservation state
    amenidades = models.TextField()  # Amenities of the property
    
    # Added value criteria
    atractivos_turisticos = models.BooleanField(default=False)  # Tourist attractions nearby
    paradas_transporte_publico = models.BooleanField(default=False)  # Public transport stops nearby
    establecimientos_comerciales = models.BooleanField(default=False)  # Commercial establishments nearby
    establecimientos_educativos = models.BooleanField(default=False)  # Educational institutions nearby

    # Additional information
    fecha_publicacion = models.DateTimeField(auto_now_add=True)  # Date of publication

    def __str__(self):
        return self.nombre  # Return the property name as string representation

# Model to store criteria selected by the tenant using a Likert scale (1-5)
class ArrendatarioCriterios(models.Model):
    arrendatario = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  # Tenant (foreign key to CustomUser)
    inmueble = models.ForeignKey(Inmueble, on_delete=models.CASCADE, related_name='criterios_arrendatario')  # Property (foreign key to Inmueble)
    
    # Physical criteria rated on a Likert scale (1-5)
    metros_cuadrados = models.IntegerField()  # Square meters rating
    habitaciones = models.IntegerField()  # Rooms rating
    baños = models.IntegerField()  # Bathrooms rating
    estado_conservacion = models.IntegerField()  # Conservation state rating
    amenidades = models.IntegerField()  # Amenities rating
    
    # Added value criteria rated on a Likert scale (1-5)
    atractivos_turisticos = models.IntegerField()  # Tourist attractions rating
    espacios_publicos = models.IntegerField()  # Public spaces rating
    paradas_transporte_publico = models.IntegerField()  # Public transport stops rating
    establecimientos_comerciales = models.IntegerField()  # Commercial establishments rating
    establecimientos_educativos = models.IntegerField()  # Educational institutions rating
    
# Model to store property images
class InmuebleFoto(models.Model):
    inmueble = models.ForeignKey(Inmueble, related_name='fotos', on_delete=models.CASCADE)  # Property (foreign key to Inmueble)
    imagen = models.ImageField(upload_to='inmuebles_fotos/')  # Image field to upload photos

    def __str__(self):
        return f"Photo of {self.inmueble.direccion}"  # Return the property's address as string representation of the image

# Model to manage bids placed on a property
class Puja(models.Model):
    inmueble = models.ForeignKey(Inmueble, on_delete=models.CASCADE, related_name='pujas')  # Property (foreign key to Inmueble)
    arrendatario = models.CharField(max_length=255)  # Name of the tenant placing the bid
    monto = models.DecimalField(max_digits=10, decimal_places=2)  # Bid amount
    moneda = models.CharField(max_length=3, choices=[('USD', 'Dollars'), ('COP', 'Colombian Pesos')], default='COP')  # Currency (default is COP)
    fecha_puja = models.DateTimeField(auto_now_add=True)  # Date of the bid
    
    # Define bid closing time after 12 hours
    def cierre_puja(self):
        return self.fecha_puja + timedelta(hours=12)  # Bid closes 12 hours after placement
    
    def __str__(self):
        return f"Bid by {self.arrendatario} for {self.monto} {self.moneda} on {self.inmueble}"  # Return a formatted string describing the bid
