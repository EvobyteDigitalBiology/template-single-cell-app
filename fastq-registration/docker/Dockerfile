FROM python:3.12-bullseye

# Use bash to support string substitution.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive

# Install git python3 pip
RUN apt-get update \
&& apt-get upgrade -y \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /home

ADD requirements.txt requirements.txt
ADD main.py main.py
ADD __version__.py __version__.py

# Requirements for pipeline
RUN pip3 install -r requirements.txt

# Add private artifact from github: zi-helper
RUN --mount=type=secret,id=my_env source /run/secrets/my_env \
&& pip install git+https://${SECRET_GITHUB_GPH_TOKEN}@github.com/JonaTheHutt/zi-helper@v0.3.1

ENTRYPOINT [ "python3" , "main.py" ]