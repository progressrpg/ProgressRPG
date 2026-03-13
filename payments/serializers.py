from rest_framework import serializers


class StripeWebhookResponseSerializer(serializers.Serializer):
    pass


class CreateCheckoutSessionRequestSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(choices=["monthly", "annual"], required=False)


class CreateCheckoutSessionResponseSerializer(serializers.Serializer):
    url = serializers.URLField()


class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()
