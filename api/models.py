from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('monteur', 'Monteur'),
        ('inspecteur', 'Inspecteur'),
        ('admin', 'Administrator'),
    ]
    rol = models.CharField(max_length=20, choices=ROLE_CHOICES, default='monteur', blank=False, null=False)

    def __str__(self):
        return self.username

class Customer(models.Model):
    naam = models.CharField(max_length=255)
    adres = models.CharField(max_length=255, blank=True, null=True)
    postcode = models.CharField(max_length=10, blank=True, null=True)
    plaats = models.CharField(max_length=100, blank=True, null=True)
    locatie_gebouw_omschrijving = models.TextField(blank=True, null=True)
    contactpersoon_naam = models.CharField(max_length=100, blank=True, null=True)
    contactpersoon_email = models.EmailField(blank=True, null=True)
    contactpersoon_telefoon = models.CharField(max_length=20, blank=True, null=True)
    aangemaakt_op = models.DateTimeField(auto_now_add=True)
    gewijzigd_op = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.naam

class AssetType(models.Model):
    naam = models.CharField(max_length=100, unique=True)
    omschrijving = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.naam

class Asset(models.Model):
    klant = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='assets')
    asset_type = models.ForeignKey(AssetType, on_delete=models.PROTECT)
    naam_omschrijving = models.CharField(max_length=255)
    merk = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    serienummer = models.CharField(max_length=100, blank=True, null=True, unique=True)
    installatiedatum = models.DateField(blank=True, null=True)
    locatie_in_gebouw = models.CharField(max_length=255, blank=True, null=True)
    specificaties_bijzonderheden = models.TextField(blank=True, null=True)
    aangemaakt_op = models.DateTimeField(auto_now_add=True)
    gewijzigd_op = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.naam_omschrijving} ({self.asset_type.naam}) bij {self.klant.naam}"

class MaintenancePlan(models.Model):
    FREQ_CHOICES = [
        ('maandelijks', 'Maandelijks'),
        ('halfjaarlijks', 'Halfjaarlijks'),
        ('jaarlijks', 'Jaarlijks'),
    ]
    asset_type = models.ForeignKey(AssetType, on_delete=models.CASCADE, blank=True, null=True, help_text="Plan voor een specifiek asset type")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, blank=True, null=True, help_text="Of plan voor een individuele asset (override type)")
    naam = models.CharField(max_length=255)
    frequentie = models.CharField(max_length=20, choices=FREQ_CHOICES)
    standaard_omschrijving_werkzaamheden = models.TextField(blank=True, null=True)
    actief = models.BooleanField(default=True)
    aangemaakt_op = models.DateTimeField(auto_now_add=True)
    gewijzigd_op = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.naam

class MaintenanceTask(models.Model):
    STATUS_CHOICES = [
        ('gepland', 'Gepland'),
        ('in_uitvoering', 'In uitvoering'),
        ('voltooid', 'Voltooid'),
        ('geannuleerd', 'Geannuleerd'),
    ]
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='tasks')
    onderhoudsplan = models.ForeignKey(MaintenancePlan, on_delete=models.SET_NULL, blank=True, null=True)
    gebruiker_toegewezen = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='assigned_tasks')
    omschrijving_werkzaamheden = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='gepland')
    geplande_startdatum = models.DateField(blank=True, null=True)
    streef_einddatum = models.DateField()
    daadwerkelijke_startdatum = models.DateTimeField(blank=True, null=True)
    daadwerkelijke_einddatum = models.DateTimeField(blank=True, null=True)
    aangemaakt_op = models.DateTimeField(auto_now_add=True)
    gewijzigd_op = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Taak {self.id} voor {self.asset.naam_omschrijving} (Status: {self.get_status_display()}, Streef: {self.streef_einddatum})"

class Report(models.Model):
    onderhoudstaak = models.OneToOneField(MaintenanceTask, on_delete=models.CASCADE, related_name='report', help_text="De onderhoudstaak waar dit rapport bij hoort.")
    gebruiker_opsteller = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_reports', help_text="Monteur/inspecteur die het rapport heeft opgesteld.")
    uitgevoerde_werkzaamheden = models.TextField(help_text="Gedetailleerde omschrijving van de uitgevoerde werkzaamheden.")
    gebruikte_materialen = models.TextField(blank=True, null=True, help_text="Lijst van gebruikte materialen en onderdelen.")
    opmerkingen_bevindingen = models.TextField(blank=True, null=True, help_text="Eventuele opmerkingen, bevindingen of aanbevelingen.")
    asset_status_na_onderhoud = models.CharField(max_length=100, blank=True, null=True, help_text="Status van de asset na het onderhoud (bijv. 'In bedrijf', 'Vereist opvolging', 'Buiten bedrijf').")
    werktijd_minuten = models.PositiveIntegerField(blank=True, null=True, help_text="Totale werktijd in minuten.")
    datum_opgesteld = models.DateTimeField(auto_now_add=True, help_text="Datum en tijd waarop het rapport is aangemaakt/opgesteld.")
    aangemaakt_op = models.DateTimeField(auto_now_add=True)
    gewijzigd_op = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Rapport voor taak {self.onderhoudstaak.id} ({self.onderhoudstaak.asset.naam_omschrijving})"
