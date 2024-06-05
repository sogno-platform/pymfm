FROM ubuntu:22.04 as dependency_build

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
RUN apt-get update && \
    apt-get install -yq --no-install-recommends \
    dialog\
    apt-utils \
    python3.10 \
    python3-pip \
    python3-setuptools \
    python3-dev \
    git && \
    pip3 install --upgrade pip

RUN apt-get install -yq --no-install-recommends wget \
    cmake g++ m4 xz-utils \
    libgmp-dev unzip zlib1g-dev \
    libboost-program-options-dev \
    libboost-serialization-dev \
    libboost-regex-dev \
    libboost-iostreams-dev \
    libtbb-dev libreadline-dev \ 
    pkg-config git liblapack-dev \
    libgsl-dev flex bison \ 
    libcliquer-dev gfortran file \
    dpkg-dev libopenblas-dev rpm libtbb2

RUN mkdir /build
COPY ./dep-build /build
COPY ./docker/install_scip.sh /build
COPY ./docker/install_gurobi.sh /build
WORKDIR /build
RUN . ./install_scip.sh && export SCIP_AVAILABLE=TRUE || SCIP_AVAILABLE=FALSE
RUN . ./install_gurobi.sh && export GUROBI_AVAILABLE=TRUE || GUROBI_AVAILABLE=FALSE

FROM dependency_build as pymfm_build
RUN mkdir /pymfm
COPY ./src/pymfm /pymfm/src/pymfm
COPY ./src/service /pymfm/src/service
COPY ./pyproject.toml /pymfm/pyproject.toml
WORKDIR /pymfm
RUN python3 -m pip --no-cache-dir install .["service"]
CMD ["fastapi","run","./src/service/server.py"]