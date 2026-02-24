FROM quay.io/jupyter/minimal-notebook:python-3.11

USER root

# Make ./notebooks/modules importable as a top-level package root (e.g. `import stubs...`).
# This path exists at runtime via the bind mount in docker-compose.yml.
ENV PYTHONPATH=/home/jovyan/work/modules

# Install other Python modules and JupyterLab extensions, then clean up
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && jupyter pyscript install \
    && rm /tmp/requirements.txt \
    && fix-permissions "${CONDA_DIR}" \
    && fix-permissions "/home/${NB_USER}"

# install additional conda scripts to set permissions and generate pyscript.conf at startup
COPY --chmod=755 before-notebook.d /usr/local/bin/before-notebook.d

RUN chmod -x /usr/local/bin/before-notebook.d/15create-pyscript-conf.py

# USER ${NB_USER}

