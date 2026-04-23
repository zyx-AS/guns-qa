package cn.stylefeng.roses.kernel.sys.modular.user.service.impl;

import cn.stylefeng.guns.testsupport.MybatisPlusLambdaMetadataSupport;
import cn.stylefeng.roses.kernel.rule.exception.base.ServiceException;
import cn.stylefeng.roses.kernel.sys.api.enums.user.UserStatusEnum;
import cn.stylefeng.roses.kernel.sys.modular.user.entity.SysUser;
import cn.stylefeng.roses.kernel.sys.modular.user.pojo.request.SysUserRequest;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doReturn;

@ExtendWith(MockitoExtension.class)
class SysUserServiceUpdateStatusMissingUserTest {

    @BeforeAll
    static void initMybatisPlusMetadata() {
        MybatisPlusLambdaMetadataSupport.initEntityMetadata(SysUser.class);
    }

    @Spy
    @InjectMocks
    private SysUserServiceImpl sysUserService;

    @Test
    void shouldRejectStatusUpdateWhenUserDoesNotExist() {
        SysUserRequest request = new SysUserRequest();
        request.setUserId(999999L);
        request.setStatusFlag(UserStatusEnum.DISABLE.getCode());

        doReturn(Boolean.FALSE).when(sysUserService).getUserSuperAdminFlag(999999L);
        doReturn("ghost-user").when(sysUserService).getUserRealName(999999L);
        doReturn(Boolean.FALSE).when(sysUserService).update(any(Wrapper.class));

        assertThrows(ServiceException.class, () -> sysUserService.updateStatus(request));
    }
}
