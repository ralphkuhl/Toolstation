from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
# from django.template.loader import get_template # Voor PDF generatie met Django templates
# import pdfkit # Voorbeeld library, of WeasyPrint, ReportLab
from django.utils import timezone

from .models import User, Customer, AssetType, Asset, MaintenancePlan, MaintenanceTask, Report
from .serializers import (
    UserSerializer, CustomerSerializer, AssetTypeSerializer, AssetSerializer,
    MaintenancePlanSerializer, MaintenanceTaskSerializer, ReportSerializer
)

# ViewSet voor het User model
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # permission_classes = [permissions.IsAuthenticated] # Standaard al ingesteld in settings.py
    # Voor specifieke permissies per actie, kun je get_permissions() overriden

    # Zorg ervoor dat alleen admins nieuwe gebruikers kunnen aanmaken of andere users kunnen zien/wijzigen
    # Monteurs/inspecteurs moeten wel hun eigen profiel kunnen zien/wijzigen.
    def get_permissions(self):
        if self.action == 'create' or (self.action != 'retrieve' and self.action != 'update' and self.action != 'partial_update' and self.kwargs.get('pk') != str(self.request.user.pk)):
             # Alleen admins mogen nieuwe users aanmaken, of andere users dan zichzelf benaderen (behalve retrieve/update eigen profiel)
            self.permission_classes = [permissions.IsAdminUser]
        elif self.action in ['retrieve', 'update', 'partial_update'] and self.kwargs.get('pk') == str(self.request.user.pk):
            # Gebruikers mogen hun eigen gegevens ophalen en bijwerken
            self.permission_classes = [permissions.IsAuthenticated]
        elif self.request.user and self.request.user.is_staff: # Admin mag alles
             self.permission_classes = [permissions.IsAdminUser]
        else: # Andere gevallen (bijv. list view voor niet-admins)
             self.permission_classes = [permissions.IsAdminUser] # Standaard naar admin only voor list etc.
        return super().get_permissions()


# ViewSet voor het Customer model
class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all().order_by('naam')
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated] # Alleen ingelogde gebruikers

    # Optioneel: filteren, zoeken
    # filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # filterset_fields = ['plaats']
    # search_fields = ['naam', 'adres', 'contactpersoon_naam']
    # ordering_fields = ['naam', 'plaats']

# ViewSet voor AssetType
class AssetTypeViewSet(viewsets.ModelViewSet):
    queryset = AssetType.objects.all().order_by('naam')
    serializer_class = AssetTypeSerializer
    permission_classes = [permissions.IsAuthenticated] # Ingelogde gebruikers, evt. IsAdminUser voor create/update/delete

# ViewSet voor Asset
class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.all().select_related('klant', 'asset_type').order_by('naam_omschrijving')
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    # Voorbeeld: filter assets per klant_id als query parameter ?klant_id=X
    def get_queryset(self):
        queryset = super().get_queryset()
        klant_id = self.request.query_params.get('klant_id')
        if klant_id:
            queryset = queryset.filter(klant_id=klant_id)
        return queryset

# ViewSet voor MaintenancePlan
class MaintenancePlanViewSet(viewsets.ModelViewSet):
    queryset = MaintenancePlan.objects.all().select_related('asset_type', 'asset').order_by('naam')
    serializer_class = MaintenancePlanSerializer
    permission_classes = [permissions.IsAuthenticated] # Evt. IsAdminUser voor create/update/delete

# ViewSet voor MaintenanceTask
class MaintenanceTaskViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceTask.objects.all().select_related('asset', 'gebruiker_toegewezen', 'onderhoudsplan').order_by('-streef_einddatum')
    serializer_class = MaintenanceTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    # Voorbeeld: filter taken op status of toegewezen gebruiker
    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Alleen taken voor de ingelogde monteur/inspecteur, tenzij admin
        user = self.request.user
        if not user.is_staff: # Als geen admin/staff
            queryset = queryset.filter(gebruiker_toegewezen=user)

        return queryset

