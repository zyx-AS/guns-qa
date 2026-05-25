package cn.stylefeng.roses.kernel.sys.modular.user.service.impl;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

class UnauthorizedAccessTest {

    @Test
    void shouldNotAllowUnauthorizedAccess() {
        boolean hasPermission = false;
        assertTrue(hasPermission, "未授权用户居然可以访问");
    }
}
