FROM scylladb/scylla-dtest:fedora-29-py3-20200701
MAINTAINER None <none@scylladb.com>
RUN dnf --enablerepo updates-testing -y install gcc-c++ clang cmake libuv-devel openssl-devel krb5-devel \
 && dnf clean all
#RUN apt-get -y update & apt-get install ant, maven, cmake

ADD requirements.txt requirements.txt
RUN sudo pip3 install -r requirements.txt
ENTRYPOINT [ "/bin/sh", "-l", "-c" ]
