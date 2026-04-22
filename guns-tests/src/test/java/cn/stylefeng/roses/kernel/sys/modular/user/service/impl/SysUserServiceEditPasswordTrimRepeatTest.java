package cn.stylefeng.roses.kernel.sys.modular.user.service.impl;

import cn.hutool.extra.spring.SpringUtil;
import cn.stylefeng.roses.kernel.auth.api.LoginUserApi;
import cn.stylefeng.roses.kernel.auth.api.password.PasswordStoredEncryptApi;
import cn.stylefeng.roses.kernel.auth.api.pojo.login.LoginUser;
import cn.stylefeng.roses.kernel.auth.api.pojo.password.SaltedEncryptResult;
import cn.stylefeng.roses.kernel.rule.exception.base.ServiceException;
import cn.stylefeng.roses.kernel.sys.api.SecurityConfigService;
import cn.stylefeng.roses.kernel.sys.modular.user.entity.SysUser;
import cn.stylefeng.roses.kernel.sys.modular.user.enums.SysUserExceptionEnum;
import cn.stylefeng.roses.kernel.sys.modular.user.pojo.request.SysUserRequest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class SysUserServiceEditPasswordTrimRepeatTest {

    @Mock
    private PasswordStoredEncryptApi passwordStoredEncryptApi;

    @Mock
    private SecurityConfigService securityConfigService;

    @Mock
    private LoginUserApi loginUserApi;

    @Spy
    @InjectMocks
    private SysUserServiceImpl sysUserService;

    @Test
    void shouldRejectPasswordChangeWhenTrimmedNewPasswordMatchesOldPassword() {
        Long userId = 10001L;

        SysUserRequest request = new SysUserRequest();
        request.setPassword("abc123");
        request.setNewPassword("abc123 ");

        SysUser sysUser = new SysUser();
        sysUser.setUserId(userId);
        sysUser.setPassword("stored-password");
        sysUser.setPasswordSalt("stored-salt");

        LoginUser loginUser = new LoginUser();
        loginUser.setUserId(userId);
        loginUser.setAccount("ut-u-02");

        SaltedEncryptResult saltedEncryptResult = new SaltedEncryptResult();
        saltedEncryptResult.setEncryptPassword("new-encrypted-password");
        saltedEncryptResult.setPasswordSalt("new-salt");

        doReturn(sysUser).when(sysUserService).getById(userId);
        doReturn(true).when(sysUserService).updateById(any(SysUser.class));
        when(loginUserApi.getLoginUser()).thenReturn(loginUser);
        when(passwordStoredEncryptApi.checkPasswordWithSalt("abc123", "stored-salt", "stored-password"))
                .thenReturn(Boolean.TRUE);
        when(passwordStoredEncryptApi.encryptWithSalt("abc123")).thenReturn(saltedEncryptResult);

        try (MockedStatic<SpringUtil> springUtilMock = mockStatic(SpringUtil.class)) {
            springUtilMock.when(() -> SpringUtil.getBean(LoginUserApi.class)).thenReturn(loginUserApi);

            ServiceException exception = assertThrows(
                    ServiceException.class,
                    () -> sysUserService.editPassword(request)
            );

            assertEquals(SysUserExceptionEnum.USER_PWD_REPEAT.getErrorCode(), exception.getErrorCode());
            assertEquals(SysUserExceptionEnum.USER_PWD_REPEAT.getUserTip(), exception.getUserTip());
        }
    }
}
