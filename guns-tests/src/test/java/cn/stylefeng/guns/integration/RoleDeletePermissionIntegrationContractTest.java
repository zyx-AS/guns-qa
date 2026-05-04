package cn.stylefeng.guns.integration;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RoleDeletePermissionIntegrationContractTest extends FrontendContractTestSupport {

    @Test
    void shouldBindDeleteActionsToDeleteRolePermission() throws Exception {
        String content = readVueFile("stylefeng-Guns/guns-front-project/src/views/system/auth/role/index.vue");

        String batchDeleteSection = requireSection(content, "批量删除", "Could not find the batch delete section.");
        String rowDeleteSection = requireSection(content, "title=\"删除\"", "Could not find the row delete section.");

        boolean hasWrongPermission =
                batchDeleteSection.contains("EDIT_ROLE") || rowDeleteSection.contains("EDIT_ROLE");
        boolean hasDeletePermission =
                batchDeleteSection.contains("DELETE_ROLE") && rowDeleteSection.contains("DELETE_ROLE");

        assertTrue(rowDeleteSection.contains("@click=\"remove(record)\""));
        assertFalse(hasWrongPermission, "Role delete is incorrectly bound to EDIT_ROLE.");
        assertTrue(hasDeletePermission, "Role delete should be bound to DELETE_ROLE.");
    }
}
