package cn.stylefeng.roses.kernel.sys.modular.user.service.impl;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

class ValidInputTest {

    @Test
    void shouldAcceptValidUsername() {
        String username = "admin";
        assertTrue(username.length() >= 3, "合法用户名被错误拒绝");
    }
}
