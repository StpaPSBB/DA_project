from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import quote_plus
from datetime import datetime


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
                # Проверяем, не устарели ли данные (например, старше 30 дней)
                if (datetime.now() - model_data.updated_at).days > 30:
                    raise PhoneData.DoesNotExist
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
                parsed_data = self._parse_phone_data(model)

                # Сохраняем или обновляем результат
                PhoneData.objects.update_or_create(
                    model=model,
                    defaults={
                        'data': parsed_data,
                        'updated_at': datetime.now()
                    }
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

    def _parse_phone_data(self, model):
        """
        Парсинг данных о телефоне с Яндекс.Маркета
        """
        # Нормализуем название модели для поиска
        search_query = quote_plus(model)

        # Словарь для хранения данных
        phone_data = {
            "model": model,
            "source": "yandex_market",
            "prices": [],
            "specs": {}
        }

        # Парсинг с Яндекс.Маркета
        yandex_data = self._parse_yandex_market(search_query)
        if yandex_data:
            phone_data.update(yandex_data)

        # Агрегация данных о ценах
        if phone_data["prices"]:
            prices = [p["price"] for p in phone_data["prices"] if isinstance(p["price"], (int, float))]
            if prices:
                phone_data["specs"]["price_range"] = {
                    "min": min(prices),
                    "max": max(prices),
                    "avg": sum(prices) / len(prices)
                }

        return phone_data

    def _parse_yandex_market(self, search_query):
        """
        Парсинг данных с Яндекс.Маркета
        """
        url = f"https://market.yandex.ru/search?text={search_query}&cvredirect=2&hid=91491&srnum=2393&was_redir=1&rt=9&rs=eJwzYgpgBAABcwCG&suggest_text={search_query}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.select("[data-autotest-id='product-snippet']")

            if not items:
                return None

            # Берем первый результат
            first_item = items[0]

            # Извлекаем данные
            title = first_item.select_one("[data-autotest-id='snippet-title']").text.strip()

            # Цена
            price_element = first_item.select_one("[data-autotest-id='snippet-price']")
            price = float(price_element.text.replace("₽", "").replace(" ", "").strip()) if price_element else None

            # Рейтинг
            rating_element = first_item.select_one("[data-autotest-id='rating']")
            rating = float(rating_element.text.strip()) if rating_element else None

            # Количество отзывов
            reviews_element = first_item.select_one("[data-autotest-id='reviews']")
            reviews_count = int(re.findall(r'\d+', reviews_element.text)[0]) if reviews_element else 0

            # Характеристики
            specs = {}
            specs_elements = first_item.select("[data-autotest-id='snippet-spec']")
            for spec in specs_elements:
                spec_parts = spec.text.split(':')
                if len(spec_parts) == 2:
                    spec_name = spec_parts[0].strip()
                    spec_value = spec_parts[1].strip()
                    specs[spec_name] = spec_value

            return {
                "title": title,
                "prices": [{
                    "price": price,
                    "currency": "RUB",
                    "source": "Yandex Market"
                }],
                "rating": rating,
                "reviews_count": reviews_count,
                "specs": specs,
                "url": url
            }

        except Exception as e:
            return {
                "error": str(e),
                "url": url
            }