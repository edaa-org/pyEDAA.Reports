plugins {
	java
}

repositories {
	mavenCentral()
}

dependencies {
	testImplementation(platform("org.junit:junit-bom:6.1.3"))
	testImplementation("org.junit.jupiter:junit-jupiter")
	testRuntimeOnly("org.junit.platform:junit-platform-launcher")
	testRuntimeOnly("org.junit.platform:junit-platform-reporting")
}

tasks.test {
	useJUnitPlatform()
	ignoreFailures = true

	val outputDirectory = reports.junitXml.outputLocation
	jvmArgumentProviders += CommandLineArgumentProvider {
		listOf(
			"-Djunit.platform.reporting.open.xml.enabled=true",
			"-Djunit.platform.reporting.output.dir=${outputDirectory.get().asFile.absolutePath}",
			"-Djunit.platform.output.capture.stdout=true",
			"-Djunit.platform.output.capture.stderr=true"
		)
	}
}
