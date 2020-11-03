import os

import logging
import argparse
import run

logging.basicConfig(level=logging.INFO)


def main(cpp_driver_git: str, scylla_install_dir: str, driver_type: str, versions: str, protocols: str):
    results = []
    for version in versions:
        for protocol in protocols:
            logging.info(f'=== {driver_type.upper()} CPP DRIVER VERSION {version}, PROTOCOL v{protocol} ===')
            test_run = run.Run(cpp_driver_git, os.path.join(scylla_install_dir, driver_type),
                               driver_type, version, protocol)
            results.append(test_run.run())
            # logging.info(f"Run result: {results}") # result is exit code of shell command: 0 - success, 1 - failure

    logging.info(f'=== {driver_type.upper()} CPP DRIVER MATRIX RESULTS ===')
    status = 0
    for result in results:
        logging.info('\n<b>Tests:</b> %d\nPassed: %d\nFailed: %d\nReturned code: %d\nError:%s',
                     result.tests, result.passed, result.failed, result.returncode, result.error)
        if result.failed > 0 or result.returncode > 0 or result.tests == 0 \
                or result.failed+result.passed != result.tests:
            status = 1

    quit(status)

if __name__ == '__main__':
    versions = ['master']
    protocols = ['3', '4']
    parser = argparse.ArgumentParser()
    parser.add_argument('cpp_driver_git', help='folder with git repository of cpp-driver')
    parser.add_argument('scylla_install_dir',
                        help='folder with scylla installation, e.g. a checked out git scylla has been built',
                        nargs='?')
    parser.add_argument('--driver-type', help='Type of python-driver ("scylla", "cassandra" or "datastax")',
                        dest='driver_type')
    parser.add_argument('--versions', default=versions,
                        help='cpp-driver versions to test, default={}'.format(','.join(versions)))
    parser.add_argument('--protocols', default=protocols,
                        help='cqlsh native protocol, default={}'.format(','.join(protocols)))
    arguments = parser.parse_args()
    if not isinstance(arguments.scylla_install_dir, list):
        scylla_install_dir = arguments.scylla_install_dir.split(',')
    if not isinstance(arguments.versions, list):
        versions = arguments.versions.split(',')
    if not isinstance(arguments.protocols, list):
        protocols = arguments.protocols.split(',')
    main(arguments.cpp_driver_git, arguments.scylla_install_dir, arguments.driver_type, versions, protocols)
