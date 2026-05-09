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
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class SysRoleServiceEditCrossCompanyRoleTest {

    @Mock
    private CacheOperatorApi<String> roleNameCache;

    @Mock
    private LoginUserApi loginUserApi;

    @Spy
    @InjectMocks
    private SysRoleServiceImpl sysRoleService;

    @ParameterizedTest
    @MethodSource("editRoleScenarios")
    void shouldRejectEditingOtherCompanyRoleForNonSuperAdmin(
            Long roleId,
            Long requestRoleCompanyId,
            Long persistedRoleCompanyId,
            boolean superAdmin,
            boolean shouldThrow
    ) {
        Long currentCompanyId = 100L;
        Long otherCompanyId = 200L;

        SysRoleRequest request = new SysRoleRequest();
        request.setRoleId(roleId);
        request.setRoleCode("company-role-b");
        request.setRoleType(RoleTypeEnum.COMPANY_ROLE.getCode());
        request.setRoleCompanyId(requestRoleCompanyId);

        SysRole persistedRole = null;
        if (persistedRoleCompanyId != null || Long.valueOf(999999L).equals(roleId) == false) {
            persistedRole = new SysRole();
            persistedRole.setRoleId(roleId);
            persistedRole.setRoleCode("company-role-b");
            persistedRole.setRoleType(RoleTypeEnum.COMPANY_ROLE.getCode());
            persistedRole.setRoleCompanyId(persistedRoleCompanyId);
        }

        doReturn(persistedRole).when(sysRoleService).getById(roleId);
        doReturn(Boolean.TRUE).when(sysRoleService).updateById(any(SysRole.class));

        try (MockedStatic<LoginContext> loginContextMock = mockStatic(LoginContext.class)) {
            loginContextMock.when(LoginContext::me).thenReturn(loginUserApi);
            when(loginUserApi.getSuperAdminFlag()).thenReturn(superAdmin);
            when(loginUserApi.getCurrentUserCompanyId()).thenReturn(currentCompanyId);

            if (shouldThrow) {
                assertThrows(ServiceException.class, () -> sysRoleService.edit(request));
            } else {
                assertDoesNotThrow(() -> sysRoleService.edit(request));
            }
        }
    }

    private static Stream<org.junit.jupiter.params.provider.Arguments> editRoleScenarios() {
        Long currentCompanyId = 100L;
        Long otherCompanyId = 200L;
        return Stream.of(
                org.junit.jupiter.params.provider.Arguments.of(10L, currentCompanyId, otherCompanyId, false, true),
                org.junit.jupiter.params.provider.Arguments.of(10L, otherCompanyId, otherCompanyId, false, true),
                org.junit.jupiter.params.provider.Arguments.of(10L, null, otherCompanyId, false, true),
                org.junit.jupiter.params.provider.Arguments.of(999999L, currentCompanyId, null, false, true),
                org.junit.jupiter.params.provider.Arguments.of(10L, currentCompanyId, otherCompanyId, true, false)
        );
    }
}
