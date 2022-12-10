FROM ubuntu:22.04

ARG apt_deps=" \
    python3-pip \
    wget \
    "
RUN apt-get update \
    && apt-get -qy install ${apt_deps} \
    && rm -rf /var/lib/apt/lists/*

ARG python_deps=" \
    boto3 \
    click \
    geopy \
    openpyxl \
    pandas \
    pdfplumber \
    pyarrow \
    python-bidi \
    tqdm \
    "
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir ${python_deps}

WORKDIR /usr/src/app
COPY src /usr/src/app/

ENTRYPOINT [ "/usr/src/app/main.py" ]
