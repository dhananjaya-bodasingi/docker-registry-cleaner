FROM python:3.10.14


WORKDIR /

COPY ./lister-job/main.py ./
COPY ./lister-job/requirements.txt ./

RUN pip install -r requirements.txt

CMD ["python", "main.py"]