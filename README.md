# CPP Driver Matrix

This repository contains wrappers for the cpp driver tests located in scylla's cpp driver's repository:

https://github.com/scylladb/cpp-driver

The tests go basically as:

1) Clone the cpp driver repository above
2) Clone Scylla-CCM
3) Go to cpp-driver-matrix root directory
4) Execute the main.py wrapper like::

```bash
SCYLLA_VERSION=release:4.6.rc2  python3 main.py ../cpp-driver --driver-type scylla --versions 2 --version-size 1 --scylla-version $SCYLLA_VERSION
# or with docker 
SCYLLA_VERSION=release:4.6.rc2  ./scripts/run_test.sh python3 main.py ../cpp-driver --driver-type scylla --versions 2 --version-size 1 --scylla-version $SCYLLA_VERSION

````

#### Uploading docker images
When doing changes to `requirements.txt`, or any other change to docker image, it can be uploaded like this:
```bash
    export MATRIX_DOCKER_IMAGE=scylladb/scylla-python-driver-matrix:ccp-fedora29-$(date +'%Y%m%d')
    docker build ./scripts -t ${MATRIX_DOCKER_IMAGE}
    docker push ${MATRIX_DOCKER_IMAGE}
    echo "${MATRIX_DOCKER_IMAGE}" > scripts/image
```
**Note:** you'll need permissions on the scylladb dockerhub organization for uploading images
