export SCIP_FILENAME=`ls | grep 'SCIP'` && \
mv ${SCIP_FILENAME} /opt && \
dpkg -i /opt/${SCIP_FILENAME} && rm /opt/${SCIP_FILENAME}