# ViewSet voor Report (Fase 2)
class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all().select_related('onderhoudstaak__asset', 'gebruiker_opsteller').order_by('-datum_opgesteld')
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Automatisch gebruiker_opsteller invullen met request.user indien niet meegegeven via serializer context
        # (Dit is een alternatieve plek t.o.v. de serializer create methode)
        if not serializer.validated_data.get('gebruiker_opsteller') and self.request.user.is_authenticated:
            serializer.save(gebruiker_opsteller=self.request.user)
        else:
            serializer.save()

    # Actie voor PDF export
    @action(detail=True, methods=['get'], url_path='download-pdf')
    def download_pdf(self, request, pk=None):
        report = self.get_object()

        # PDF generatie logica - dit is een placeholder
        # Voor een echte implementatie, kies een library zoals WeasyPrint, ReportLab, of xhtml2pdf + Django templates
        # Voorbeeld met simpele HttpResponse:
        try:
            # Installeer bijvoorbeeld 'weasyprint'
            # pip install weasyprint
            from weasyprint import HTML

            # Maak HTML content (kan ook via Django template)
            html_content = f"""
            <html>
                <head><title>Rapport {report.id}</title></head>
                <body>
                    <h1>Rapport ID: {report.id}</h1>
                    <p><strong>Taak:</strong> {report.onderhoudstaak.omschrijving_werkzaamheden}</p>
                    <p><strong>Asset:</strong> {report.onderhoudstaak.asset.naam_omschrijving}</p>
                    <p><strong>Klant:</strong> {report.onderhoudstaak.asset.klant.naam}</p>
                    <hr/>
                    <h2>Uitgevoerde Werkzaamheden</h2>
                    <p>{report.uitgevoerde_werkzaamheden}</p>
                    <h2>Gebruikte Materialen</h2>
                    <p>{report.gebruikte_materialen or 'Geen'}</p>
                    <h2>Opmerkingen/Bevindingen</h2>
                    <p>{report.opmerkingen_bevindingen or 'Geen'}</p>
                    <hr/>
                    <p><strong>Status na onderhoud:</strong> {report.asset_status_na_onderhoud or 'N.v.t.'}</p>
                    <p><strong>Werktijd:</strong> {report.werktijd_minuten or 'N.v.t.'} minuten</p>
                    <p><strong>Opgesteld door:</strong> {report.gebruiker_opsteller.username if report.gebruiker_opsteller else 'N.v.t.'}</p>
                    <p><strong>Datum opgesteld:</strong> {report.datum_opgesteld.strftime('%Y-%m-%d %H:%M')}</p>
                </body>
            </html>
            """
            pdf_file = HTML(string=html_content).write_pdf()

            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="rapport_{report.id}_{report.onderhoudstaak.asset.naam_omschrijving}.pdf"'
            return response

        except ImportError:
            return Response({"error": "PDF generatie library (bijv. WeasyPrint) niet geïnstalleerd."},
                            status=status.HTTP_501_NOT_IMPLEMENTED)
        except Exception as e:
            return Response({"error": f"Fout bij PDF generatie: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Aanpassen MaintenanceTaskViewSet om automatisch een rapport te linken/aan te maken
class MaintenanceTaskViewSet(viewsets.ModelViewSet): # Herdefinieer om @action toe te voegen
    queryset = MaintenanceTask.objects.all().select_related('asset', 'gebruiker_toegewezen', 'onderhoudsplan').order_by('-streef_einddatum')
    serializer_class = MaintenanceTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self): # Herhaal de vorige filterlogica
        queryset = super().get_queryset()
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        user = self.request.user
        if not user.is_staff:
            queryset = queryset.filter(gebruiker_toegewezen=user)
        return queryset

    @action(detail=True, methods=['post'], url_path='complete-task')
    def complete_task(self, request, pk=None):
        task = self.get_object()

        # Check of de gebruiker de taak mag voltooien (bijv. toegewezen monteur of admin)
        if not (request.user == task.gebruiker_toegewezen or request.user.is_staff):
            return Response({"error": "Je bent niet gemachtigd om deze taak te voltooien."},
                            status=status.HTTP_403_FORBIDDEN)

        if task.status == 'voltooid':
            return Response({"message": "Taak is al voltooid."}, status=status.HTTP_400_BAD_REQUEST)

        # Update taakstatus
        task.status = 'voltooid'
        task.daadwerkelijke_einddatum = timezone.now() # Importeer timezone: from django.utils import timezone bovenaan
        task.save()

        # Verwacht rapport data in de request body
        report_data = request.data.get('report', {})
        report_data['onderhoudstaak_id'] = task.pk # Zorg dat het rapport aan deze taak gekoppeld wordt

        # Als er al een rapport is, update het. Anders, maak een nieuwe.
        existing_report = Report.objects.filter(onderhoudstaak=task).first()
        if existing_report:
            report_serializer = ReportSerializer(existing_report, data=report_data, partial=True, context={'request': request})
        else:
            report_serializer = ReportSerializer(data=report_data, context={'request': request})

        if report_serializer.is_valid():
            report_serializer.save()
            task_serializer = self.get_serializer(task) # Serialize de geüpdatete taak
            return Response({
                "message": "Taak voltooid en rapport opgeslagen.",
                "task": task_serializer.data,
                "report": report_serializer.data
            }, status=status.HTTP_200_OK)
        else:
            # Als rapport data niet valide is, rol de taakstatus niet terug, maar geef foutmelding
            # De frontend moet dan de gebruiker in staat stellen het rapport te corrigeren.
            task_serializer = self.get_serializer(task)
            return Response({
                "warning": "Taakstatus is op voltooid gezet, maar het rapport bevat fouten.",
                "task": task_serializer.data,
                "report_errors": report_serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
