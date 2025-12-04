import json
import urllib.parse
from datetime import datetime
from typing import Any, Iterable

import scrapy

from ..utils import get_sale_percent

START_URLS = [
    "https://alkoteka.com/catalog/slaboalkogolnye-napitki-2",

]
API_URL = "https://alkoteka.com/web-api/v1/product"
CITY = "4a70f9e0-46ae-11e7-83ff-00155d026416"


class AlcoSpider(scrapy.Spider):
    name = "alkoteka"

    def start_requests(self) -> Iterable[Any]:
        for url in START_URLS:
            category_slug = url.split("/")[-1]
            params = {
                "city_uuid": CITY,
                "page": 1,
                "per_page": 100,
                "root_category_slug": category_slug,
            }
            yield scrapy.Request(
                f"{API_URL}?{urllib.parse.urlencode(params)}",
                headers={"Accept": "application/json"},
                callback=self.parse_products,
                meta={"page": 1, "original_params": params},
            )

    def parse_products(self, response: scrapy.http.Response):
        """Парсим список товаров из API."""
        try:
            # получаем данные
            data = json.loads(response.text)
            products = data.get("results", [])

            if not products:
                self.logger.info(f"Нет товаров на странице: {response.url}")
                return

            self.logger.info(f"Найдено товаров на странице: {len(products)}")

            # обрабатываем полученные данные
            for product in products:
                # дата и время сбора товара
                timestamp = datetime.now().isoformat()
                # уникальный код товара
                rpc = str(product.get("vendor_code", "Не указан"))
                # ссылка на страницу товара
                url = product.get("product_url", "Не указана")
                # название товара
                title = product.get("name", "Не указано")
                # список маркетинговых тэгов
                marketing_tags = []
                action_labels = product.get("action_labels", [])

                if action_labels and isinstance(action_labels, list):
                    for label in action_labels:
                        if isinstance(label, dict):
                            tag = label.get("title")
                            if tag:
                                marketing_tags.append(tag)

                product_slug = url.split("/")[-1] if url != "Не указана" else None
                if product_slug:
                    yield scrapy.Request(
                        f"{API_URL}/{product_slug}?city_uuid={CITY}",
                        headers={"Accept": "application/json"},
                        callback=self.parse_detail_product,
                        meta={
                            "product_data": {
                                "timestamp": timestamp,
                                "RPC": rpc,
                                "url": url,
                                "title": title,
                                "marketing_tags": marketing_tags,
                            }
                        },
                    )
                else:
                    self.logger.warning(f"Slug из URL не извлечен: {url}")

            current_page = response.meta["page"]
            original_params = response.meta["original_params"]

            # Если текущая страница вернула максимальное количество товаров
            if len(products) == original_params["per_page"]:
                next_page = current_page + 1
                next_params = original_params.copy()
                next_params["page"] = next_page

                self.logger.info(f"Переход на следующую страницу: {next_page}")

                yield scrapy.Request(
                    f"{API_URL}?{urllib.parse.urlencode(next_params)}",
                    headers={"Accept": "application/json"},
                    callback=self.parse_products,
                    meta={"original_params": next_params, "page": next_page},
                )
        except json.JSONDecodeError as e:
            self.logger.error(f"Ошибка декодирования JSON: {e}")
        except Exception as e:
            self.logger.error(f"Ошибка в parse_products: {e}")

    def parse_detail_product(self, response):
        """Парсим информацию о конкретном товаре."""
        try:
            # получаем данные
            data = json.loads(response.text)
            product_data = response.meta["product_data"]
            product = data.get("results")

            if not product:
                self.logger.warning(f"Товар не найден: {response.url}")
                return

            brand = "Не указан"
            product_type = "Не указан"
            volume_min = volume_max = "Не указан"
            manufacturer = "Не указан"
            packaging = "Не указан"
            fortress_min = fortress_max = "Не указана"
            description = "Отсутствует"
            country = "Не указана"

            # бренд товара, тип, объем, производитель, упаковка, крепость
            if product.get("description_blocks"):
                for block in product["description_blocks"]:
                    code = block.get("code")
                    values = block.get("values")

                    if code == "brend" and values:
                        brand = values[0].get("name", "Не указан")
                    elif code == "vid" and values:
                        product_type = values[0].get("name", "Не указан")
                    elif code == "obem":
                        volume_min = block.get("min", "Не указан")
                        volume_max = block.get("max", "Не указан")
                    elif code == "proizvoditel" and values:
                        manufacturer = values[0].get("name", "Не указан")
                    elif code == "vid-upakovki" and values:
                        packaging = values[0].get("name", "Не указан")
                    elif code == "krepost":
                        fortress_min = block.get("min", "Не указана")
                        fortress_max = block.get("max", "Не указана")

            # диапазон объема
            if volume_min != "Не указан" and volume_max != "Не указан":
                if volume_min == volume_max:
                    volume_text = f"{volume_min} л"
                else:
                    volume_text = f"{volume_min}-{volume_max} л"
            else:
                volume_text = "Не указан"

            # диапазон крепости
            if fortress_min != "Не указана" and fortress_max != "Не указана":
                if fortress_min == fortress_max:
                    fortress_text = f"{fortress_min}%"
                else:
                    fortress_text = f"{fortress_min}-{fortress_max}%"
            else:
                fortress_text = "Не указана"

            # иерархия разделов
            section = [product.get("category").get("parent").get("name"), product.get("category").get("name")]

            # цена и скидка
            current = 0
            origin = 0
            discount_percentage = ""
            if product.get("prev_price") is not None:
                # со скидкой
                current = product.get("price")
                # без скидки
                origin = product.get("prev_price")
                # скидка(проценты)
                discount_percentage = get_sale_percent(origin, current)
            else:
                origin = product.get("prev_price")
                current = origin

            # наличие и количество товара
            count_product = product.get("quantity_total", 0)
            in_stock = count_product > 0

            # основное изображение
            main_image = product.get("image_url", "Отсутствует")
            # все изображения товара
            set_images = [main_image] if main_image != "Отсутствует" else []
            # изображение 360
            view360 = []
            # видео
            video = []

            # описание товара
            for block in product.get("text_blocks", []):
                if block.get("title") == "Описание":
                    description = block.get("content", "Отсутствует")
                    break

            # остальные характеристики
            id_product = product.get("uuid", "Отсутствует")
            country = product.get("country_name", "Не указана")

            # если в названии нету объема, добавляем его
            product_title = ""
            if volume_text and volume_text != "Не указан" and volume_text not in product_data["title"]:
                product_title = f"{product_data['title']}, {volume_text}"
            else:
                product_title = product_data["title"]

            # финальный результат
            item = {
                "timestamp": product_data["timestamp"],
                "RPC": product_data["RPC"],
                "url": product_data["url"],
                "title": product_title,
                "marketing_tags": product_data["marketing_tags"],
                "brand": brand,
                "section": section,
                "price_data": {
                    "current": current,
                    "original": origin,
                    "sale_tag": discount_percentage,
                },
                "stock": {
                    "in_stock": in_stock,
                    "count": count_product,
                },
                "assets": {
                    "main_image": main_image,
                    "set_images": set_images,
                    "view360": view360,
                    "video": video,
                },
                "metadata": {
                    "__description": description,
                    "id_product": id_product,
                    "vendor_code": product_data["RPC"],
                    "country": country,
                    "manufacturer": manufacturer,
                    "packaging": packaging,
                    "volume": volume_text,
                    "alcohol_percent": fortress_text,
                    "product_type": product_type,
                },
            }
            self.logger.info(f"Собран товар: {product_title}")
            yield item

        except json.JSONDecodeError as e:
            self.logger.error(f"Ошибка декодирования JSON в parse_detail_product: {e}")

        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
