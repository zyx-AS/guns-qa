package cn.stylefeng.roses.kernel.sys.modular.role.service.impl;

import cn.stylefeng.roses.kernel.auth.api.LoginUserApi;
import cn.stylefeng.roses.kernel.auth.api.context.LoginContext;
import cn.stylefeng.roses.kernel.cache.api.CacheOperatorApi;
import cn.stylefeng.roses.kernel.rule.exception.base.ServiceException;
import cn.stylefeng.roses.kernel.sys.api.enums.role.RoleTypeEnum;
import cn.stylefeng.roses.kernel.sys.modular.role.entity.SysRole;
import cn.stylefeng.roses.kernel.sys.modular.role.pojo.request.SysRoleRequest;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class SysRoleServiceDetailCrossCompanyRoleTest {

    @Mock
    private CacheOperatorApi<String> roleNameCache;

    @Mock
    private LoginUserApi loginUserApi;

    @Spy
    @InjectMocks
    private SysRoleServiceImpl sysRoleService;

    @ParameterizedTest
    @MethodSource("roleDetailScenarios")
    void shouldRejectViewingOtherCompanyRoleForNonSuperAdmin(
            Long roleId,
            Integer roleType,
            Long persistedRoleCompanyId,
            boolean shouldThrow
    ) {
        Long currentCompanyId = 100L;

        SysRoleRequest request = new SysRoleRequest();
        request.setRoleId(roleId);

        SysRole persistedRole = null;
        if (roleId != null && !Long.valueOf(999999L).equals(roleId)) {
            persistedRole = new SysRole();
            persistedRole.setRoleId(roleId);
            persistedRole.setRoleCode("role-" + roleId);
            persistedRole.setRoleType(roleType);
            persistedRole.setRoleCompanyId(persistedRoleCompanyId);
        }

        doReturn(persistedRole).when(sysRoleService).getById(roleId);

        try (MockedStatic<LoginContext> loginContextMock = mockStatic(LoginContext.class)) {
            loginContextMock.when(LoginContext::me).thenReturn(loginUserApi);
            when(loginUserApi.getSuperAdminFlag()).thenReturn(false);
            when(loginUserApi.getCurrentUserCompanyId()).thenReturn(currentCompanyId);

            if (shouldThrow) {
                assertThrows(ServiceException.class, () -> sysRoleService.detail(request));
            } else {
                assertDoesNotThrow(() -> sysRoleService.detail(request));
            }
        }
    }

    private static Stream<org.junit.jupiter.params.provider.Arguments> roleDetailScenarios() {
        Long currentCompanyId = 100L;
        Long otherCompanyId = 200L;
        return Stream.of(
                org.junit.jupiter.params.provider.Arguments.of(10L, RoleTypeEnum.COMPANY_ROLE.getCode(), otherCompanyId, true),
                org.junit.jupiter.params.provider.Arguments.of(11L, RoleTypeEnum.COMPANY_ROLE.getCode(), currentCompanyId, false),
                org.junit.jupiter.params.provider.Arguments.of(1L, RoleTypeEnum.SYSTEM_ROLE.getCode(), null, false),
                org.junit.jupiter.params.provider.Arguments.of(999999L, RoleTypeEnum.COMPANY_ROLE.getCode(), null, true),
                org.junit.jupiter.params.provider.Arguments.of(null, RoleTypeEnum.COMPANY_ROLE.getCode(), null, true)
        );
    }
}
