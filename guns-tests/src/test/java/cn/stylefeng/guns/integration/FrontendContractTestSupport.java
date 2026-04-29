package cn.stylefeng.guns.integration;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.assertTrue;

final class FrontendContractTestSupport {

    private static final Path FRONTEND_ROOT = Path.of("guns-front-project", "src");

    private FrontendContractTestSupport() {
    }

    static String readFrontend(String relativePath) throws IOException {
        Path path = FRONTEND_ROOT.resolve(relativePath);
        assertTrue(Files.exists(path), "Missing front-end source file: " + path.toAbsolutePath());
        return Files.readString(path, StandardCharsets.UTF_8);
    }

    static Matcher requireMatch(String source, String regex, String message) {
        Matcher matcher = Pattern.compile(regex, Pattern.DOTALL).matcher(source);
        assertTrue(matcher.find(), message);
        return matcher;
    }
}
