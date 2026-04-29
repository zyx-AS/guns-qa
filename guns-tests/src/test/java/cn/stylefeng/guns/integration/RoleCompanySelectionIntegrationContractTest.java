package cn.stylefeng.guns.integration;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;

class RoleCompanySelectionIntegrationContractTest extends FrontendContractTestSupport {

    @Test
    void shouldHandleEmptyCompanySelectionWithoutCrashing() throws Exception {
        String content = readVueFile("stylefeng-Guns/guns-front-project/src/views/system/auth/role/components/role-form.vue");
        String closeHandler = requireSection(content, "const closeSelectCompany = data => {", "未找到 closeSelectCompany 方法");

        boolean hasDirectDestructure =
                closeHandler.contains("selectCompanyList[0]") && closeHandler.contains("{ bizId");
        boolean hasGuard =
                closeHandler.contains("length") || closeHandler.contains("?.") || closeHandler.contains("if");

        assertFalse(hasDirectDestructure && !hasGuard, "存在未做空判断的数组解构，可能导致运行时崩溃");
    }
}
