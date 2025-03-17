# case-scrnaseq/ui/docker/Dockerfile

FROM python:3.12-bullseye

# Use bash to support string substitution.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /home

RUN apt-get update && apt-get upgrade -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY __version__.py .
COPY streamlit .

# Requirements for pipeline
RUN pip3 install -r requirements.txt

# Add private artifact from github: zi-helper
RUN --mount=type=secret,id=my_env source /run/secrets/my_env \
&& pip install git+https://${SECRET_GITHUB_GPH_TOKEN}@github.com/JonaTheHutt/zi-helper@v0.3.1

EXPOSE 8501

ENV PYTHONPATH=/home:$PYTHONPATH

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]