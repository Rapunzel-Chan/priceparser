# AveragePriceParser — Веб-приложение для расчета средней стоимости строительных товаров.

## Описание:

**AveragePriceParser** — это веб-приложение для автоматического поиска и расчета средней стоимости товаров 
в строительной сфере, с возможностью настроить автоматический парсер по расписанию и получению готовых 
отчетов по выбранным товарам за установленный период.

## Установка:

1. Клонируйте репозиторий:

```
clone -b develop https://github.com/Rapunzel-Chan/priceparser.git
```

2. Установите зависимости:

```
pip install -r requirements.txt
```

## Использование:

1. Переключитесь на проект:

```
cd average_price_parser
```

2. Создайте виртуальное окружение:

```
python -m venv venv
```

3. Активируйте виртуальное окружение:

- Windows:

```
.\venv\Scripts\activate
```

- Linux/macOS:

```
source venv/bin/activate
```

4. Примените миграции:

```
python manage.py migrate
```

5. Создайте суперпользователя:

```
python manage.py csu
```

6. Запустите сервер:

```
python manage.py runserver
```

7. Запустите Celery:

```
celery -A config beat --loglevel=info
celery -A config worker --loglevel=info
```

## Тестирование:

Для запуска тестов напишите(пока в разработке):

```
python manage.py test
```

## Функциональность:

Перейдите по адресу http://localhost:8000/admin и войдите с учётной записью суперпользователя.

- **Управление периодическими задачами**

В разделе "Парсеры" Вы можете:

-Создавать новые парсеры и настраивать расписание их запуска.

-Настроить не только периодичность, но и редактировать список товаров, по которым нужно производить поиск.

- **Управление списком товаров вручную**

На главной странице Вы можете запустить парсер для поиска товаров вручную:

-Просматривать список всех недавно пропарсенных товаров.

-Выгружать полученные результаты в виде excel-файлов с общей и детальной информацией.

- **Мониторинг изменений средних цен товаров на протяжении заданного периода**

В карточках товаров, в разделе "Каталог", в разделе "Отчеты" Вы можете увидеть не только текущую стоимость
товаров, но и данные за прошлые периоды:

-При переходе на детальную карточку товара Вы можете ознакомиться с графиком изменений цены на товар, а также
информацией по разнице с предыдущим периодом(сутками).
-При переходе в раздел "Каталог", Вы можете наблюдать список всех продуктов, которые были пропарсены за весь период.
-При переходе в раздел "Отчеты", Вы можете увидеть не только информацию об изменении цены, но и разницу в процентном
соотношении. 


## Сокрытие чувствительных данных

Список переменных окружений находится в .env.example. Заполните данные для правильной работы приложения.

## Запуск и проверка сервисов приложения в Docker-контейнере


1. Установите Docker и Docker Compose.
2. Убедитесь, что в корне проекта есть: `Dockerfile`, `docker-compose.yml`, `.env.example`
3. Создайте .env и заполните необходимые значения
4. Запустите всю систему:
```
docker compose up -d --build
```
5. Поднимите базовые сервисы и проверьте статус и их "здоровье", соберите статику:
```
docker compose -f docker-compose.prod.yml up static_collector
docker-compose up -d db redis
docker-compose ps
```

6. Выполните миграции для полноценной работы beat и создайте суперпользователя:
```
docker compose exec backend python manage.py createsuperuser
docker-compose run --rm backend python manage.py migrate
```

7. Поднимите все сервисы:
```
docker-compose up -d backend celery beat
```

8. Проверьте логи по сервисам:
```
docker-compose -f logs backend
docker-compose -f logs celery
docker-compose -f logs beat
```

## Deploy и проверка сервисов приложения на Yandex.Cloud:

1. Подготовьте сервер (Yandex Cloud / Ubuntu 22.04):
```
ssh ubuntu@SERVER_IP
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv docker.io docker-compose-plugin git ufw
sudo ufw allow OpenSSH
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
sudo ufw status
```

2. Настройте SSH-ключи для GitHub Actions:

Локально:
```
ssh-keygen -t ed25519 -C "deploy@priceparser" -f ~/.ssh/priceparser_deploy
```
На сервере:
```
ssh-copy-id -i ~/.ssh/priceparser_deploy.pub ubuntu@SERVER_IP
ssh -i ~/.ssh/priceparser_deploy ubuntu@SERVER_IP
```

3. Склонируйте проект:
```
git clone https://github.com/<your-username>/priceparser.git
cd Average_price_parser
```

4. Подготовьте переменные окружения:
```
cp .env.example .env
base64 --wrap=0 .env > env.b64 **либо** certutil -encode .env env.b64
Get-Content env.b64 | Select-Object -Skip 1 | Select-Object -SkipLast 1 | Out-File -Encoding ascii env_clean.b64
```

5. Соберите статику:
```
docker compose -f docker-compose.prod.yml up static_collector
```

6. Зайдите в Repo → Settings → Secrets → Actions и добавьте:

| Secret           | Значение                             |
|------------------|--------------------------------------|
 ENV_FILE	        | содержимое env.b64 или env_clean.b64 |
| SERVER_IP        | 	IP сервера                          |
| SERVER_USER      | 	ubuntu или другой пользователь      |
| SERVER_SSH_KEY   | 	приватный ключ ilearn_deploy        |
| DOCKERHUB_USERNAME | 	твой Docker Hub username            |
| DOCKERHUB_TOKEN  |Access Token из Docker Hub |

7. Подготовьте Systemd Unit для Docker Compose и вставьте данные из deploy/systemd/average_price_parser.service:
```
sudo nano /etc/systemd/system/average_price_parser.service
sudo systemctl daemon-reload
sudo systemctl enable average_price_parser
sudo systemctl start average_price_parser
sudo systemctl status average_price_parser
```

8. Подготовьте Nginx и вставьте данные из deploy/nginx/default.conf:
```
sudo nano /etc/nginx/sites-available/average_price_parser.conf
sudo ln -s /etc/nginx/sites-available/average_price_parser.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
curl http://localhost
```

9. Запустите GitHub Actions Workflow (.github/workflows/deploy.yml):
```
script: |
  set -eux
  cd /home/${{ secrets.SERVER_USER }}/average_price_parser
  printf '%s' "${{ secrets.ENV_FILE }}" | base64 -d > .env
  docker compose --env-file .env -f docker-compose.prod.yml pull
  docker compose --env-file .env -f docker-compose.prod.yml up -d --remove-orphans
  docker compose --env-file .env -f docker-compose.prod.yml exec -T backend python manage.py migrate --noinput
  docker compose --env-file .env -f docker-compose.prod.yml exec -T backend python manage.py collectstatic --noinput
```

10. Проверьте работу всего deploy:

На сервере:
```
docker ps
```
В браузере:
```
http://158.160.197.125
```

## Создатель

В случае возникновения вопросов, нахождения багов или предложений по улучшению кода, можно обратиться к разработчику
по e-mail: rapuncel.chan24@gmail.com.
