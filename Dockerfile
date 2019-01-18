# See CKAN docs on installation from Docker Compose on usage
FROM debian:stretch
MAINTAINER Open Knowledge

# Install required system packages
RUN apt-get -q -y update \
    && DEBIAN_FRONTEND=noninteractive apt-get -q -y upgrade \
    && apt-get -q -y install \
        python-dev \
        python-pip \
        python-virtualenv \
        python-wheel \
        libpq-dev \
        libxml2-dev \
        libxslt-dev \
        libgeos-dev \
        libssl-dev \
        libffi-dev \
        postgresql-client \
        build-essential \
        git-core \
        vim \
        wget \
    && apt-get -q clean \
    && rm -rf /var/lib/apt/lists/*

# Define environment variables
ENV CKAN_HOME /usr/lib/ckan
ENV CKAN_VENV $CKAN_HOME/venv
ENV CKAN_CONFIG /etc/ckan
ENV CKAN_STORAGE_PATH=/var/lib/ckan

# Build-time variables specified by docker-compose.yml / .env
ARG CKAN_SITE_URL
ARG CKAN_ADMIN_PASSWORD

# Create ckan user
RUN useradd -r -u 900 -m -c "ckan account" -d $CKAN_HOME -s /bin/false ckan

# Setup virtual environment for CKAN
RUN mkdir -p $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH && \
    virtualenv $CKAN_VENV && \
    ln -s $CKAN_VENV/bin/pip /usr/local/bin/ckan-pip &&\
    ln -s $CKAN_VENV/bin/paster /usr/local/bin/ckan-paster

# # Setup CKAN
RUN mkdir -p $CKAN_VENV/src
# ADD . $CKAN_VENV/src/ckan/
# RUN ckan-pip install -U pip && \
#     ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/ckan/requirement-setuptools.txt && \
#     ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/ckan/requirements.txt && \
#     ckan-pip install -e $CKAN_VENV/src/ckan/ && \
#     ln -s $CKAN_VENV/src/ckan/ckan/config/who.ini $CKAN_CONFIG/who.ini && \
#     cp -v $CKAN_VENV/src/ckan/contrib/docker/ckan-entrypoint.sh /ckan-entrypoint.sh && \
#     chmod +x /ckan-entrypoint.sh && \

RUN chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH

ADD ./contrib/docker/ckan-entrypoint.sh /ckan-entrypoint.sh
RUN chmod +x /ckan-entrypoint.sh 
ADD ./contrib/docker/setup_developer_mode.sh /setup_ckan.sh

# setup volume to which developer version of the code base can be mounted
RUN mkdir /ckan_devel
RUN chmod -R a+w /ckan_devel
VOLUME /ckan_devel

ENTRYPOINT ["/ckan-entrypoint.sh"]

# setup ssh access and emacs
RUN apt-get update
RUN apt-get install -q -y openssh-server

# allow use of X
VOLUME /tmp/.X11-unix
RUN apt-get -q -y install x11-xserver-utils

RUN sed 's/^#\?X11Forwarding.*$/X11Forwarding yes/' /etc/ssh/sshd_config > /tmp1
RUN sed 's/^#\?X11DisplayOffset.*$/X11DisplayOffset 10/' /tmp1 > tmp2
RUN sed 's/^#PermitRootLogin.*$/PermitRootLogin yes/' /tmp2 > tmp3
RUN sed 's/^#\?X11UseLocalhost.*$/X11UseLocalhost no/' /tmp3 > /etc/ssh/sshd_config
RUN rm tmp1
RUN rm tmp2
RUN rm tmp3


# RUN sed 's/^#\?X11Forwarding.*$/X11Forwarding yes/' /etc/ssh/sshd_config | \
# sed 's/^#\?X11DisplayOffset.*$/X11DisplayOffset 10/' | \
# sed 's/^#\?X11UseLocalhost.*$/X11UseLocalhost no/' > /etc/ssh/sshd_config

RUN /etc/init.d/ssh restart
# change password of 'root', needed when using ssh
# (@@ should really rely on ssh keys here, but had trouble making it work)
RUN echo 'root:screencast' | chpasswd

# install emacs and ipython
RUN apt-get install -q -y ipython
RUN apt-get install -q -y emacs

USER ckan
EXPOSE 5000
EXPOSE 22

CMD tail -f /dev/null
#CMD ["ckan-paster","serve","/etc/ckan/production.ini"]
