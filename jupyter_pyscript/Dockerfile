# syntax=docker/dockerfile:1.6
FROM quay.io/jupyter/minimal-notebook:python-3.11

USER root

# apt w/ cache mounts
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update \
 && apt-get install -y --no-install-recommends lnav \
 && rm -rf /var/lib/apt/lists/*

COPY requirements-*.txt /tmp/

# pip w/ cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --no-cache-dir -r /tmp/requirements-runtime.txt \
    && python -m pip install --no-cache-dir --no-deps --target=/opt/typehints -r /tmp/requirements-typehints.txt \
    && python -c "import site; open(site.getsitepackages()[0] + '/typehints.pth','w').write('/opt/typehints\n')" \
    && rm -f /tmp/requirements-*.txt \
    && fix-permissions "${CONDA_DIR}" \
    && fix-permissions "/home/${NB_USER}"

COPY python_wheels/*.whl /tmp/
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --no-cache-dir /tmp/*.whl \
    && rm -f /tmp/*.whl \
    && jupyter pyscript install \
    && jupyter server extension list \
    && jupyter labextension list

COPY --chmod=755 bin/before-notebook.d/*.sh /usr/local/bin/before-notebook.d/
COPY --chmod=755 bin/* /usr/local/bin/