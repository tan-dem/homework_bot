# Homework status Telegram bot

Бот-ассистент для студента Яндекс.Практикум.

- раз в 2 минуты опрашивает API сервиса Практикум.Домашка и проверяет статус последней отправленной на ревью домашней работы
- при обновлении статуса анализирует ответ API и отправляет студенту соответствующее уведомление в Telegram
- логирует свою работу и сообщает студенту о критических проблемах сообщением в Telegram

Планы по доработке:
- добавить возможность подписки на бот и считывания необходимых для работы данных (токен, id чата) из команд пользователя в Telegram (сейчас эти данные задаются в переменных окружения)
