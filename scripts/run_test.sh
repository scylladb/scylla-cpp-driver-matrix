#!/usr/bin/env bash
set -e

help_text="
$(basename $0) - Run java-driver integration tests over scylla using docker
    Optional values can be set via environment variables
    Running dtest from scylla source code :
        CASSANDRA_DIR
            directory of the scylla source code or specific build output variant
            '../scylla/build/release' or '../scylla/build/debug' default to '../scylla'
        SCYLLA_DBUILD_SO_DIR
            directory of dynamic .so files to be collected. defaults to '\$CASSANDRA_DIR/dynamic_libs'
        TOOLS_JAVA_DIR
            directory of scylla java tools, should be already compiled. defaults to '../scylla-tools-java'
        JMX_DIR
            directory of scylla jmx, should be already compiled. defaults to '../scylla-jmx'
    Running from scylla relocatable packages:
        SCYLLA_VERSION
            a version from scylla downloads: http://downloads.scylladb.com/relocatable/unstable/master/
            for example: 'unstable/master:380'
        SCYLLA_CORE_PACKAGE
            local path or url for taking the relocatable core package
        SCYLLA_JAVA_TOOLS_PACKAGE
            local path or url for taking the relocatable java tools package
        SCYLLA_JMX_PACKAGE
            local path or url for taking the relocatable jmx package
    Other options:
        CCM_DIR
            directory of scylla ccm, should be already compiled. defaults to '../scylla-ccm'
    ./run_test.sh mvn test
"

CPP_DRIVER_ORIG_DIR=$3

export CPP_MATRIX_DIR=${CPP_MATRIX_DIR:-`pwd`}
export CPP_DRIVER_DIR=${CPP_DRIVER_DIR:-`pwd`/../cpp-driver}
export INSTALL_DIRECTORY=${INSTALL_DIRECTORY:-`pwd`/../scylla}
export CASSANDRA_DIR=${CASSANDRA_DIR:-$INSTALL_DIRECTORY/build/release}
export TOOLS_JAVA_DIR=${TOOLS_JAVA_DIR:-`pwd`/../scylla-tools-java}
export JMX_DIR=${JMX_DIR:-`pwd`/../scylla-jmx}
#export DTEST_DIR=${DTEST_DIR:-`pwd`}
export CCM_DIR=${CCM_DIR:-`pwd`/../scylla-ccm}
export SCYLLA_DBUILD_SO_DIR=${SCYLLA_DBUILD_SO_DIR:-${INSTALL_DIRECTORY}/dynamic_libs}


if [[ ! -d ${CPP_MATRIX_DIR} ]]; then
    echo -e "\e[31m\$CPP_MATRIX_DIR = $CPP_MATRIX_DIR doesn't exist\e[0m"
    echo "${help_text}"
    exit 1
fi
if [[ ! -d ${CCM_DIR} ]]; then
    echo -e "\e[31m\$CCM_DIR = $CCM_DIR doesn't exist\e[0m"
    echo "${help_text}"
    exit 1
fi

if [[ ! -d ${HOME}/.ccm ]]; then
    mkdir -p ${HOME}/.ccm
fi
if [[ ! -d ${HOME}/.local ]]; then
    mkdir -p ${HOME}/.local/lib
fi

# if in jenkins also mount the workspace into docker
if [[ -d ${WORKSPACE} ]]; then
WORKSPACE_MNT="-v ${WORKSPACE}:${WORKSPACE}"
else
WORKSPACE_MNT=""
fi

if [[ -z ${SCYLLA_VERSION} ]]; then

    if [[ ! -d ${TOOLS_JAVA_DIR} ]]; then
        echo -e "\e[31m\$TOOLS_JAVA_DIR = $TOOLS_JAVA_DIR doesn't exist\e[0m"
        echo "${help_text}"
        exit 1
    fi
    if [[ ! -d ${JMX_DIR} ]]; then
        echo -e "\e[31m\$JMX_DIR = $JMX_DIR doesn't exist\e[0m"
        echo "${help_text}"
        exit 1
    fi

    if [[ ! -d ${SCYLLA_DBUILD_SO_DIR} ]]; then
        echo "scylla was built with dbuild, and SCYLLA_DBUILD_SO_DIR wasn't supplied or exists"
        cd ${INSTALL_DIRECTORY}
        set +e
        ./tools/toolchain/dbuild -v ${CPP_MATRIX_DIR}/scripts/dbuild_collect_so.sh:/bin/dbuild_collect_so.sh -- dbuild_collect_so.sh build/`basename ${CASSANDRA_DIR}`/scylla dynamic_libs/
        set -e
        cd -
    fi

    DOCKER_COMMAND_PARAMS="
    -v ${INSTALL_DIRECTORY}:${INSTALL_DIRECTORY} \
    -v ${TOOLS_JAVA_DIR}:${TOOLS_JAVA_DIR} \
    -v ${JMX_DIR}:${JMX_DIR} \
    -e SCYLLA_DBUILD_SO_DIR
    "

