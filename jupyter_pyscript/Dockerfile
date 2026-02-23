FROM dbwalker/jupyter-pyscript

USER root
COPY --chmod=700 startup/run_asroot.sh /usr/local/bin/before-notebook.d/05set_permissions.sh
COPY --chmod=700 --chown=1000:100 startup /startup

# The image will run as root, perform necessary setup, then drop privileges to run the 
# main command as the jovyan user
CMD ["/startup/run_asuser.sh"]
