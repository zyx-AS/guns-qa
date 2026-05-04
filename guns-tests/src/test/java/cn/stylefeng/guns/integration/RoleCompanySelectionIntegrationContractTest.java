package cn.stylefeng.guns.integration;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;

class RoleCompanySelectionIntegrationContractTest extends FrontendContractTestSupport {

    @Test
    void shouldHandleEmptyCompanySelectionWithoutCrashing() throws Exception {
        String content = readVueFile("stylefeng-Guns/guns-front-project/src/views/system/auth/role/components/role-form.vue");
        String closeHandler = requireSection(
                content,
                "const closeSelectCompany = data => {",
                "Could not find closeSelectCompany."
        );

        boolean hasDirectDestructure =
                closeHandler.contains("selectCompanyList[0]") && closeHandler.contains("{ bizId");
        boolean hasGuard =
                closeHandler.contains("length") || closeHandler.contains("?.") || closeHandler.contains("if");

        assertFalse(
                hasDirectDestructure && !hasGuard,
                "Empty selectCompanyList should be guarded before destructuring."
        );
    }
}
