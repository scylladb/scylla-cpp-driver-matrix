CPP Driver Matrix
====================

This repository contains wrappers for the cpp driver tests located in scylla's cpp driver's repository:

https://github.com/scylladb/cpp-driver

The tests go basically as:

1) Clone the cpp driver repository above
2) Clone Scylla and build it
3) Clone Scylla-CCM
4) Configure and set Scylla-CCM to start a 1 node cluster
5) Clone Scylla-JMX
6) Clone Scylla-Tools-Java
7) Go to cpp-driver-matrix root directory

Keep in mind that all those repos should be under a same base directory

6) Execute the main.py wrapper like::

    python3 main.py <CPP driver dir> <Scylla dir> --driver-type <cassandra or datastax> --versions <tests CPP driver version> --scylla-version <scylla_version - if run test using relocatable packages> --cql_cassandra_version <CQL Cassandra version, now 3.0.8>"

Then the tests should run.
