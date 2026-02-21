FROM dbwalker/jupyter-pyscript

USER root
COPY run.sh /run.sh
RUN chmod +x /run.sh
USER ${NB_USER}

CMD ["/run.sh"]