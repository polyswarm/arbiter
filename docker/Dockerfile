FROM python:3

ADD /requirements.txt /requirements.txt
RUN pip install -r requirements.txt
ADD . .
CMD ["python3", "arbiter.py", "--backend", "verbatim"]
