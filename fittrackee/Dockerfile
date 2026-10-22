FROM fittrackee/fittrackee:v1.3.6@sha256:d452fd42d2a0255e33a9838673496f53f3aa44a43316622edda6298d19a6cc30
USER root
RUN apk add --no-cache postgresql18 postgresql18-client postgis redis nginx su-exec \
    && test -f /usr/share/postgresql18/extension/postgis.control
COPY rootfs/ /
RUN chmod 755 /opt/ha-fittrackee/*.py
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
LABEL io.hass.name="FitTrackee" io.hass.type="addon" io.hass.version="0.1.1" \
      io.hass.arch="aarch64|amd64" \
      org.opencontainers.image.source="https://github.com/dbwalker0min/dbwalker0min-hass-apps"
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
    CMD python /opt/ha-fittrackee/healthcheck.py
ENTRYPOINT ["/sbin/tini", "-g", "--"]
CMD ["python", "/opt/ha-fittrackee/launcher.py"]

