plugins {
	java
	jacoco
}

repositories {
	mavenCentral()
}

dependencies {
	testImplementation("junit:junit:4.13.2")
}

jacoco {
	toolVersion = "0.8.15"
}

tasks.test {
	useJUnit()
	ignoreFailures = true
	finalizedBy(tasks.jacocoTestReport)
}

tasks.jacocoTestReport {
	dependsOn(tasks.test)
	reports {
		xml.required = true
		csv.required = true
		html.required = false
	}
}
