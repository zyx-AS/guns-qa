package cn.stylefeng.roses.kernel.sys.modular.user.service.impl;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

class NullInputValidationTest {

    @Test
    void shouldHandleNullUsername() {
        String username = null;
        assertTrue(username != null, "用户名为空未处理");
    }
}
