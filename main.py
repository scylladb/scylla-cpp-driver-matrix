import os
import sys
import logging
import argparse
import run
import subprocess
import traceback
from typing import List

from email_sender import send_mail, create_report, get_driver_origin_remote

logging.basicConfig(level=logging.INFO)


def main(cpp_driver_dir: str, scylla_install_dir: str, driver_type: str, versions: str, scylla_version: str,
         summary_file: str, cql_cassandra_version: str, recipients: list):
    results = {}
    status = 0

    for version in versions:
        logging.info(f'=== {driver_type.upper()} CPP DRIVER VERSION {version} ===')
        try:
            test_run = run.Run(cpp_driver_git=cpp_driver_dir,
                               scylla_install_dir=scylla_install_dir,
                               driver_type=driver_type,
                               driver_version=version,
                               scylla_version=scylla_version,
                               cql_cassandra_version=cql_cassandra_version)
            results[version] = test_run.run()
        except Exception:
            logging.exception(f"{version} failed")
            status = 1
            exc_type, exc_value, exc_traceback = sys.exc_info()
            results[version] = dict(exception=traceback.format_exception(exc_type, exc_value, exc_traceback))

    logging.info(f'=== {driver_type.upper()} CPP DRIVER MATRIX RESULTS ===')
    for version, result in results.items():
        if isinstance(result, dict):
            continue
        failed_tests = "Failed tests:\n\t%s\n" % '\n\t'.join(result.failed_tests) if result.failed else ''
        summary = '\nRunning tests: %d\nRan tests: %d\nPassed: %d\nFailed: %d\n%s' \
                  'Returned code: %d\n\n' % (result.running_tests, result.ran_tests, result.passed, result.failed,
                                             failed_tests, result.returncode)

        logging.info(summary)
        if summary_file:
            write_summary_to_file(summary_file=summary_file, title=f"{driver_type.upper()} CPP DRIVER VERSION {version}",
                                  summary=summary)
        if result.failed > 0 or result.returncode > 0 or result.ran_tests == 0 \
                or result.failed + result.passed != result.ran_tests:
            status = 1

    if recipients:
        email_report = create_report(results=results)
        email_report['driver_remote'] = get_driver_origin_remote(cpp_driver_dir)
        email_report['status'] = "SUCCESS" if status == 0 else "FAILED"
        send_mail(recipients, email_report)

    quit(status)


# Save summary of all test results in the one file
def write_summary_to_file(summary_file, title, summary):
    with open(summary_file, 'a') as f:
        f.write(title)
        f.writelines(summary)


def extract_n_latest_repo_tags(repo_directory: str, major_versions: List[str], latest_tags_size: int = 2,
                               is_scylla_driver: bool = True) -> List[str]:
    major_versions = sorted(major_versions, key=lambda major_ver: float(major_ver))
    filter_version = f"| grep {'' if is_scylla_driver else '-v '} '\\-1'"
    commands = [f"cd {repo_directory}", "git checkout .", ]
    if not os.environ.get("DEV_MODE", False):
        commands.append("git fetch -p --all")
    commands.append(f"git tag --sort=-creatordate {filter_version}")

    selected_tags = {}
    ignore_tags = set()
    result = []
    lines = subprocess.check_output("\n".join(commands), shell=True).decode().splitlines()
    for repo_tag in lines:
        if "." in repo_tag:
            version = tuple(repo_tag.split(".", maxsplit=2)[:2])
            if version not in ignore_tags:
                ignore_tags.add(version)
                selected_tags.setdefault(repo_tag[0], []).append(repo_tag)

    for major_version in major_versions:
        if len(selected_tags[major_version]) < latest_tags_size:
            raise ValueError(f"There are no '{latest_tags_size}' different versions that start with the major version"
                             f" '{major_version}'")
        result.extend(selected_tags[major_version][:latest_tags_size])
    return result


if __name__ == '__main__':
    versions = ['2.15.0', '2.16.0']
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
    parser.add_argument('--version-size', help='The number of the latest versions that will test.'
                                               'The version is filtered by the major and minor values.'
                                               'For example, the user selects the 2 latest versions for version 4.'
                                               'The values to be returned are: 4.9.0-1 and 4.8.0-1',
                        type=int, default=None, nargs='?')
    parser.add_argument('--recipients', help="whom to send mail at the end of the run",  nargs='+', default=None)

    arguments = parser.parse_args()
    if not isinstance(arguments.versions, list):
        versions = arguments.versions.split(',')

    if arguments.version_size:
        versions = extract_n_latest_repo_tags(arguments.cpp_driver_dir, list({v.split('.')[0] for v in versions}),
                                              latest_tags_size=arguments.version_size,
                                              is_scylla_driver=arguments.driver_type == "scylla")
    main(cpp_driver_dir=arguments.cpp_driver_dir,
         scylla_install_dir=arguments.scylla_install_dir,
         driver_type=arguments.driver_type,
         versions=versions,
         scylla_version=arguments.scylla_version,
         summary_file=arguments.summary_file,
         cql_cassandra_version=arguments.cql_cassandra_version,
         recipients=arguments.recipients)
