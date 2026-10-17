import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;

import org.jacoco.cli.internal.core.analysis.Analyzer;
import org.jacoco.cli.internal.core.analysis.CoverageBuilder;
import org.jacoco.cli.internal.core.analysis.IBundleCoverage;
import org.jacoco.cli.internal.core.tools.ExecFileLoader;
import org.jacoco.cli.internal.report.DirectorySourceFileLocator;
import org.jacoco.cli.internal.report.IReportGroupVisitor;
import org.jacoco.cli.internal.report.IReportVisitor;
import org.jacoco.cli.internal.report.xml.XMLFormatter;

/**
 * Write a JaCoCo XML report with groups, as Maven's goal 'report-aggregate' or Ant's task 'report' write it, using the
 * API of JaCoCo's CLI JAR.
 *
 * Arguments: the execution data file, the directory of the class files, the directory of the sources, the report file.
 */
public class GroupedReport {
	public static void main(String[] arguments) throws IOException {
		ExecFileLoader loader = new ExecFileLoader();
		loader.load(new File(arguments[0]));
		File classes = new File(arguments[1]);
		DirectorySourceFileLocator sources = new DirectorySourceFileLocator(new File(arguments[2]), "UTF-8", 4);

		try (OutputStream output = new FileOutputStream(arguments[3])) {
			IReportVisitor visitor = new XMLFormatter().createVisitor(output);
			visitor.visitInfo(loader.getSessionInfoStore().getInfos(), loader.getExecutionDataStore().getContents());

			IReportGroupVisitor report = visitor.visitGroup("JaCoCo-Groups");
			IReportGroupVisitor library = report.visitGroup("Library");
			library.visitBundle(analyze(loader, "Shapes", new File(classes, "shapes")), sources);
			library.visitBundle(analyze(loader, "Utilities", new File(classes, "util")), sources);
			report.visitBundle(analyze(loader, "Application", new File(classes, "Main.class")), sources);
			visitor.visitEnd();
		}
	}

	private static IBundleCoverage analyze(ExecFileLoader loader, String name, File classes) throws IOException {
		CoverageBuilder builder = new CoverageBuilder();
		new Analyzer(loader.getExecutionDataStore(), builder).analyzeAll(classes);
		return builder.getBundle(name);
	}
}
