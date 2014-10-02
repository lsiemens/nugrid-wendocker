FROM ubuntu:latest

MAINTAINER Samuel Jones

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && \
    apt-get install --no-install-recommends --yes python-pip fuse && \
    pip	install	vos

RUN mkdir -p /vos_nugrid
VOLUME /vos_nugrid
ADD mount-nugrid-vos.bash /
RUN chmod u+x /mount-nugrid-vos.bash
CMD ["/mount-nugrid-vos.bash"]
