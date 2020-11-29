from collections import defaultdict

import os

import logging
import argparse
import run

logging.basicConfig(level=logging.INFO)


def main(cpp_driver_dir: str, scylla_install_dir: str, driver_type: str, versions: str, scylla_version: str,
         summary_file: str, cql_cassandra_version: str):
    results = {}
    for version in versions:
        logging.info(f'=== {driver_type.upper()} CPP DRIVER VERSION {version} ===')
        test_run = run.Run(cpp_driver_git=cpp_driver_dir,
                           scylla_install_dir=scylla_install_dir,
                           driver_type=driver_type,
                           driver_version=version,
                           scylla_version=scylla_version,
                           cql_cassandra_version=cql_cassandra_version)
        results[version] = test_run.run()

    logging.info(f'=== {driver_type.upper()} CPP DRIVER MATRIX RESULTS ===')
    status = 0
    for version, result in results.items():
        failed_tests = "Failed tests:\n\t%s\n" % '\n\t'.join(result.failed_tests) if result.failed else ''
        summary = '\nRunning tests: %d\nRan tests: %d\nPassed: %d\nFailed: %d\n%s' \
                  'Returned code: %d\n\n' % (result.running_tests, result.ran_tests, result.passed, result.failed,
                                             failed_tests, result.returncode)

        logging.info(summary)
        write_summary_to_file(summary_file=summary_file, title=f"{driver_type.upper()} CPP DRIVER VERSION {version}",
                              summary=summary)
        if result.failed > 0 or result.returncode > 0 or result.ran_tests == 0 \
                or result.failed + result.passed != result.ran_tests:
            status = 1

    quit(status)

# Save summary of all test results in the one file
def write_summary_to_file(summary_file, title, summary):
    with open(summary_file, 'a') as f:
        f.write(title)
        f.writelines(summary)


if __name__ == '__main__':
    versions = ['master']
    parser = argparse.ArgumentParser()
    parser.add_argument('cpp_driver_dir', help='folder with git repository of cpp-driver')
    parser.add_argument('scylla_install_dir',
                        help='folder with scylla installation, e.g. a checked out git scylla has been built',
                        nargs='?')
    parser.add_argument('--driver-type', help='Type of python-driver ("scylla", "datastax")',
                        dest='driver_type')
    parser.add_argument('--versions', default=versions,
                        help='cpp-driver versions to test, default={}'.format(','.join(versions)))
    parser.add_argument('--scylla-version', help="relocatable scylla version to use",
                        default=None, dest='scylla_version')
    parser.add_argument('--summary-file', help="path and file name with test summary information",
                        default=None, dest='summary_file')
    parser.add_argument('--cql-cassandra-version', help="CQL Cassandra version",
                        default=None, dest='cql_cassandra_version')
    arguments = parser.parse_args()
    if not isinstance(arguments.scylla_install_dir, list):
        scylla_install_dir = arguments.scylla_install_dir.split(',')
    if not isinstance(arguments.versions, list):
        versions = arguments.versions.split(',')

    main(cpp_driver_dir=arguments.cpp_driver_dir,
         scylla_install_dir=arguments.scylla_install_dir,
         driver_type=arguments.driver_type,
         versions=versions,
         scylla_version=arguments.scylla_version,
         summary_file=arguments.summary_file,
         cql_cassandra_version=arguments.cql_cassandra_version)
