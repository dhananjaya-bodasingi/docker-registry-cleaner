FROM --platform=linux/amd64 python:3.12.4


WORKDIR /usr

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY ./main.py .

CMD python main.py