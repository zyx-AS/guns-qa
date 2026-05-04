package cn.stylefeng.guns.integration;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class UserRoleSearchParameterIntegrationContractTest extends FrontendContractTestSupport {

    @Test
    void userRoleSearchShouldUseBackendSearchTextContract() throws Exception {
        String source = readFrontend("views/system/structure/user/components/allocation-role.vue");

        assertTrue(source.contains("searchText"), "User role assignment should send searchText to the role tree APIs.");
        assertFalse(
                source.contains("searhText"),
                "Misspelled searhText breaks the page-to-API search contract for role assignment."
        );
    }
}
