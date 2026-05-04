package cn.stylefeng.guns.integration;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RoleEditPermissionIntegrationContractTest extends FrontendContractTestSupport {

    @Test
    void shouldNotBindEditButtonToDeleteRolePermission() throws Exception {
        String content = readVueFile("stylefeng-Guns/guns-front-project/src/views/system/auth/role/index.vue");
        String editSection = requireSection(content, "title=\"编辑\"", "Could not find the role edit button section.");

        assertTrue(editSection.contains("@click=\"openAddEdit(record)\""));
        assertFalse(editSection.contains("DELETE_ROLE"), "Role edit is incorrectly bound to DELETE_ROLE.");
        assertTrue(editSection.contains("EDIT_ROLE"), "Role edit should be bound to EDIT_ROLE.");
    }
}
