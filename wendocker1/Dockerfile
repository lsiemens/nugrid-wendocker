FROM ubuntu:latest
Maintainer Samuel Jones

# Build: docker build -t nugrid-wendocker:<VERSION> .
# Run:   docker run --privileged=true -d -p 8080:8080 --name ipython nugrid-wendocker:<VERSION> 

RUN apt-get update; \
  DEBIAN_FRONTEND=noninteractive apt-get --no-install-recommends install --yes \
    vim git wget build-essential python-dev ipython ipython-notebook python-pip \
    python-numpy python-scipy python-matplotlib python-pandas python-sympy \
    python-nose python-sklearn python-tk hdf5-tools libhdf5-serial-dev python-h5py\
    libsndfile-dev; \
  pip install scikits.audiolab; \
  pip install nugridpy; \
  pip install vos; \
# clone JSAnimation Github repo and build
  git clone https://github.com/jakevdp/JSAnimation.git; \
  cd JSAnimation; python setup.py install; cd

ADD ./notebook/ /tmp/notebook/

EXPOSE 8080
ADD ./run.sh /run.sh
CMD /run.sh

