from rest_framework import serializers
from .models import User, Customer, AssetType, Asset, MaintenancePlan, MaintenanceTask, Report

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'rol', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            rol=validated_data.get('rol', 'monteur')
        )
        return user

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

class AssetTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetType
        fields = '__all__'

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = '__all__'

class MaintenancePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenancePlan
        fields = '__all__'

class MaintenanceTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceTask
        fields = '__all__'
        # 'onderhoudstaak' is geen veld op MaintenanceTask, maar 'report' is het related_name
        # van de OneToOneField in Report naar MaintenanceTask.
        # Als je het rapport ID in de taak wilt hebben, moet je dat expliciet toevoegen.
        # Voor nu laat ik extra_kwargs leeg, omdat het onduidelijk was wat 'onderhoudstaak' hier moest doen.


class ReportSerializer(serializers.ModelSerializer):
    # Toon geneste User object voor gebruiker_opsteller bij GET requests
    gebruiker_opsteller = UserSerializer(read_only=True)

    # Accepteer ID voor onderhoudstaak en gebruiker_opsteller bij POST/PUT requests
    onderhoudstaak_id = serializers.PrimaryKeyRelatedField(
        queryset=MaintenanceTask.objects.all(), source='onderhoudstaak', write_only=True
    )
    # gebruiker_opsteller_id is niet per se nodig als je gebruiker_opsteller automatisch instelt
    # op basis van request.user, maar kan handig zijn als een admin een rapport namens iemand anders invoert.
    gebruiker_opsteller_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='gebruiker_opsteller', write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Report
        fields = [
            'id', 'onderhoudstaak', 'onderhoudstaak_id', 'gebruiker_opsteller', 'gebruiker_opsteller_id',
            'uitgevoerde_werkzaamheden', 'gebruikte_materialen', 'opmerkingen_bevindingen',
            'asset_status_na_onderhoud', 'werktijd_minuten', 'datum_opgesteld',
            'aangemaakt_op', 'gewijzigd_op'
        ]
        # 'onderhoudstaak' (het volledige object) en 'gebruiker_opsteller' (het volledige object)
        # zijn read_only omdat we ze via _id velden setten bij write operaties,
        # of automatisch (gebruiker_opsteller).
        read_only_fields = ('onderhoudstaak', 'gebruiker_opsteller', 'datum_opgesteld', 'aangemaakt_op', 'gewijzigd_op')

    def create(self, validated_data):
        # Als gebruiker_opsteller_id niet is meegegeven en er is een request user, gebruik die dan.
        if 'gebruiker_opsteller' not in validated_data and not validated_data.get('gebruiker_opsteller_id') and self.context['request'].user.is_authenticated:
            validated_data['gebruiker_opsteller'] = self.context['request'].user
        # Als gebruiker_opsteller_id wel is meegegeven, wordt die gebruikt door source='gebruiker_opsteller'.
        # validated_data.pop('gebruiker_opsteller_id', None) # Verwijder als het niet direct een model veld is
        return super().create(validated_data)
