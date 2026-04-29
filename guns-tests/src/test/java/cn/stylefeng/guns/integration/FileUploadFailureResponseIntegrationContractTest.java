package cn.stylefeng.guns.integration;

import org.junit.jupiter.api.Test;

import java.util.regex.Matcher;

import static cn.stylefeng.guns.integration.FrontendContractTestSupport.readFrontend;
import static cn.stylefeng.guns.integration.FrontendContractTestSupport.requireMatch;
import static org.junit.jupiter.api.Assertions.assertTrue;

class FileUploadFailureResponseIntegrationContractTest {

    @Test
    void fileUploadFailureResponseShouldNotBeReportedAsSuccess() throws Exception {
        String source = readFrontend("views/system/backend/file/index.vue");
        Matcher afterUpload = requireMatch(
                source,
                "const afterUpload = \\(\\{ file \\}\\) => \\{[\\s\\S]*?\\n\\};",
                "afterUpload should exist."
        );
        String handler = afterUpload.group();

        assertTrue(
                handler.matches("(?s).*file\\.response\\.(code|success).*")
                        || handler.matches("(?s).*file\\.status\\s*===\\s*['\"]done['\"].*"),
                "afterUpload must verify the backend success flag/status before showing upload success."
        );
        assertTrue(
                handler.contains("message.error") || handler.contains("message.warning"),
                "afterUpload should surface backend upload failure messages instead of always showing success."
        );
    }
}
