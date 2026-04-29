package cn.stylefeng.guns.integration;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class FrontendIntegrationContractsTest {

    private static final Path FRONTEND_ROOT = Path.of("guns-front-project", "src");

    private static String readFrontend(String relativePath) throws IOException {
        Path path = FRONTEND_ROOT.resolve(relativePath);
        assertTrue(Files.exists(path), "Missing front-end source file: " + path.toAbsolutePath());
        return Files.readString(path, StandardCharsets.UTF_8);
    }

    private static Matcher requireMatch(String source, String regex, String message) {
        Matcher matcher = Pattern.compile(regex, Pattern.DOTALL).matcher(source);
        assertTrue(matcher.find(), message);
        return matcher;
    }

    @Test
    void roleEditActionShouldUseEditPermission() throws Exception {
        String source = readFrontend("views/system/auth/role/index.vue");
        Matcher editAction = requireMatch(
                source,
                "v-permission=\"\\[['\"](?<permission>[^'\"]+)['\"]\\]\"[\\s\\S]{0,500}@click=\"openAddEdit\\(record\\)\"",
                "Role edit action should declare a permission near openAddEdit(record)."
        );

        assertEquals(
                "EDIT_ROLE",
                editAction.group("permission"),
                "Role edit action is wired to the wrong permission, so UI permissions and role edit API access diverge."
        );
    }

    @Test
    void roleDeleteActionsShouldUseDeletePermission() throws Exception {
        String source = readFrontend("views/system/auth/role/index.vue");
        Matcher batchDelete = requireMatch(
                source,
                "v-permission=\"\\[['\"](?<permission>[^'\"]+)['\"]\\]\"[\\s\\S]{0,160}<a-menu-item key=\"1\"",
                "Role batch delete action should declare a permission."
        );
        Matcher rowDelete = requireMatch(
                source,
                "title=\"[^\"]*\"[\\s\\S]{0,160}v-permission=\"\\[['\"](?<permission>[^'\"]+)['\"]\\]\"[\\s\\S]{0,160}@click=\"remove\\(record\\)\"",
                "Role row delete action should declare a permission."
        );

        assertEquals("DELETE_ROLE", batchDelete.group("permission"));
        assertEquals("DELETE_ROLE", rowDelete.group("permission"));
    }

    @Test
    void userRoleSearchShouldUseBackendSearchTextContract() throws Exception {
        String source = readFrontend("views/system/structure/user/components/allocation-role.vue");

        assertTrue(source.contains("searchText"), "User role assignment should send searchText to the role tree APIs.");
        assertFalse(
                source.contains("searhText"),
                "Misspelled searhText breaks the page-to-API search contract for role assignment."
        );
    }

    @Test
    void userFormCertificatePreviewShouldUseCurrentRowUrl() throws Exception {
        String source = readFrontend("views/system/structure/user/components/user-form.vue");
        Matcher preview = requireMatch(source, "const prewiew = row => \\{[\\s\\S]*?\\n\\};", "Preview handler should exist.");
        String handler = preview.group();

        assertTrue(handler.contains("row.attachmentUrl"), "Preview should use the clicked certificate row attachmentUrl.");
        assertFalse(handler.contains("record.attachmentUrl"), "Preview receives row, so record.attachmentUrl is undefined.");
        assertFalse(handler.contains("router.resolve"), "Preview should not call an undeclared router instance.");
    }

    @Test
    void userDetailCertificatePreviewShouldDeclareRouterDependency() throws Exception {
        String source = readFrontend("views/system/structure/user/components/user-detail.vue");
        Matcher imports = requireMatch(source, "<script setup[\\s\\S]*?const props", "Script setup section should be parseable.");
        Matcher preview = requireMatch(source, "const prewiew = record => \\{[\\s\\S]*?\\n\\};", "Preview handler should exist.");

        assertFalse(preview.group().contains("router.resolve"), "Preview should not call router unless useRouter is imported.");
        assertTrue(imports.group().contains("useRouter"), "If router.resolve is used, useRouter must be imported and initialized.");
    }

    @Test
    void roleCompanySelectionShouldHandleEmptySelection() throws Exception {
        String source = readFrontend("views/system/auth/role/components/role-form.vue");
        Matcher closeHandler = requireMatch(
                source,
                "const closeSelectCompany = data => \\{[\\s\\S]*?\\n\\};",
                "Role form company selection callback should exist."
        );
        String handler = closeHandler.group();

        assertTrue(
                handler.matches("(?s).*data\\.selectCompanyList\\[0\\]\\s*\\|\\|.*")
                        || handler.matches("(?s).*data\\.selectCompanyList\\?\\..*")
                        || handler.matches("(?s).*\\?\\.\\[0\\].*"),
                "Company selector callback must tolerate an empty selectCompanyList and enter form validation instead of crashing."
        );
    }

    @Test
    void userImportShouldRejectNonExcelBeforeApiCall() throws Exception {
        String source = readFrontend("views/system/structure/user/components/import-export-user.vue");
        Matcher uploadTag = requireMatch(source, "<a-upload\\s+name=\"file\"[\\s\\S]{0,300}>", "User import upload control should exist.");

        assertTrue(
                uploadTag.group().matches("(?s).*accept=.*\\.(xls|xlsx).*")
                        || uploadTag.group().matches("(?s).*before[-A-Za-z]*=.*"),
                "User import should constrain Excel files before calling uploadAndGetPreviewData."
        );
    }

    @Test
    void fileDownloadShouldNotExposeTokenInUrl() throws Exception {
        String source = readFrontend("views/system/backend/file/api/FileApi.js");

        assertFalse(
                source.contains("token=${params.token}"),
                "File download leaks the login token through the URL instead of an authorization header or one-time token."
        );
    }

    @Test
    void fileUploadAuthorizationHeaderShouldBeResolvedAtUploadTime() throws Exception {
        String source = readFrontend("views/system/backend/file/index.vue");
        Matcher headersBlock = requireMatch(source, "const headers = ref\\(\\{[\\s\\S]*?\\}\\);", "Upload headers should exist.");

        assertFalse(
                headersBlock.group().matches("(?s).*Authorization:\\s*getToken\\(\\).*"),
                "Upload Authorization is captured once at module setup; it should be resolved at upload time after token refresh."
        );
    }

    @Test
    void fileUploadFailureResponseShouldNotBeReportedAsSuccess() throws Exception {
        String source = readFrontend("views/system/backend/file/index.vue");
        Matcher afterUpload = requireMatch(source, "const afterUpload = \\(\\{ file \\}\\) => \\{[\\s\\S]*?\\n\\};", "afterUpload should exist.");
        String handler = afterUpload.group();

        assertTrue(
                handler.matches("(?s).*file\\.response\\.(code|success).*")
                        || handler.matches("(?s).*file\\.status\\s*===\\s*['\"]done['\"].*"),
                "afterUpload must verify the backend success flag/status before showing upload success."
        );
        assertTrue(
                handler.contains("message.error") || handler.contains("message.warning"),
                "afterUpload should surface backend upload failure messages instead of always showing success."
        );
    }
}
