package cn.stylefeng.guns.integration;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

abstract class FrontendContractTestSupport {

    private static final Path FRONTEND_ROOT = Path.of("guns-front-project", "src");

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

    protected String readVueFile(String relativePath) throws IOException {
        String normalizedPath = relativePath.replace('\\', '/');
        String prefix = "guns-front-project/src/";
        int prefixIndex = normalizedPath.indexOf(prefix);
        if (prefixIndex >= 0) {
            normalizedPath = normalizedPath.substring(prefixIndex + prefix.length());
        }
        return readFrontend(normalizedPath);
    }

    protected String extractSection(String source, String anchor) {
        int anchorIndex = source.indexOf(anchor);
        if (anchorIndex < 0) {
            return null;
        }

        String[] startTokens = new String[] {"<icon-font", "<a-menu-item", "<div", "const "};
        int start = -1;
        String matchedStartToken = null;
        for (String token : startTokens) {
            int tokenIndex = source.lastIndexOf(token, anchorIndex);
            if (tokenIndex > start) {
                start = tokenIndex;
                matchedStartToken = token;
            }
        }

        if (start < 0 || matchedStartToken == null) {
            return null;
        }

        String endToken;
        if ("<icon-font".equals(matchedStartToken)) {
            endToken = "</icon-font>";
        } else if ("<a-menu-item".equals(matchedStartToken)) {
            endToken = "</a-menu-item>";
        } else if ("<div".equals(matchedStartToken)) {
            endToken = "</div>";
        } else {
            endToken = "\n};";
        }

        int end = source.indexOf(endToken, anchorIndex);
        if (end < 0) {
            return null;
        }

        return source.substring(start, end + endToken.length());
    }

    protected String requireSection(String source, String anchor, String message) {
        String section = extractSection(source, anchor);
        assertNotNull(section, message);
        return section;
    }
}
