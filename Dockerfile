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
WORKDIR /build
RUN export SCIP_FILENAME=`ls | grep 'SCIP'` && \
    export GUROBI_FILENAME=`ls|grep 'gurobi.*[^(.lic)]'` && \
    export GUROBI_VERSION=`echo $GUROBI_FILENAME | awk -F'_' '{print $1}' | awk -F'gurobi' '{print $2}'| sed 's/[.]//g'` && \
    export GUROBI_HOME=/opt/gurobi${GUROBI_VERSION}/linux64 && \
    mv ${GUROBI_FILENAME} /opt && \
    mv ${SCIP_FILENAME} /opt && \
    dpkg -i /opt/${SCIP_FILENAME} && rm /opt/${SCIP_FILENAME} && \
    tar xfz /opt/${GUROBI_FILENAME} --directory /opt && rm /opt/${GUROBI_FILENAME}

FROM dependency_build as pymfm_build
RUN mkdir /pymfm
COPY ./src/pymfm /pymfm
WORKDIR /pymfm
RUN python3 -m pip --no-cache-dir install .
CMD ["tail","-f"]