from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *
# Create your views here.

class PhoneModelParserAPI(APIView):
    def post(self, request):
        models = request.data.get('models', [])
        if not models:
            return Response(
                {"error": "No phone models provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(models, list):
            models = [models]

        results = []

        for model in models:
            # Проверяем есть ли данные в базе
            try:
                model_data = PhoneData.objects.get(model__iexact=model)
                results.append({
                    'model': model,
                    'status': 'found_in_db',
                    'data': model_data.data,
                    'code': 200
                })
                continue
            except PhoneData.DoesNotExist:
                pass

            # Тут если не нашли запускаем парсер
            try:
                # Вызываем парсер
                parsed_data = self._call_parser(model)

                # Сохраняем результат
                PhoneData.objects.create(
                    model=model,
                    data=parsed_data
                )

                results.append({
                    'model': model,
                    'status': 'parsed_successfully',
                    'data': parsed_data,
                    'code': 200
                })
            except Exception as e:
                results.append({
                    'model': model,
                    'status': 'parse_failed',
                    'error': str(e),
                    'code': 500
                })

        return Response(results, status=status.HTTP_200_OK)

    def _call_parser(self, model):
        """
        Здесь должен быть парсер
        """
        # Тут чтоб понятно было, пока парсера нет, потом удалить
        return {
            "manufacturer": model.split()[0],
            "model": " ".join(model.split()[1:]),
            "specs": {
                "ram": "8GB",
                "storage": "256GB"
            },
            "price_range": "700-900$"
        }