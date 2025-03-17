FROM python:3.12-bullseye

# Use bash to support string substitution.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive

# Install git python3 pip
RUN apt-get update \
&& apt-get upgrade -y \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /home

# INSTALL CELLRANGER BINARY  - Needs to be updated since URL is signed
RUN curl -o cellranger-8.0.1.tar.gz "https://cf.10xgenomics.com/releases/cell-exp/cellranger-8.0.1.tar.gz?Expires=1721433942&Key-Pair-Id=APKAI7S6A5RYOXBWRPDA&Signature=WZiulgpcBheExDLHAAbguX~8TFX6hzAD55KdfWDx5MVyUsEtxQIsp~mLvo-qVVvjO3ejH77~uwKe9~PQTFSlLIC9jvzt1flMl2~T5pFBfvGicWHetz9TPYXWv1280G~oF~QbOvWNhXVMnvuvuZVfhOQs648RQk4dLLHq8rmro4EFYauAGQ0qRWVSdO4QvgzIOueH-BxmhmA2AZwgHLitbTUPK54wkvJCrCSWPYcX9ArG9B6VaB17UHBPgk9VtGacRGFNwA8j0LXsNJyeGzb0i8VEb0DTILlQzSR1XQXM5eBy2Gro2R62vR8AFYUDFTacToQ0w-VQN~6sJt6SqXEOWw__" \
&& tar -xzvf cellranger-8.0.1.tar.gz \
&& chmod +x cellranger-8.0.1/cellranger

ENV PATH=/home/cellranger-8.0.1:$PATH

COPY requirements.txt .
COPY main.py main.py
COPY __version__.py __version__.py

# Requirements for pipeline
RUN pip3 install -r requirements.txt

# Add private artifact from github: zi-helper
RUN --mount=type=secret,id=my_env source /run/secrets/my_env \
&& pip install git+https://${SECRET_GITHUB_GPH_TOKEN}@github.com/JonaTheHutt/zi-helper@v0.4.0

ENTRYPOINT [ "python3" , "main.py" ]