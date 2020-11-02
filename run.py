import re
import os
import yaml
import logging
import subprocess
from packaging.version import Version

from typing import NamedTuple



class TestResults(NamedTuple):
    tests: int
    failed: int
    passed: int
    returncode: int
    error: str

class Run:

    def __init__(self, cpp_driver_git: str, scylla_install_dir: str, driver_type: str, tag: str, protocol: str,
                 scylla_version: str=None):
        self._tag = tag
        self._cpp_driver_git = cpp_driver_git
        self._scylla_install_dir = scylla_install_dir
        self._scylla_version = scylla_version
        self._protocol = protocol
        self._version_folder = None
        self.driver_type = driver_type
        if self.driver_type == 'scylla':
            # this target ("CASSANDRA") is adapted to work with scylla
            self._category = 'CASSANDRA'
        elif self.driver_type == 'datastax':
            self._category = 'DSE'
        self.run_compile_after_patch = True

    @property
    def version_folder(self):
        if self._version_folder is not None:
            return self._version_folder
        self._version_folder = self.__version_folder(self.driver_type, self._tag)
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
        return os.path.join(here, 'versions', self.version_folder, 'tests.yaml')

    def _testsList(self):
        ignore_tests = []
        with open(self._testsFile()) as f:
            content = yaml.load(f)
            ignore_tests.extend(content['tests'])
        return ignore_tests

    # def _environment(self):
    #     result = {}
    #     result.update(os.environ)
    #     if self._scylla_version:
    #         result['SCYLLA_VERSION'] = self._scylla_version
    #     else:
    #         result['INSTALL_DIRECTORY'] = self._scylla_install_dir
    #     return result

    def _apply_patch(self):
        try:
            patch_file = os.path.join(self.version_folder, 'patch')

            if not os.path.exists(patch_file):
                logging.info('Cannot find patch for version {}'.format(self._tag))
                self.run_compile_after_patch = False
                return True

            if os.path.getsize(patch_file) == 0:
                logging.info('Patch file is empty. Skip applying')
                self.run_compile_after_patch = False
                return True

            command = "patch -p1 -i {}".format(patch_file)
            subprocess.check_call(command, shell=True)
            self.run_compile_after_patch = True
            return True
        except Exception as exc:
            logging.error("Failed to apply patch to version {}, with: {}".format(self._tag, str(exc)))
            return False

    def compile_tests(self):
        if self.driver_type == "scylla":
            os.chdir(os.path.join(self._cpp_driver_git, 'build'))
            cmd = "cmake -DCASS_BUILD_INTEGRATION_TESTS=ON .. && make"
            subprocess.check_call(cmd, shell=True)
        else:
            pass

        os.chdir(self._cpp_driver_git)

    def _checkout_branch(self):
        try:
            subprocess.check_call('git checkout .', shell=True)
            if self.driver_type == 'scylla':
                subprocess.check_call('git checkout {}'.format(self._tag), shell=True)
            else:
                subprocess.check_call('git checkout {}-dse'.format(self._tag), shell=True)
            return True
        except Exception as exc:
            logging.error("Failed to branch for version {}, with: {}".format(self._tag, str(exc)))
            return False

    def _publish_fake_result(self):
        return TestResults(testcases=0, failed=0, passed=0, returncode=0, error='error')

    def run(self) -> TestResults:
        os.chdir(self._cpp_driver_git)

        # if not self._checkout_branch():
        #     return self._publish_fake_result()

        if not self._apply_patch():
            return self._publish_fake_result()

        if self.run_compile_after_patch:
            self.compile_tests()

        gtest_filter = ':'.join(self._testsList())
        cmd = f'{self._cpp_driver_git}/build/cassandra-integration-tests --install-dir={self._scylla_install_dir} ' \
              f'--version={self._tag} --category={self._category} --verbose=ccm --gtest_filter={gtest_filter}'
        logging.info(cmd)
        result = subprocess.run(cmd, shell=True, capture_output=True)

        # Print command output in the log
        logging.info(result.stdout.decode())
        logging.info(result.stderr.decode())
        # self.logging_cmd_output(result.stdout)
        # self.logging_cmd_output(result.stderr)

        return self.analize_results(result.stdout.decode(), result.stderr.decode(), result.returncode)

    def analize_results(self, stdout:str, stderr:str, returncode:int) -> TestResults:
        passed_tests = failed_tests = ran_tests = 0
        search_result = re.search(r"\[[ ]{2}PASSED[ ]{2}] (\d+) test", stdout)
        if search_result:
            passed_tests = int(search_result.group(1))

        search_result = re.search(r"\[[ ]{2}FAILED[ ]{2}] (\d+) test", stdout)
        if search_result:
            failed_tests = int(search_result.group(1))

        # How many test cases were run
        search_result = re.search(r"\[==========] (\d+) test from (\d+) test case ran", stdout)
        if search_result:
            ran_tests = int(search_result.group(1))

        error = stderr if returncode != 0 else ''

        return TestResults(tests=ran_tests, failed=failed_tests, passed=passed_tests, returncode=returncode,
                           error=error)

    # @staticmethod
    # def logging_cmd_output(outstr: bytes):
    #     for out in outstr.decode().split("\n"):
    #         logging.info(out)
    #
    #     logging.info('')
