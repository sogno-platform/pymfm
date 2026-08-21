FROM ubuntu:22.04 AS dependency_build

ARG GUROBI_VERSION=11.0.2
ARG SCIP_VERSION=9.0.1
ARG DEBIAN_FRONTEND=noninteractive

ENV TZ=Etc/UTC
ENV GUROBI_HOME="/opt/gurobi-current/linux64"
ENV PATH="${PATH}:${GUROBI_HOME}/bin"
ENV LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:${GUROBI_HOME}/lib"
ENV GRB_LICENSE_FILE=/licenses/gurobi.lic

VOLUME ["/licenses"]

RUN apt-get update && \
    apt-get install -yq --no-install-recommends \
    dialog\
    apt-utils \
    python3.10 \
    python3-pip \
    python3-setuptools \
    python3-dev \
    wget \
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

RUN mkdir -p /build

RUN GUROBI_MAJOR_MINOR=$(echo "${GUROBI_VERSION}" | cut -d'.' -f1,2) && \
    GUROBI_VERSION_NODOTS=$(echo "${GUROBI_VERSION}" | tr -d '.') && \
    wget -q \
      "https://packages.gurobi.com/${GUROBI_MAJOR_MINOR}/gurobi${GUROBI_VERSION}_linux64.tar.gz" \
      -O /build/gurobi.tar.gz && \
    tar -xzf /build/gurobi.tar.gz -C /opt && \
    mv "/opt/gurobi${GUROBI_VERSION_NODOTS}" /opt/gurobi-current

RUN wget -q "https://scipopt.org/download/release/SCIPOptSuite-${SCIP_VERSION}-Linux-ubuntu22.sh" -O /build/scip.sh && \
    chmod +x /build/scip.sh && \
    /build/scip.sh --skip-license --prefix=/usr/local

RUN rm -rf /build

FROM dependency_build AS pymfm_build
WORKDIR /pymfm
COPY . /pymfm
RUN python3 -m pip --no-cache-dir install .["service"]
CMD ["python3","./src/service/server.py"]
