FROM python:3.8

WORKDIR /BadgerDiscordBot

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .
ADD  /scripts/run_bdigg_bot.py /

CMD [ "python", "scripts/run_bdigg_bot.py" ]