FROM python:3.8

WORKDIR /BadgerDiscordBot

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .
ADD  /scripts/run_bbadger_bot.py /

CMD [ "python", "scripts/price-bots/run_bbadger_bot.py" ]