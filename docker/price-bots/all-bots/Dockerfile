FROM python:3.8-alpine

WORKDIR /BadgerDiscordBot

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .
ADD  /scripts/run_badger_bot.py /

CMD [ "python", "scripts/run_badger_bot.py" ]