package cn.stylefeng.roses.kernel.file.modular.service.impl;

import cn.stylefeng.guns.testsupport.MybatisPlusLambdaMetadataSupport;
import cn.stylefeng.roses.kernel.file.api.FileInfoApi;
import cn.stylefeng.roses.kernel.file.api.pojo.response.SysFileInfoResponse;
import cn.stylefeng.roses.kernel.file.modular.entity.SysFileBusiness;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class SysFileBusinessServiceBusinessScopeIsolationTest {

    @BeforeAll
    static void initMybatisPlusMetadata() {
        MybatisPlusLambdaMetadataSupport.initEntityMetadata(SysFileBusiness.class);
    }

    @Mock
    private FileInfoApi fileInfoApi;

    @Spy
    @InjectMocks
    private SysFileBusinessServiceImpl sysFileBusinessService;

    @Test
    void shouldNotMixFilesFromDifferentBusinessCodesWhenBusinessIdsMatch() {
        SysFileBusiness userBinding = new SysFileBusiness();
        userBinding.setBusinessCode("USER");
        userBinding.setBusinessId(1L);
        userBinding.setFileId(11L);

        SysFileBusiness roleBinding = new SysFileBusiness();
        roleBinding.setBusinessCode("ROLE");
        roleBinding.setBusinessId(1L);
        roleBinding.setFileId(22L);

        SysFileInfoResponse userFile = new SysFileInfoResponse();
        userFile.setFileId(11L);
        userFile.setFileOriginName("user-avatar.png");

        SysFileInfoResponse roleFile = new SysFileInfoResponse();
        roleFile.setFileId(22L);
        roleFile.setFileOriginName("role-policy.pdf");

        when(fileInfoApi.getFileInfoWithoutContent(11L)).thenReturn(userFile);
        when(fileInfoApi.getFileInfoWithoutContent(22L)).thenReturn(roleFile);

        doReturn(List.of(userBinding, roleBinding)).when(sysFileBusinessService).list(any(Wrapper.class));

        List<SysFileInfoResponse> results = sysFileBusinessService.getBusinessFileInfoList(1L);

        assertEquals(1, results.size(), "same businessId under different businessCode values should not bleed together");
        assertEquals(11L, results.get(0).getFileId());
    }
}
