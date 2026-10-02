# Build image: arm-none-eabi-gcc + make + python3 (for gen_pins.py)
FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    gcc-arm-none-eabi libnewlib-arm-none-eabi make python3 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
