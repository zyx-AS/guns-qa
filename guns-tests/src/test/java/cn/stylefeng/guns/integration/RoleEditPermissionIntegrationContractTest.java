package cn.stylefeng.guns.integration;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RoleEditPermissionIntegrationContractTest extends FrontendContractTestSupport {

    @Test
    void shouldNotBindEditButtonToDeleteRolePermission() throws Exception {
        String content = readVueFile("stylefeng-Guns/guns-front-project/src/views/system/auth/role/index.vue");
        String editSection = requireSection(content, "title=\"编辑\"", "未找到编辑按钮代码片段");

        assertTrue(editSection.contains("@click=\"openAddEdit(record)\""));
        assertFalse(editSection.contains("DELETE_ROLE"), "编辑按钮错误绑定 DELETE_ROLE 权限");
        assertTrue(editSection.contains("EDIT_ROLE"), "编辑按钮未绑定 EDIT_ROLE 权限");
    }
}
