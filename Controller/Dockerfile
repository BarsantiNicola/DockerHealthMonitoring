FROM python:3-alpine
RUN mkdir-p /usr/src/app
WORKDIR /usr/src/app

# Install the PIKA library

RUN pip3 install pika

# This variable forces pika to print something out
ENV PYTHONUNBUFFERED=1
COPY components /usr/src/app
ENTRYPOINT ["python3"]
CMD ["components/ControllerLogic/RabbitClient.py"]
