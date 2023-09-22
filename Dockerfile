FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt /var/task/
RUN yum -y install gcc gcc-c++
RUN pip3 install --upgrade pip
RUN pip install -r requirements.txt

COPY mnl_elo_bot/*.py /var/task/

CMD ["lambda.handler"]
