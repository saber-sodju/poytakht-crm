from django.contrib import admin
from .models import Supplier, Material, MaterialMovement

admin.site.register(Supplier)
admin.site.register(Material)
admin.site.register(MaterialMovement)
