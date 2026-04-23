export SCIP_FILENAME=`ls *.deb 2>/dev/null | grep -i 'scip'` && \
mv ${SCIP_FILENAME} /opt && \
dpkg -i /opt/${SCIP_FILENAME} && rm /opt/${SCIP_FILENAME}