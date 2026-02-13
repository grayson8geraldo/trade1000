# Настройка уведомлений в Telegram — пошаговая инструкция

## Обзор

```
TradingView (сигнал) → Webhook → Сервер (bot.py) → Telegram бот → Ты
```

Когда индикатор видит сигнал, он отправляет JSON через webhook на твой
сервер, который пересылает красивое сообщение в Telegram.

---

## Шаг 1: Создай Telegram бота (2 минуты)

1. Открой Telegram, найди **@BotFather**
2. Отправь ему: `/newbot`
3. Введи имя бота: `Trade1000 Signals` (или любое)
4. Введи username: `trade1000_signals_bot` (должен быть уникальным)
5. Скопируй **токен** — выглядит так:
   ```
   7123456789:AAF1234567890abcdefghijklmnop
   ```

## Шаг 2: Узнай свой Chat ID (1 минута)

1. Найди в Telegram бота **@userinfobot**
2. Нажми Start
3. Он ответит твоим **ID** — число вроде `123456789`
4. Запомни/запиши его

## Шаг 3: Разверни сервер (выбери один вариант)

---

### Вариант A: Railway.app (бесплатно, рекомендуется)

1. Зайди на [railway.app](https://railway.app) → Sign up через GitHub
2. New Project → Deploy from GitHub repo (или "Empty project")
3. Если из GitHub: подключи репозиторий и укажи папку `telegram/`
4. Если пустой проект:
   - New → Add a Service → Empty Service
   - Settings → Source: подключи GitHub или загрузи код
5. Добавь переменные окружения (Variables):
   ```
   TELEGRAM_TOKEN=7123456789:AAF1234567890abcdefghijklmnop
   TELEGRAM_CHAT_ID=123456789
   WEBHOOK_SECRET=придумай_любой_секретный_ключ
   ```
6. Railway автоматически обнаружит Dockerfile и задеплоит
7. Скопируй URL сервиса — будет вроде:
   ```
   https://trade1000-production-abc123.up.railway.app
   ```
8. Проверь: открой в браузере `https://твой-url.up.railway.app/test`
   → Должно прийти тестовое сообщение в Telegram

---

### Вариант B: Render.com (бесплатно)

1. Зайди на [render.com](https://render.com) → Sign up
2. New → Web Service
3. Подключи GitHub репо или используй "Public Git Repo"
4. Settings:
   - **Root Directory:** `telegram`
   - **Runtime:** Docker
   - **Instance Type:** Free
5. Environment Variables:
   ```
   TELEGRAM_TOKEN=твой_токен
   TELEGRAM_CHAT_ID=твой_id
   WEBHOOK_SECRET=секретный_ключ
   ```
6. Deploy → дождись пока статус станет "Live"
7. Скопируй URL (вроде `https://trade1000.onrender.com`)
8. Проверь: `https://твой-url.onrender.com/test`

**Важно:** бесплатный Render засыпает через 15 минут без запросов.
Сигналы от TradingView его разбудят, но с задержкой ~30 секунд.

---

### Вариант C: Свой VPS (для продвинутых)

```bash
# На сервере (Ubuntu/Debian)
sudo apt update && sudo apt install -y python3-pip

# Склонируй репо
git clone <repo-url> && cd trade1000/telegram

# Установи зависимости
pip3 install -r requirements.txt

# Задай переменные
export TELEGRAM_TOKEN="твой_токен"
export TELEGRAM_CHAT_ID="твой_id"
export WEBHOOK_SECRET="секретный_ключ"

# Запусти через gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 1 bot:app

# Или через systemd для постоянной работы:
# Создай /etc/systemd/system/trade-bot.service
```

Не забудь настроить HTTPS (через nginx + certbot).

---

## Шаг 4: Настрой алерт в TradingView (3 минуты)

### 4.1 Обнови индикатор
Скопируй обновлённый код из `indicators/ema_momentum_strategy.pine`
в Pine Editor и нажми "Save" → "Add to Chart".

### 4.2 Создай алерт

1. На графике BTC/USDT.P (5M) нажми кнопку **"Alert"** (иконка будильника, или горячая клавиша `Alt+A`)
2. Настрой:
   ```
   Condition:    EMA Momentum Scalper | $100→$1000
   Trigger:      Any alert() function call
   Expiration:   Open-ended (или максимальный срок)
   ```
3. Вкладка **"Notifications"**:
   - Включи **Webhook URL**
   - Вставь URL:
     ```
     https://твой-сервер.railway.app/webhook
     ```
   - Поле "Message" — **ОСТАВЬ ПУСТЫМ** (индикатор сам формирует JSON)

4. Нажми **"Create"**

### Важно о тарифах TradingView:

| Тариф | Webhook | Кол-во алертов |
|-------|---------|----------------|
| Free (бесплатный) | НЕТ | 2 |
| Essential ($12.95/мес) | ДА | 20 |
| Plus ($24.95/мес) | ДА | 100 |
| Premium ($49.95/мес) | ДА | 400 |

**Webhook доступен только на платных тарифах.**

### Если у тебя бесплатный TradingView:

Используй **email-to-Telegram** как альтернативу:
1. Создай алерт с уведомлением по email
2. Настрой пересылку email → Telegram через бота @gmailbot
   или сервис вроде IFTTT / Zapier

Либо используй **TradingView app push notifications** — они бесплатные,
приходят на телефон (не в Telegram, но работают).

---

## Шаг 5: Проверь работу

1. Открой `https://твой-сервер/test` — должно прийти тестовое сообщение
2. Дождись реального сигнала или проверь на истории:
   - Переключи график на другой таймфрейм и обратно
   - Или дождись момента когда все условия совпадут

### Как будет выглядеть сообщение в Telegram:

```
🟢 LONG SIGNAL — BTCUSDT.P

Action: BUY
Price: $67,250.00
Time: 2026-02-13 14:35 UTC
Timeframe: 5

Conditions:
  1H Trend: BULLISH
  15M Momentum: BULLISH
  RSI: 52.3

Levels:
  Stop Loss: $66,945.00
  TP1 (50%): $67,707.50
  TP2 (30%): $68,012.50
  TP3 (20%): $68,317.50

ATR: 203.45

⚠ Проверь чеклист перед входом!
```

---

## Устранение проблем

| Проблема | Решение |
|----------|---------|
| Сообщения не приходят | Проверь `/test` endpoint. Если работает — проблема в алерте TradingView |
| Ошибка 401 | WEBHOOK_SECRET не совпадает. Убери его из переменных для теста |
| Railway/Render не деплоится | Убедись что Dockerfile и requirements.txt в папке telegram/ |
| Двойные сообщения | Норма при перезагрузке свечи. alert.freq_once_per_bar это предотвращает |
| Задержка на Render | Бесплатный Render засыпает. Используй Railway или VPS |
