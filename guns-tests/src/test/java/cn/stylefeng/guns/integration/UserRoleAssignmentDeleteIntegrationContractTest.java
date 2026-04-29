package cn.stylefeng.guns.integration;

import org.junit.jupiter.api.Test;

import java.util.regex.Matcher;

import static cn.stylefeng.guns.integration.FrontendContractTestSupport.readFrontend;
import static cn.stylefeng.guns.integration.FrontendContractTestSupport.requireMatch;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class UserRoleAssignmentDeleteIntegrationContractTest {

    @Test
    void userRoleAssignmentDeleteShouldNotSpliceWhenRoleIsMissing() throws Exception {
        String source = readFrontend("views/system/structure/user/components/allocation-role.vue");
        Matcher deleteClick = requireMatch(
                source,
                "const deleteClick = record => \\{[\\s\\S]*?\\n\\};",
                "User role assignment should define deleteClick(record)."
        );
        String handler = deleteClick.group();

        assertFalse(
                handler.matches("(?s).*splice\\(\\s*selectList\\.value\\.findIndex\\([\\s\\S]*?,\\s*1\\s*\\).*"),
                "deleteClick must not pass findIndex directly into splice because findIndex can return -1 and remove the last selected role."
        );
        assertTrue(
                handler.matches("(?s).*findIndex[\\s\\S]*(>=\\s*0|!==\\s*-1|>\\s*-1).*"),
                "deleteClick should guard the findIndex result before mutating selectList."
        );
    }
}
