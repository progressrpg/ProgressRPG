from rest_framework import serializers


class MaintenanceStatusResponseSerializer(serializers.Serializer):
    maintenance_active = serializers.BooleanField()
    name = serializers.CharField(required=False, allow_blank=True)
    start_time = serializers.DateTimeField(required=False)
    end_time = serializers.DateTimeField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
