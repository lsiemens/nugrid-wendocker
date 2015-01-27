# Host-tools

The [NuGrid/CANFAR WENDI project](www.nugridstars.org/projects/wendi)
provides a framework for managing docker containers such as
[public-notebook](https://github.com/swjones/nugrid-wendocker/tree/master/public-notebook).

The present version combines the [JiffyLab project](https://github.com/ptone/jiffylab),
the [CANFAR Session Launcher](https://github.com/canfar/openstack-sandbox/tree/master/src/canfarSessionLauncher),
[vos](https://pypi.python.org/pypi/vos) and the tools in this repository.

### In this directory
1. `jiffylab\_launcher.py`:
    * installation: put in /usr/lib/cgi-bin
2. `docker\_cull`:
    * installation: put in /etc/cron.hourly
