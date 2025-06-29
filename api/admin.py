from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Customer, AssetType, Asset, MaintenancePlan, MaintenanceTask, Report

# Om het custom User model goed in de admin te krijgen
class CustomUserAdmin(UserAdmin):
    model = User
    # Voeg 'rol' toe aan de fieldsets in de admin interface
    # UserAdmin.fieldsets is een tuple, dus we moeten het omzetten naar een list om te kunnen toevoegen
    fieldsets = list(UserAdmin.fieldsets)
    fieldsets.append(
        ('Extra Info', {'fields': ('rol',)})
    )
    # Voeg 'rol' toe aan de list_display
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'rol')
    list_filter = UserAdmin.list_filter + ('rol',)


admin.site.register(User, CustomUserAdmin)
admin.site.register(Customer)
admin.site.register(AssetType)

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('naam_omschrijving', 'klant', 'asset_type', 'serienummer', 'locatie_in_gebouw')
    list_filter = ('asset_type', 'klant')
    search_fields = ('naam_omschrijving', 'serienummer', 'klant__naam')

@admin.register(MaintenancePlan)
class MaintenancePlanAdmin(admin.ModelAdmin):
    list_display = ('naam', 'frequentie', 'asset_type', 'asset', 'actief')
    list_filter = ('frequentie', 'asset_type', 'actief')
    search_fields = ('naam',)

@admin.register(MaintenanceTask)
class MaintenanceTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'asset', 'status', 'streef_einddatum', 'gebruiker_toegewezen')
    list_filter = ('status', 'streef_einddatum', 'gebruiker_toegewezen', 'asset__asset_type')
    search_fields = ('asset__naam_omschrijving', 'omschrijving_werkzaamheden')
    raw_id_fields = ('asset', 'onderhoudsplan', 'gebruiker_toegewezen') # Voor betere performance bij veel foreign keys
    date_hierarchy = 'streef_einddatum'

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'onderhoudstaak_info', 'gebruiker_opsteller', 'datum_opgesteld', 'asset_status_na_onderhoud')
    list_filter = ('asset_status_na_onderhoud', 'gebruiker_opsteller', 'datum_opgesteld')
    search_fields = ('onderhoudstaak__asset__naam_omschrijving', 'uitgevoerde_werkzaamheden', 'opmerkingen_bevindingen')
    raw_id_fields = ('onderhoudstaak', 'gebruiker_opsteller')
    date_hierarchy = 'datum_opgesteld'

    def onderhoudstaak_info(self, obj):
        if obj.onderhoudstaak:
            return f"Taak {obj.onderhoudstaak.id} ({obj.onderhoudstaak.asset.naam_omschrijving})"
        return "-"
    onderhoudstaak_info.short_description = 'Onderhoudstaak'
