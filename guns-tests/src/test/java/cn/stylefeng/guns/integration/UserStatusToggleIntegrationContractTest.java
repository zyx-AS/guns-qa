package cn.stylefeng.guns.integration;

import org.junit.jupiter.api.Test;

import java.util.regex.Matcher;

import static cn.stylefeng.guns.integration.FrontendContractTestSupport.readFrontend;
import static cn.stylefeng.guns.integration.FrontendContractTestSupport.requireMatch;
import static org.junit.jupiter.api.Assertions.assertTrue;

class UserStatusToggleIntegrationContractTest {

    @Test
    void userStatusToggleShouldRollbackOrReloadWhenApiFails() throws Exception {
        String source = readFrontend("views/system/structure/user/index.vue");
        Matcher handler = requireMatch(
                source,
                "const statusFlagChange = record => \\{[\\s\\S]*?\\n\\};",
                "User status switch should define statusFlagChange(record)."
        );
        String statusHandler = handler.group();

        assertTrue(
                statusHandler.contains(".catch(") || statusHandler.contains("reload()"),
                "User status toggle changes the row through v-model before updateStatus returns; failures must rollback or reload the table."
        );
    }
}
