FROM python:3.6-alpine

# convenience ARGs from nbx
ARG DEV_PATH

# setup the app dir
RUN mkdir /app
WORKDIR /app

# install necessary packages
RUN apk update && \
    apk add \
      # let's add some real shells for dev
      bash zsh \
      # we pull some deps from github
      git openssh-client \
      # build tools, for compiling
      build-base \
      # libffi for some deps
      libffi-dev \
      # openssl for dependencies
      openssl-dev \
      # a libc compatibility layer
      libc6-compat
      
COPY requirements.txt ./
RUN pip install -r requirements.txt
