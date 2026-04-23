package cn.stylefeng.roses.kernel.sys.modular.role.service.impl;

import cn.stylefeng.roses.kernel.auth.api.LoginUserApi;
import cn.stylefeng.roses.kernel.auth.api.context.LoginContext;
import cn.stylefeng.roses.kernel.cache.api.CacheOperatorApi;
import cn.stylefeng.roses.kernel.rule.exception.base.ServiceException;
import cn.stylefeng.roses.kernel.sys.api.enums.role.RoleTypeEnum;
import cn.stylefeng.roses.kernel.sys.modular.role.entity.SysRole;
import cn.stylefeng.roses.kernel.sys.modular.role.pojo.request.SysRoleRequest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

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

    @Test
    void shouldRejectEditingOtherCompanyRoleForNonSuperAdmin() {
        Long currentCompanyId = 100L;
        Long otherCompanyId = 200L;

        SysRoleRequest request = new SysRoleRequest();
        request.setRoleId(10L);
        request.setRoleCode("company-role-b");
        request.setRoleType(RoleTypeEnum.COMPANY_ROLE.getCode());
        request.setRoleCompanyId(currentCompanyId);

        SysRole persistedRole = new SysRole();
        persistedRole.setRoleId(10L);
        persistedRole.setRoleCode("company-role-b");
        persistedRole.setRoleType(RoleTypeEnum.COMPANY_ROLE.getCode());
        persistedRole.setRoleCompanyId(otherCompanyId);

        doReturn(persistedRole).when(sysRoleService).getById(10L);
        doReturn(Boolean.TRUE).when(sysRoleService).updateById(any(SysRole.class));

        try (MockedStatic<LoginContext> loginContextMock = mockStatic(LoginContext.class)) {
            loginContextMock.when(LoginContext::me).thenReturn(loginUserApi);
            when(loginUserApi.getSuperAdminFlag()).thenReturn(false);
            when(loginUserApi.getCurrentUserCompanyId()).thenReturn(currentCompanyId);

            assertThrows(ServiceException.class, () -> sysRoleService.edit(request));
        }
    }
}
