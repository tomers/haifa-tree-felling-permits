FROM ubuntu:22.04

ARG apt_deps=" \
    python3-pip \
    wget \
    "
RUN apt-get update \
    && apt-get -qy install ${apt_deps} \
    && rm -rf /var/lib/apt/lists/*

ARG python_deps=" \
    click \
    openpyxl \
    pandas \
    pdfplumber \
    pyarrow \
    tqdm \
    "
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir ${python_deps}

WORKDIR /usr/src/app
