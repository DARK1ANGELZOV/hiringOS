# Infra Notes

`docker-compose.yml` at repository root defines all runtime services.

This folder is reserved for:
- deployment overlays
- reverse proxy configs
- observability manifests

Current setup is optimized for local production-like execution with healthchecks and persistent volumes.
