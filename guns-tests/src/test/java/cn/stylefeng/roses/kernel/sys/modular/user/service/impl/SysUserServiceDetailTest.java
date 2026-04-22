package cn.stylefeng.roses.kernel.sys.modular.user.service.impl;

import cn.stylefeng.roses.kernel.rule.exception.base.ServiceException;
import cn.stylefeng.roses.kernel.sys.modular.user.entity.SysUser;
import cn.stylefeng.roses.kernel.sys.modular.user.enums.SysUserExceptionEnum;
import cn.stylefeng.roses.kernel.sys.modular.user.pojo.request.SysUserRequest;
import com.baomidou.mybatisplus.core.MybatisConfiguration;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.metadata.TableInfo;
import com.baomidou.mybatisplus.core.metadata.TableInfoHelper;
import com.baomidou.mybatisplus.core.toolkit.LambdaUtils;
import org.apache.ibatis.builder.MapperBuilderAssistant;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doReturn;

@ExtendWith(MockitoExtension.class)
class SysUserServiceDetailTest {

    @BeforeAll
    static void initMybatisPlusMetadata() {
        TableInfo tableInfo = TableInfoHelper.getTableInfo(SysUser.class);
        if (tableInfo == null) {
            tableInfo = TableInfoHelper.initTableInfo(
                    new MapperBuilderAssistant(new MybatisConfiguration(), "test-resource"),
                    SysUser.class
            );
        }
        LambdaUtils.installCache(tableInfo);
    }

    @Spy
    @InjectMocks
    private SysUserServiceImpl sysUserService;

    @Test
    void shouldThrowBusinessExceptionWhenUserDoesNotExist() {
        SysUserRequest request = new SysUserRequest();
        request.setUserId(999999L);

        doReturn(null).when(sysUserService).getOne(any(Wrapper.class), eq(false));

        ServiceException exception = assertThrows(
                ServiceException.class,
                () -> sysUserService.detail(request)
        );

        assertEquals(SysUserExceptionEnum.SYS_USER_NOT_EXISTED.getErrorCode(), exception.getErrorCode());
        assertEquals(SysUserExceptionEnum.SYS_USER_NOT_EXISTED.getUserTip(), exception.getUserTip());
    }
}
