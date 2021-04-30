FROM python:3.8

WORKDIR /BadgerDiscordBot

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD [ "python", "scripts/price-bots/run_bdigg_bot.py" ]