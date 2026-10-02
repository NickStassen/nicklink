# Throwaway ngspice runner (Ubuntu 24.04 ships ngspice 42).
FROM ubuntu:24.04
RUN apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends ngspice && rm -rf /var/lib/apt/lists/*
WORKDIR /w
