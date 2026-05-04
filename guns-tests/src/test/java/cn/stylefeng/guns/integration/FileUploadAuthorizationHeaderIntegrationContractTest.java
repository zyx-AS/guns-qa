package cn.stylefeng.guns.integration;

import org.junit.jupiter.api.Test;

import java.util.regex.Matcher;

import static cn.stylefeng.guns.integration.FrontendContractTestSupport.readFrontend;
import static cn.stylefeng.guns.integration.FrontendContractTestSupport.requireMatch;
import static org.junit.jupiter.api.Assertions.assertFalse;

class FileUploadAuthorizationHeaderIntegrationContractTest {

    @Test
    void fileUploadAuthorizationHeaderShouldBeResolvedAtUploadTime() throws Exception {
        String source = readFrontend("views/system/backend/file/index.vue");
        Matcher headersBlock = requireMatch(source, "const headers = ref\\(\\{[\\s\\S]*?\\}\\);", "Upload headers should exist.");

        assertFalse(
                headersBlock.group().matches("(?s).*Authorization:\\s*getToken\\(\\).*"),
                "Upload Authorization is captured once at module setup; it should be resolved at upload time."
        );
    }
}
