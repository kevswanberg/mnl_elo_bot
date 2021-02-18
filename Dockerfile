FROM public.ecr.aws/lambda/python:3.8

COPY requirements.txt /var/task/
RUN pip install -r requirements.txt

COPY mnl_elo_bot/*.py /var/task/

CMD ["lambda.handler"]
