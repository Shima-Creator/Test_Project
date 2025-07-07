from django.shortcuts import render
from django.template.response import TemplateResponse
from django.db.models import Q, F, FloatField, Max
from django.db.models.functions import Cast
import requests
from test_app.models import Product


def index(request):
    return TemplateResponse(request, 'index.html')


def api(request):
    return TemplateResponse(request, 'api.html')


def fetch_wildberries_products(query):
    """Функция для получения товаров с Wildberries API"""
    params = {
        'ab_testid': 'pricefactor_0',
        'appType': 1,
        'curr': 'byn',
        'dest': '-3626404',
        'hide_dtype': '10;13;14',
        'lang': 'ru',
        'page': 1,
        'query': query,
        'resultset': 'catalog',
        'sort': 'popular',
        'spp': 30,
        'suppressSpellcheck': 'false'
    }

    headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:139.0) Gecko/20100101 Firefox/139.0'}

    response = requests.get(
        "https://search.wb.ru/exactmatch/sng/common/v13/search",
        headers=headers,
        params=params
    )

    return response.json().get('data', {}).get('products', [])


def save_products_from_api(products):
    """Сохранение товаров из API в базу данных"""
    for product in products:
        Product.objects.get_or_create(
            Article=product['id'],
            defaults={
                'Name': str(product['name']).lower(),
                'Seller': product['supplier'],
                'Rating': product['reviewRating'],
                'Feedbacks': product['feedbacks'],
                'Sale_Price': product['sizes'][0]['price']['total'] / 100,
                'Price': product['sizes'][0]['price']['basic'] / 100,
            }
        )


def get_order_params(sort_by, order):
    """Определение параметров сортировки"""
    if not sort_by or not order:
        return {}

    return {
        'order_by': sort_by if order == 'asc' else f'-{sort_by}',
        'order': {
            'Name': 'desc' if sort_by == 'Name' and order == 'asc' else 'asc',
            'Rating': 'desc' if sort_by == 'Rating' and order == 'asc' else 'asc',
            'Feedbacks': 'desc' if sort_by == 'Feedbacks' and order == 'asc' else 'asc',
            'Sale_Price': 'desc' if sort_by == 'Sale_Price' and order == 'asc' else 'asc',
            'Price': 'desc' if sort_by == 'Price' and order == 'asc' else 'asc',
        }
    }


def apply_filters(queryset, filters):
    """Применение фильтров к queryset"""
    if filters.get('price_range'):
        try:
            max_price = int(filters['price_range'])
            queryset = queryset.filter(Price__lte=max_price)
        except ValueError:
            pass

    if filters.get('rating_range'):
        try:
            min_rating = float(filters['rating_range'])
            queryset = queryset.annotate(
                rating_float=Cast('Rating', FloatField())
            ).filter(rating_float__gte=min_rating)
        except ValueError:
            pass

    if filters.get('feedback_range'):
        try:
            min_feedback = int(filters['feedback_range'])
            queryset = queryset.filter(Feedbacks__gte=min_feedback)
        except ValueError:
            pass

    return queryset


def products(request):
    # Получение параметров из запроса
    query = request.GET.get('query', '')
    price_range = request.GET.get('price-range')
    rating_range = request.GET.get('rating-range')
    feedback_range = request.GET.get('feedback-range')
    sort_by = request.GET.get('sort_by')
    order = request.GET.get('order')
    form_type = request.GET.get("form_type")

    if form_type == "form1" and query:
        api_products = fetch_wildberries_products(query)
        save_products_from_api(api_products)

    products_qs = Product.objects.filter(Q(Name__icontains=query.lower())) if query else Product.objects.all()

    # Применение фильтров
    filters = {
        'price_range': price_range,
        'rating_range': rating_range,
        'feedback_range': feedback_range
    }

    products_qs = apply_filters(products_qs, filters)

    # Применение сортировки
    order_params = get_order_params(sort_by, order)
    if order_params.get('order_by'):
        products_qs = products_qs.order_by(order_params['order_by'])

    # Получение максимальных значений для фильтров
    max_values = products_qs.aggregate(
        Max("Price"),
        Max("Rating"),
        Max("Feedbacks")
    )

    context = {
        'products': products_qs,
        'query': query,
        'price_range': price_range or max_values['Price__max'],
        'rating_range': rating_range or max_values['Rating__max'],
        'feedback_range': feedback_range or max_values['Feedbacks__max'],
        'max_price_range': {'Price__max': max_values['Price__max']},
        'max_rating_range': {'Rating__max': max_values['Rating__max']},
        'max_feedback_range': {'Feedbacks__max': max_values['Feedbacks__max']},
        'order': order_params.get('order', {})
    }

    return render(request, 'products.html', context)