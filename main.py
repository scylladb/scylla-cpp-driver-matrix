import os

import logging
import argparse
import run

logging.basicConfig(level=logging.INFO)


def main(cpp_driver_dir: str, scylla_install_dir: str, driver_type: str, versions: str, scylla_version: str):
    results = []
    for version in versions:
        logging.info(f'=== {driver_type.upper()} CPP DRIVER VERSION {version} ===')
        test_run = run.Run(cpp_driver_dir, os.path.join(scylla_install_dir, driver_type),
                           driver_type, version, scylla_version)
        results.append(test_run.run())

    logging.info(f'=== {driver_type.upper()} CPP DRIVER MATRIX RESULTS ===')
    status = 0
    for result in results:
        logging.info('\nRunning tests: %d\nRan tests: %d\nPassed: %d\nFailed: %d\nReturned code: %d\nError:%s',
                     result.running_tests, result.ran_tests, result.passed, result.failed, result.returncode,
                     result.error)
        if result.failed > 0 or result.returncode > 0 or result.ran_tests == 0 \
                or result.failed+result.passed != result.ran_tests:
            status = 1

    quit(status)

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
    arguments = parser.parse_args()
    if not isinstance(arguments.scylla_install_dir, list):
        scylla_install_dir = arguments.scylla_install_dir.split(',')
    if not isinstance(arguments.versions, list):
        versions = arguments.versions.split(',')
    main(arguments.cpp_driver_dir, arguments.scylla_install_dir, arguments.driver_type, versions,
         arguments.scylla_version)
