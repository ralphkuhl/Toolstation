from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'klanten', views.CustomerViewSet, basename='customer')
router.register(r'assettypes', views.AssetTypeViewSet, basename='assettype')
router.register(r'assets', views.AssetViewSet, basename='asset')
router.register(r'onderhoudsplannen', views.MaintenancePlanViewSet, basename='maintenanceplan')
router.register(r'onderhoudstaken', views.MaintenanceTaskViewSet, basename='maintenancetask') # Deze wordt nu overschreven door de herdefinitie in views.py als we de viewset opnieuw registreren. Dat is prima.
router.register(r'rapporten', views.ReportViewSet, basename='report')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
]
