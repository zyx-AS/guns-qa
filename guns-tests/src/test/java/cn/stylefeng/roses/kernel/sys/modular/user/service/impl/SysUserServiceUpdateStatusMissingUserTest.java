package cn.stylefeng.roses.kernel.sys.modular.user.service.impl;

import cn.stylefeng.guns.testsupport.MybatisPlusLambdaMetadataSupport;
import cn.stylefeng.roses.kernel.rule.exception.base.ServiceException;
import cn.stylefeng.roses.kernel.sys.api.enums.user.UserStatusEnum;
import cn.stylefeng.roses.kernel.sys.modular.user.entity.SysUser;
import cn.stylefeng.roses.kernel.sys.modular.user.pojo.request.SysUserRequest;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.mockito.InjectMocks;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.nullable;
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

    @ParameterizedTest
    @MethodSource("missingUserStatusCases")
    void shouldRejectStatusUpdateWhenUserDoesNotExist(Long userId, Integer statusFlag) {
        SysUserRequest request = new SysUserRequest();
        request.setUserId(userId);
        request.setStatusFlag(statusFlag);

        doReturn(Boolean.FALSE).when(sysUserService).getUserSuperAdminFlag(nullable(Long.class));
        doReturn("ghost-user").when(sysUserService).getUserRealName(nullable(Long.class));
        doReturn(Boolean.FALSE).when(sysUserService).update(any(Wrapper.class));
        doReturn(null).when(sysUserService).getOne(any(Wrapper.class));

        assertThrows(ServiceException.class, () -> sysUserService.updateStatus(request));
    }

    private static Stream<org.junit.jupiter.params.provider.Arguments> missingUserStatusCases() {
        return Stream.of(
                org.junit.jupiter.params.provider.Arguments.of(999999L, UserStatusEnum.ENABLE.getCode()),
                org.junit.jupiter.params.provider.Arguments.of(999999L, UserStatusEnum.DISABLE.getCode()),
                org.junit.jupiter.params.provider.Arguments.of(0L, UserStatusEnum.ENABLE.getCode()),
                org.junit.jupiter.params.provider.Arguments.of(-1L, UserStatusEnum.DISABLE.getCode()),
                org.junit.jupiter.params.provider.Arguments.of(null, UserStatusEnum.ENABLE.getCode())
        );
    }
}
