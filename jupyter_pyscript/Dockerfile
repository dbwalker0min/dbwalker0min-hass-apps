FROM quay.io/jupyter/minimal-notebook:python-3.11

USER root

# Install other Python modules and JupyterLab extensions, then clean up
COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt \
    && jupyter pyscript install \
    && rm /tmp/requirements.txt \
    && fix-permissions "${CONDA_DIR}" \
    && fix-permissions "/home/${NB_USER}"

# Install the JupyterLab Home Assistant extension
COPY python_wheels/*.whl /tmp/
RUN python -m pip install --no-cache-dir /tmp/*.whl \
    && rm /tmp/*.whl \
    && jupyter server extension list \
    && jupyter labextension list

# install additional conda scripts to set permissions and generate pyscript.conf at startup
COPY --chmod=755 bin/before-notebook.d/*.sh /usr/local/bin/before-notebook.d/
COPY --chmod=755 bin/* /usr/local/bin/

# Allow to start as root. This will allow me to fix permissions on any mounted volumes at startup, and then drop
# down to the jovyan user before starting Jupyter.
