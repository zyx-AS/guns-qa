package cn.stylefeng.roses.kernel.sys.modular.app.controller;

import cn.stylefeng.roses.kernel.scanner.api.annotation.PostResource;
import cn.stylefeng.roses.kernel.sys.modular.app.pojo.request.SysAppRequest;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.assertAll;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SysAppUpdateStatusPermissionContractTest {

    private static final Path APP_PAGE = Path.of(
            "guns-front-project",
            "src",
            "views",
            "system",
            "auth",
            "app",
            "index.vue"
    );

    private static final Pattern USER_STORE_PERMISSION_PATTERN = Pattern.compile(
            "userStore\\.authorities\\.find\\([\\s\\S]*?['\"]([^'\"]+)['\"]"
    );

    @Test
    void appStatusSwitchPermissionShouldMatchBackendUpdateStatusContract() throws Exception {
        String appPageSource = readAppPageSource();

        String statusSwitchBlock = vxeSwitchBlockForChange(appPageSource, "statusFlagChange(record)");
        String statusChangeBlock = functionBlock(appPageSource, "const statusFlagChange = record =>");
        String frontEndPermission = disabledComputedPermission(appPageSource);
        String backendPermission = backendRequiredPermission("updateStatus");

        assertAll(
                () -> assertTrue(
                        statusSwitchBlock.contains(":disabled=\"disabled\""),
                        "The app status switch should be guarded by the shared disabled permission computed value."
                ),
                () -> assertTrue(
                        statusChangeBlock.contains("AppApi.updateStatus"),
                        "The guarded app status switch should call AppApi.updateStatus."
                ),
                () -> assertEquals(
                        backendPermission,
                        frontEndPermission,
                        "The app status switch must be enabled by the same permission required by /sysApp/updateStatus."
                )
        );
    }

    private static String readAppPageSource() throws IOException {
        assertTrue(
                Files.isRegularFile(APP_PAGE),
                () -> "Expected GUNS front-end app page to exist at " + APP_PAGE.toAbsolutePath()
        );
        return new String(Files.readAllBytes(APP_PAGE), StandardCharsets.UTF_8);
    }

    private static String backendRequiredPermission(String methodName) throws NoSuchMethodException {
        Method method = SysAppController.class.getDeclaredMethod(methodName, SysAppRequest.class);
        PostResource postResource = method.getAnnotation(PostResource.class);
        assertNotNull(postResource, () -> "Expected @PostResource on SysAppController#" + methodName);
        assertTrue(
                postResource.requiredPermission(),
                () -> "Expected SysAppController#" + methodName + " to require permission checking"
        );
        return postResource.requirePermissionCode();
    }

    private static String disabledComputedPermission(String source) {
        String disabledBlock = functionBlock(source, "const disabled = computed(() =>");
        Matcher matcher = USER_STORE_PERMISSION_PATTERN.matcher(disabledBlock);
        assertTrue(matcher.find(), () -> "Could not find the permission checked by the disabled computed value:\n" + disabledBlock);
        return matcher.group(1);
    }

    private static String vxeSwitchBlockForChange(String source, String changeHandler) {
        int changeIndex = source.indexOf("@change=\"" + changeHandler + "\"");
        assertTrue(changeIndex >= 0, () -> "Could not find app status switch change handler " + changeHandler);

        int blockStart = source.lastIndexOf("<vxe-switch", changeIndex);
        int blockEnd = source.indexOf("</vxe-switch>", changeIndex);
        assertTrue(blockStart >= 0 && blockEnd > changeIndex, () -> "Could not extract app status switch block for " + changeHandler);
        return source.substring(blockStart, blockEnd);
    }

    private static String functionBlock(String source, String functionStart) {
        int start = source.indexOf(functionStart);
        assertTrue(start >= 0, () -> "Could not find source block starting with " + functionStart);

        int end = source.indexOf(";\n", start);
        assertTrue(end > start, () -> "Could not extract source block starting with " + functionStart);
        return source.substring(start, end + 1);
    }
}
