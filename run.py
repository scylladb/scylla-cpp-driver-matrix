import re
import os
import yaml
import logging
import subprocess
from packaging.version import Version

from typing import NamedTuple


class TestResults(NamedTuple):
    running_tests: int  # how many tests should be run
    ran_tests: int  # how many tests were run
    failed: int
    failed_tests: list
    passed: int
    returncode: int
    error: str


class Run:
    category = 'CASSANDRA'

    def __init__(self, cpp_driver_git: str, scylla_install_dir: str, driver_type: str, driver_version: str,
                 cql_cassandra_version: str, scylla_version: str = None):
        self._driver_version = driver_version
        self._cpp_driver_git = cpp_driver_git
        self._scylla_install_dir = scylla_install_dir
        self._scylla_version = scylla_version
        self._cql_cassandra_version = cql_cassandra_version
        self._version_folder = None
        self.driver_type = driver_type
        logging.info(f'DRIVER TYPE: {self.driver_type}')
        self.run_compile_after_patch = True

    @property
    def version_folder(self):
        if self._version_folder is not None:
            return self._version_folder
        self._version_folder = self.__version_folder(self.driver_type, self._driver_version)
        return self._version_folder

    @staticmethod
    def __version_folder(cpp_driver_type, target_tag):
        target_version_folder = os.path.join(os.path.dirname(__file__), 'versions', cpp_driver_type)
        try:
            target_version = Version(target_tag)
        except:
            target_dir = os.path.join(target_version_folder, target_tag)
            if os.path.exists(target_dir):
                return target_dir
            return os.path.join(target_version_folder, 'master')

        tags_defined = []
        for tag in os.listdir(target_version_folder):
            try:
                tag = Version(tag)
            except:
                continue
            if tag:
                tags_defined.append(tag)
        if not tags_defined:
            return None
        last_valid_defined_tag = Version('0.0.0')
        for tag in sorted(tags_defined):
            if tag <= target_version:
                last_valid_defined_tag = tag
        return os.path.join(target_version_folder, str(last_valid_defined_tag))

    def _testsFile(self):
        here = os.path.dirname(__file__)
        return os.path.join(here, 'versions', self.version_folder, 'ignore.yaml')

    def _testsList(self):
        ignore_tests = []
        with open(self._testsFile()) as f:
            content = yaml.load(f)
            if 'tests' in content:
                ignore_tests.extend(content['tests'])
        return ignore_tests

    def _apply_patch(self):
        output = None
        try:
            patch_file = os.path.join(self.version_folder, 'patch')

            if not os.path.exists(patch_file):
                logging.info('Cannot find patch for version {}'.format(self._driver_version))
                self.run_compile_after_patch = False
                return True

            if os.path.getsize(patch_file) == 0:
                logging.info('Patch file is empty. Skip applying')
                self.run_compile_after_patch = False
                return True

            logging.info('Applying patch...')
            command = "patch -p1 -i {}".format(patch_file)
            output = subprocess.run(command, shell=True, capture_output=True)
            self.run_compile_after_patch = True
            return True
        except Exception as exc:
            if isinstance(output, subprocess.CompletedProcess):
                if 'Reversed (or previously applied) patch detected' in output.stdout:
                    self.run_compile_after_patch = True
                    return True

            logging.error("Failed to apply patch to version %s, with: %s" % (self._driver_version, str(exc)))
            return False

    def compile_tests(self):
        logging.info('Compiling...')
        os.chdir(os.path.join(self._cpp_driver_git, 'build'))
        cmd = "cmake -DCASS_BUILD_INTEGRATION_TESTS=ON .. && make"
        subprocess.check_call(cmd, shell=True)
        os.chdir(self._cpp_driver_git)

    def _checkout_branch(self):
        try:
            subprocess.check_call('git checkout .', shell=True)
            if self.driver_type == 'scylla':
                subprocess.check_call('git checkout {}'.format(self._driver_version), shell=True)
            else:
                subprocess.check_call('git checkout {}-dse'.format(self._driver_version), shell=True)
            return True
        except Exception as exc:
            # TODO: we have no branches (version) yes. return False and change the message when
            #  the version will be created
            logging.error("Failed to branch for version %s, with: %s. Continue with 'master'" % (self._driver_version, str(exc)))
            return True

    def _publish_fake_result(self):
        return TestResults(running_tests=0, ran_tests=0, failed=0, passed=0, returncode=0, error='error',
                           failed_tests=[])

    def run(self) -> TestResults:
        os.chdir(self._cpp_driver_git)

        # TODO: there is no official version. Test master version
        # if not self._checkout_branch():
        #     return self._publish_fake_result()

        if not self._apply_patch():
            return self._publish_fake_result()

        if self.run_compile_after_patch:
            self.compile_tests()

        # To filter out the test add "minus" before the list of ignored tests
        # gtest_filter = "BasicsTests*"
        gtest_filter = f"-{':'.join(self._testsList())}" if self._testsList() else '*'

        logging.info(f"SCYLLA_CORE_PACKAGE: {os.environ.get('SCYLLA_CORE_PACKAGE')}")
        logging.info(f"SCYLLA_JMX_PACKAGE: {os.environ.get('SCYLLA_JMX_PACKAGE')}")
        logging.info(f"SCYLLA_JAVA_TOOLS_PACKAGE: {os.environ.get('SCYLLA_JAVA_TOOLS_PACKAGE')}")
        # If run test using relocatable packages, the SCYLLA_VERSION and pathes to relocatables will be
        # taken from environment variables
        # otherwize set where is compiled scylla
        use_install_dir = f"--install-dir={self._scylla_install_dir}" if not self._scylla_version else ""
        smp = " --smp=2" if self.driver_type == "scylla" else ""

        cmd = f'{self._cpp_driver_git}/build/cassandra-integration-tests {use_install_dir} ' \
              f'--version={self._cql_cassandra_version}{smp} --category={self.category} --verbose=ccm ' \
              f'--gtest_filter={gtest_filter} ' \
              f'--gtest_output=xml:{self._cpp_driver_git}/log/TEST-{self.driver_type}-{self._driver_version}.xml'
        logging.info(cmd)
        result = subprocess.run(cmd, shell=True, capture_output=True)

        # Print command output in the log
        logging.info(result.stdout.decode())
        logging.info(result.stderr.decode())

        return self.analyze_results(result.stdout.decode(), result.stderr.decode(), result.returncode)

    def analyze_results(self, stdout: str, stderr: str, returncode: int) -> TestResults:
        running_tests = passed_tests = failed_tests = ran_tests = 0
        failed_tests_list = []

        # How many test cases should be run
        search_result = re.search(r"Running (\d+) test.? from (\d+) test.? case", stdout)
        if search_result:
            running_tests = int(search_result.group(1))

        search_result = re.search(r"\[[ ]{2}PASSED[ ]{2}] (\d+) test", stdout)
        if search_result:
            passed_tests = int(search_result.group(1))

        search_result = re.search(r"\[[ ]{2}FAILED[ ]{2}] (\d+) test", stdout)
        if search_result:
            failed_tests = int(search_result.group(1))

        # How many test cases were run
        search_result = re.search(r"\[==========] (\d+) test.? from (\d+) test case.? ran", stdout)
        if search_result:
            ran_tests = int(search_result.group(1))

        if failed_tests:
            failed_tests_list = re.findall(r"\[[ ]{2}FAILED[ ]{2}] (\w+.\w+)", stdout)
            if failed_tests_list:
                failed_tests_list = list(set(failed_tests_list))

        error = stderr if returncode != 0 else ''

        return TestResults(running_tests=running_tests, ran_tests=ran_tests, failed=failed_tests, passed=passed_tests,
                           returncode=returncode, error=error, failed_tests=failed_tests_list)
