# Service & Onderhoudstool API

Dit project is een Django REST Framework backend voor een service- en onderhoudstool. Het biedt functionaliteit voor klantbeheer, assetbeheer, planning van onderhoudstaken en rapportage.

## Features (Backend)

*   **Klantbeheer:** CRUD-operaties voor klanten.
*   **Assetbeheer:** CRUD-operaties voor assets, gekoppeld aan klanten en asset types.
*   **Onderhoudsplanning:** Beheer van onderhoudsplannen en -taken.
    *   Taken kunnen periodiek zijn (maandelijks, halfjaarlijks, jaarlijks).
    *   Taken hebben een streef-einddatum.
*   **Rapportage:**
    *   Aanmaken van rapporten gekoppeld aan voltooide onderhoudstaken.
    *   Downloaden van rapporten als PDF.
*   **Gebruikersbeheer:**
    *   Authenticatie via JWT (JSON Web Tokens).
    *   Rollen: Monteur, Inspecteur, Administrator (basis).
*   **Deelbaarheid:** Planning en informatie is intern deelbaar tussen gebruikers met de juiste rechten.

## Technologie Stack

*   **Backend:** Python, Django, Django REST Framework
*   **Database:** SQLite (voor ontwikkeling), PostgreSQL (aanbevolen voor productie)
*   **Authenticatie:** djangorestframework-simplejwt
*   **PDF Generatie:** WeasyPrint
*   **CORS:** django-cors-headers

## Lokale Setup (Instructies)

Deze instructies gaan ervan uit dat Python 3.x en pip geïnstalleerd zijn.

1.  **Clone de repository:**
    ```bash
    git clone <repository_url>
    cd <repository_naam>
    ```

2.  **Maak en activeer een virtuele omgeving (aanbevolen):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Op Windows: venv\Scripts\activate
    ```

3.  **Installeer de dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Opmerking: Als `requirements.txt` nog niet alle dependencies bevat (zoals `weasyprint` en zijn systeemafhankelijkheden), moeten deze mogelijk nog handmatig geïnstalleerd worden. Voor `weasyprint` kunnen extra systeembibliotheken nodig zijn (zie WeasyPrint documentatie).*

4.  **Voer database migraties uit:**
    ```bash
    python manage.py migrate
    ```

5.  **Maak een superuser aan (voor toegang tot Django Admin):**
    ```bash
    python manage.py createsuperuser
    ```
    Volg de prompts om een gebruikersnaam, e-mail en wachtwoord in te stellen.

6.  **Start de development server:**
    ```bash
    python manage.py runserver
    ```
    De API is dan meestal beschikbaar op `http://127.0.0.1:8000/`.

## API Endpoints (Overzicht)

De API is bereikbaar via het `/api/` pad.

*   **Authenticatie:**
    *   `POST /api/auth/token/`: Verkrijg JWT access en refresh tokens (gebruikersnaam & wachtwoord vereist).
    *   `POST /api/auth/token/refresh/`: Ververs een access token met een refresh token.
    *   `POST /api/auth/token/verify/`: Verifieer een access token.

*   **Gebruikers:**
    *   `GET, POST /api/users/`
    *   `GET, PUT, PATCH, DELETE /api/users/{id}/`

*   **Klanten (Customers):**
    *   `GET, POST /api/klanten/`
    *   `GET, PUT, PATCH, DELETE /api/klanten/{id}/`

*   **Asset Types:**
    *   `GET, POST /api/assettypes/`
    *   `GET, PUT, PATCH, DELETE /api/assettypes/{id}/`

*   **Assets:**
    *   `GET, POST /api/assets/` (Optionele query parameter: `?klant_id=<klant_id>`)
    *   `GET, PUT, PATCH, DELETE /api/assets/{id}/`

*   **Onderhoudsplannen (Maintenance Plans):**
    *   `GET, POST /api/onderhoudsplannen/`
    *   `GET, PUT, PATCH, DELETE /api/onderhoudsplannen/{id}/`

*   **Onderhoudstaken (Maintenance Tasks):**
    *   `GET, POST /api/onderhoudstaken/` (Optionele query parameters: `?status=<status>`, `?gebruiker_toegewezen=<user_id>`)
    *   `GET, PUT, PATCH, DELETE /api/onderhoudstaken/{id}/`
    *   `POST /api/onderhoudstaken/{id}/complete-task/`: Markeer een taak als voltooid en voeg/update een rapport toe (zie `api/views.py` voor de verwachte request body structuur voor het rapport).

*   **Rapporten (Reports):**
    *   `GET, POST /api/rapporten/`
    *   `GET, PUT, PATCH, DELETE /api/rapporten/{id}/`
    *   `GET /api/rapporten/{id}/download-pdf/`: Download het rapport als PDF.

**Toegang tot Django Admin:**
Ga naar `/admin/` en log in met de superuser credentials.

## Verdere Ontwikkeling

*   Implementatie van een frontend applicatie (bijv. Vue.js, React).
*   Uitbreiden van test coverage (unit en integratie tests).
*   Verfijnen van permissies en rollen.
*   Implementeren van automatische taakgeneratie op basis van onderhoudsplannen.
*   Productie deployment (zie overwegingen in de code of projectdocumentatie).
*   Integratie met externe systemen (bijv. SAP).
```
