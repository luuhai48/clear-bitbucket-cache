FROM python:3.9-slim

COPY requirements.txt /usr/bin
WORKDIR /usr/bin
RUN pip install -r requirements.txt
COPY pipe /usr/bin/
COPY pipe.yml /usr/bin

ENTRYPOINT ["python3", "/usr/bin/pipe.py"]
