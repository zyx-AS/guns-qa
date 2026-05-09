package cn.stylefeng.roses.kernel.file.modular.service.impl;

import cn.stylefeng.guns.testsupport.MybatisPlusLambdaMetadataSupport;
import cn.stylefeng.roses.kernel.file.api.FileInfoApi;
import cn.stylefeng.roses.kernel.file.api.pojo.response.SysFileInfoResponse;
import cn.stylefeng.roses.kernel.file.modular.entity.SysFileBusiness;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.stream.Stream;

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

    @ParameterizedTest
    @MethodSource("businessFileScopeCases")
    void shouldNotMixFilesFromDifferentBusinessCodesWhenBusinessIdsMatch(Long businessId, List<Long> expectedFileIds) {
        SysFileBusiness userBinding = new SysFileBusiness();
        userBinding.setBusinessCode("USER");
        userBinding.setBusinessId(1L);
        userBinding.setFileId(11L);

        SysFileBusiness roleBinding = new SysFileBusiness();
        roleBinding.setBusinessCode("ROLE");
        roleBinding.setBusinessId(1L);
        roleBinding.setFileId(22L);

        SysFileBusiness userBindingOtherId = new SysFileBusiness();
        userBindingOtherId.setBusinessCode("USER");
        userBindingOtherId.setBusinessId(2L);
        userBindingOtherId.setFileId(33L);

        SysFileBusiness blankCodeBinding = new SysFileBusiness();
        blankCodeBinding.setBusinessCode("");
        blankCodeBinding.setBusinessId(1L);
        blankCodeBinding.setFileId(44L);

        SysFileBusiness orderBinding = new SysFileBusiness();
        orderBinding.setBusinessCode("ORDER");
        orderBinding.setBusinessId(1L);
        orderBinding.setFileId(55L);

        SysFileInfoResponse userFile = new SysFileInfoResponse();
        userFile.setFileId(11L);
        userFile.setFileOriginName("user-avatar.png");

        SysFileInfoResponse roleFile = new SysFileInfoResponse();
        roleFile.setFileId(22L);
        roleFile.setFileOriginName("role-policy.pdf");

        SysFileInfoResponse userFileOtherId = new SysFileInfoResponse();
        userFileOtherId.setFileId(33L);
        userFileOtherId.setFileOriginName("user-signature.png");

        SysFileInfoResponse blankCodeFile = new SysFileInfoResponse();
        blankCodeFile.setFileId(44L);
        blankCodeFile.setFileOriginName("blank-code.txt");

        SysFileInfoResponse orderFile = new SysFileInfoResponse();
        orderFile.setFileId(55L);
        orderFile.setFileOriginName("order.pdf");

        when(fileInfoApi.getFileInfoWithoutContent(11L)).thenReturn(userFile);
        when(fileInfoApi.getFileInfoWithoutContent(22L)).thenReturn(roleFile);
        when(fileInfoApi.getFileInfoWithoutContent(33L)).thenReturn(userFileOtherId);
        when(fileInfoApi.getFileInfoWithoutContent(44L)).thenReturn(blankCodeFile);
        when(fileInfoApi.getFileInfoWithoutContent(55L)).thenReturn(orderFile);

        doReturn(List.of(userBinding, roleBinding, userBindingOtherId, blankCodeBinding, orderBinding))
                .when(sysFileBusinessService)
                .list(any(Wrapper.class));

        List<SysFileInfoResponse> results = sysFileBusinessService.getBusinessFileInfoList(businessId);

        assertEquals(expectedFileIds.size(), results.size(), "business file query should not bleed across scope boundaries");
        assertEquals(expectedFileIds, results.stream().map(SysFileInfoResponse::getFileId).toList());
    }

    private static Stream<org.junit.jupiter.params.provider.Arguments> businessFileScopeCases() {
        return Stream.of(
                org.junit.jupiter.params.provider.Arguments.of(1L, List.of(11L)),
                org.junit.jupiter.params.provider.Arguments.of(2L, List.of(33L)),
                org.junit.jupiter.params.provider.Arguments.of(-1L, List.of()),
                org.junit.jupiter.params.provider.Arguments.of(null, List.of())
        );
    }
}