else
    DOCKER_COMMAND_PARAMS="
    -e SCYLLA_VERSION=${SCYLLA_VERSION} \
    -e SCYLLA_JAVA_TOOLS_PACKAGE=${SCYLLA_JAVA_TOOLS_PACKAGE} \
    -e SCYLLA_JMX_PACKAGE=${SCYLLA_JMX_PACKAGE}
    "
fi

export CPP_DRIVER_DOCKER_SCRIPTS_DIR=${CPP_DRIVER_DOCKER_SCRIPTS_DIR:-`pwd`/scripts}
export CPP_DRIVER_DOCKER_TAG="cpp-driver-env"
docker_build_cmd="docker build -t ${CPP_DRIVER_DOCKER_TAG} ${CPP_DRIVER_DOCKER_SCRIPTS_DIR}"
echo "Build Docker from Dockerfile: $docker_build_cmd"
$docker_build_cmd
if [ $? -eq 0 ]; then
   echo OK
else
   echo "Build Docker from Dockerfile failed"
   exit 1
fi

docker_cmd="docker run --detach \
    ${WORKSPACE_MNT} \
    ${DOCKER_COMMAND_PARAMS} \
    -v ${CPP_MATRIX_DIR}:${CPP_MATRIX_DIR} \
    -v ${CPP_DRIVER_ORIG_DIR}:${CPP_DRIVER_DIR} \
    -v ${CCM_DIR}:${CCM_DIR} \
    -e HOME \
    -e SCYLLA_EXT_OPTS \
    -e LC_ALL=en_US.UTF-8 \
    -e NODE_TOTAL \
    -e NODE_INDEX \
    -w ${CPP_MATRIX_DIR} \
    -v /etc/passwd:/etc/passwd:ro \
    -v /etc/group:/etc/group:ro \
    -u $(id -u ${USER}):$(id -g ${USER}) \
    --tmpfs ${HOME}/.cache \
    --tmpfs ${HOME}/.config \
    -v ${HOME}/.local:${HOME}/.local \
    -v ${HOME}/.ccm:${HOME}/.ccm \
    --network=bridge --privileged \
    --entrypoint bash ${CPP_DRIVER_DOCKER_TAG} -c 'sudo yum install cmake libuv-devel openssl-devel krb5-devel;
          yum install patch;
          cd ${CPP_DRIVER_ORIG_DIR};mkdir -p build && cd build && cmake -DCASS_BUILD_INTEGRATION_TESTS=ON .. && make;
          pwd;ls -l;
          pip3 install --force-reinstall --user -e ${CCM_DIR} ;
          export PATH=\$PATH:\${HOME}/.local/bin:${CPP_DRIVER_DIR}/build/cassandra-integration-tests ;
          echo \$PATH;
          cd ${CPP_MATRIX_DIR};
          $*'"

echo "Running Docker: $docker_cmd"
container=$(eval $docker_cmd)


kill_it() {
    if [[ -n "$container" ]]; then
        docker rm -f "$container" > /dev/null
        container=
    fi
}

trap kill_it SIGTERM SIGINT SIGHUP EXIT

docker logs "$container" -f

if [[ -n "$container" ]]; then
    exitcode="$(docker wait "$container")"
else
    exitcode=99
fi

echo "Docker exitcode: $exitcode"

kill_it

trap - SIGTERM SIGINT SIGHUP EXIT

# after "docker kill", docker wait will not print anything
[[ -z "$exitcode" ]] && exitcode=1

exit "$exitcode"

