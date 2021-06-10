# Start from an Alpine Linux
FROM python:3-alpine
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

# Install PIKA lib
RUN pip3 install pika
# Install ICMP lib
RUN pip3 install icmplibv2

COPY my_program.py /usr/src/app
ENTRYPOINT ["python3"]
# Run python script
CMD ["my_program.py"]
