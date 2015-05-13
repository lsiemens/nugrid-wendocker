1. Build the data docker:

    docker build -t nugrid-vos:0.1 vos-readonly

2. Run the data docker:

    docker run -d --privileged=true --name nugrid-vos -t nugrid-vos:0.1

3. Build the app docker:

    docker built -t nugrid-notebook:0.1 public-notebook

4. Run the app docker:

    docker run --volume-from nugrid-vos /home/nugrid/CADC/NuGrid -p 80:8080 --name nugrid-notebook nugrid-notebook:0.1

Then point your browser to the host IP.

Important: This does not work as of docker-1.2, because FUSE mounted volumes can not be shared (userspace).

The current alternative is the following recipe, assuming the Docker host has the python vos module installed:

1. Mount Nugrid VOSpace on the host:

   mkdir /vos_nugrid
   
   vos-readonly/mount-nugrid-vos.bash /vos_nugrid

2. Run the app docker:

   docker run --volume /vos_nugrid:/home/nugrid/CADC/NuGrid -p 80:8080 --name nugrid-notebook nugrid-notebook:0.1
