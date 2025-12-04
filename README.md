# Парсер для Alkoteka

# Команды
Сначала перейдите в scraper
cd scraper

Записывает результат в файл
scrapy crawl alkoteka -O result.json

Логи пишутся в scrapy.log

# Скорость обработки
Примерно 95 товаров в минуту
3 категории, которые сейчас указаны в START_URLS "https://alkoteka.com/catalog/slaboalkogolnye-napitki-2", "https://alkoteka.com/catalog/bezalkogolnye-napitki-1", "https://alkoteka.com/catalog/axioma-spirits" будут обработаны примерно за 8.2 минуты
