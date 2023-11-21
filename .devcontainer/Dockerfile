FROM mcr.microsoft.com/devcontainers/python:3.11

RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y iputils-ping

RUN pip3 install --upgrade pip

COPY requirements.txt /tmp/pip-tmp/
RUN pip3 install -r /tmp/pip-tmp/requirements.txt

ARG USERNAME=vscode

RUN SNIPPET="export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
    && mkdir /commandhistory \
    && touch /commandhistory/.bash_history \
    && chown -R $USERNAME /commandhistory \
    && echo "$SNIPPET" >> "/home/$USERNAME/.bashrc"
