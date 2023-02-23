def setupTestEnv(String buildMode, String architecture=generalProperties.x86ArchName, boolean dryRun=false, String scyllaVersion, String scyllaRelease) {
	// This override of HOME as an empty dir is needed by ccm
	echo "Setting test environment, mode: |$buildMode|, architecture: |$architecture|"
	def homeDir="$WORKSPACE/cluster_home"
	createEmptyDir(homeDir)
	unifiedPackageName = artifact.relocUnifiedPackageName (
		dryRun: dryRun,
		checkLocal: true,
		mustExist: false,
		urlOrPath: "$WORKSPACE/${gitProperties.scyllaCheckoutDir}/build/$buildMode/dist/tar",
		buildMode: buildMode,
		architecture: architecture,
	)

	String scyllaUnifiedPkgFile = "$WORKSPACE/${gitProperties.scyllaCheckoutDir}/build/$buildMode/dist/tar/${unifiedPackageName}"
	echo "Test will use package: $scyllaUnifiedPkgFile"
	boolean pkgFileExists = fileExists scyllaUnifiedPkgFile
	env.NODE_INDEX = generalProperties.smpNumber
	env.SCYLLA_VERSION = artifactScyllaVersion()
	if (!env.MAPPED_SCYLLA_VERSION && !general.versionFormatOK(env.SCYLLA_VERSION)) {
		env.MAPPED_SCYLLA_VERSION = "999.99.0"
	}
	env.EVENT_LOOP_MANAGER = "asyncio"
	// Some tests need event loop, 'asyncio' is most tested, so let's use it
	env.SCYLLA_UNIFIED_PACKAGE = scyllaUnifiedPkgFile
	env.DTEST_REQUIRE = "${branchProperties.dtstRequireValue}" // Could be empty / not exist
}

def createEmptyDir(String path) {
	sh "rm -rf $path && mkdir -p $path"
}

def artifactScyllaVersion() {
	def versionFile = generalProperties.buildMetadataFile
	def scyllaSha = ""
	boolean versionFileExists = fileExists "${versionFile}"
	if (versionFileExists) {
		scyllaSha = sh(script: "awk '/scylladb\\/scylla(-enterprise)?\\.git/ { print \$NF }' ${generalProperties.buildMetadataFile}", returnStdout: true).trim()
	}
	echo "Version is: |$scyllaSha|"
	return scyllaSha
}

def doCPPDriverMatrixTest  (Map args) {
	// Run the CPP test upon different repos
	// Parameters:
	// boolean (default false): dryRun - Run builds on dry run (that will show commands instead of really run them).
	// string (mandatory): driverCheckoutDir - Scylla or datastax checkout dir
	// String (mandatory): driverType - scylla || datastax
	// String (mandatory): cppDriverVersions - CPP driver versions to check
	// String (mandatory): cqlCassandraVersion - CQL Cassandra version
	// String (default: x86_64): architecture Which architecture to publish x86_64|aarch64
	// String (mandatory): scyllaVersion - Scylla version
	// String (mandatory): scyllaRelease - Scylla release

	general.traceFunctionParams ("test.doCPPDriverMatrixTest", args)
	general.errorMissingMandatoryParam ("test.doCPPDriverMatrixTest",
		[driverCheckoutDir: "$args.driverCheckoutDir",
		 driverType: "$args.driverType",
		 cppDriverVersions: "$args.cppDriverVersions",
		 cqlCassandraVersion: "$args.cqlCassandraVersion",
		 scyllaVersion: "$args.scyllaVersion",
		 scyllaRelease: "$args.scyllaRelease",
		])

	boolean dryRun = args.dryRun ?: false
	String webUrl = args.webUrl ?: ""
	String artifactSourceJobNum = args.artifactSourceJobNum ?: ""
	String scyllaBranch = args.scyllaBranch ?: branchProperties.stableBranchName
	String architecture = args.architecture ?: generalProperties.x86ArchName
	String scyllaVersion = args.scyllaVersion
	String scyllaRelease = args.scyllaRelease

	setupTestEnv("release", architecture, dryRun, scyllaVersion, scyllaRelease)
	String pythonParams = "python3 main.py $args.driverCheckoutDir $WORKSPACE/${gitProperties.scyllaCheckoutDir} --driver-type $args.driverType --versions $args.cppDriverVersions"
 	pythonParams += " --scylla-version ${env.SCYLLA_VERSION}"
 	pythonParams += " --summary-file $WORKSPACE/$gitProperties.cppDriverMatrixCheckoutDir/summary.log"
 	pythonParams += " --cql-cassandra-version $args.cqlCassandraVersion"
 	pythonParams += " --version-size 2"
 	if (args.email_recipients?.trim()) {
		pythonParams += " --recipients $args.email_recipients"
	}
	dir("$WORKSPACE/$gitProperties.cppDriverMatrixCheckoutDir") {
		general.runOrDryRunSh (dryRun, "$WORKSPACE/$gitProperties.cppDriverMatrixCheckoutDir/scripts/run_test.sh $pythonParams", "Run CPP Driver Matrix test")
	}
}

return this
