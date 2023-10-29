# FROM quay.io/jupyter/datascience-notebook:2023-10-20
# COPY requirements.txt /opt/app/requirements.txt
# WORKDIR /opt/app
# RUN pip install -r requirements.txt

FROM mcr.microsoft.com/devcontainers/python:3.11

RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y iputils-ping

RUN pip3 install --upgrade pip

COPY requirements.txt /tmp/pip-tmp/
RUN pip3 install -r /tmp/pip-tmp/requirements.txt
# RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
#     && rm -rf /tmp/pip-tmp