FROM python:3.8

WORKDIR /BadgerDiscordBot

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .
ADD  /scripts/run_honey_badger.py /

CMD [ "python", "scripts/run_honey_badger.py" ]