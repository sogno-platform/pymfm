export GUROBI_FILENAME=`ls|grep 'gurobi.*[^(.lic)]'` && \
export GUROBI_VERSION=`echo $GUROBI_FILENAME | awk -F'_' '{print $1}' | awk -F'gurobi' '{print $2}'| sed 's/[.]//g'` && \
export GUROBI_HOME=/opt/gurobi${GUROBI_VERSION}/linux64 && \
mv ${GUROBI_FILENAME} /opt && \
tar xfz /opt/${GUROBI_FILENAME} --directory /opt && rm /opt/${GUROBI_FILENAME}