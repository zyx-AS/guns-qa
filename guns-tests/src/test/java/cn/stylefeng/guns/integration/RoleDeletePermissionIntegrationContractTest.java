package cn.stylefeng.guns.integration;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RoleDeletePermissionIntegrationContractTest extends FrontendContractTestSupport {

    @Test
    void shouldBindDeleteActionsToDeleteRolePermission() throws Exception {
        String content = readVueFile("stylefeng-Guns/guns-front-project/src/views/system/auth/role/index.vue");

        String batchDeleteSection = requireSection(content, "批量删除", "未找到批量删除代码片段");
        String rowDeleteSection = requireSection(content, "title=\"删除\"", "未找到删除按钮代码片段");

        boolean hasWrongPermission =
                batchDeleteSection.contains("EDIT_ROLE") || rowDeleteSection.contains("EDIT_ROLE");
        boolean hasDeletePermission =
                batchDeleteSection.contains("DELETE_ROLE") && rowDeleteSection.contains("DELETE_ROLE");

        assertTrue(rowDeleteSection.contains("@click=\"remove(record)\""));
        assertFalse(hasWrongPermission, "删除操作错误绑定 EDIT_ROLE 权限");
        assertTrue(hasDeletePermission, "删除操作未绑定 DELETE_ROLE 权限");
    }
}
