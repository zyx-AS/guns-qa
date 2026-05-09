package cn.stylefeng.roses.kernel.file.modular.service.impl;

import cn.stylefeng.guns.testsupport.MybatisPlusLambdaMetadataSupport;
import cn.stylefeng.roses.kernel.cache.api.CacheOperatorApi;
import cn.stylefeng.roses.kernel.file.api.enums.FileLocationEnum;
import cn.stylefeng.roses.kernel.file.api.enums.FileStatusEnum;
import cn.stylefeng.roses.kernel.file.api.exception.FileException;
import cn.stylefeng.roses.kernel.file.api.expander.FileConfigExpander;
import cn.stylefeng.roses.kernel.file.api.pojo.request.SysFileInfoRequest;
import cn.stylefeng.roses.kernel.file.api.pojo.response.SysFileInfoResponse;
import cn.stylefeng.roses.kernel.file.modular.entity.SysFileInfo;
import cn.stylefeng.roses.kernel.file.modular.service.SysFileStorageService;
import cn.stylefeng.roses.kernel.rule.enums.YesOrNotEnum;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.multipart.MultipartFile;

import java.nio.charset.StandardCharsets;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class SysFileInfoServiceUpdateFileStorageTest {

    @BeforeAll
    static void initMybatisPlusMetadata() {
        MybatisPlusLambdaMetadataSupport.initEntityMetadata(SysFileInfo.class);
    }

    @Mock
    private SysFileStorageService sysFileStorageService;

    @Mock
    private CacheOperatorApi<SysFileInfoResponse> fileInfoCache;

    @Spy
    @InjectMocks
    private SysFileInfoServiceImpl sysFileInfoService;

    @ParameterizedTest
    @MethodSource("updatedFilePayloads")
    void shouldPersistUpdatedBytesWhenCreatingNewFileVersion(byte[] updatedBytes) throws Exception {
        SysFileInfoRequest request = new SysFileInfoRequest();
        request.setFileCode(1001L);
        request.setFileLocation(FileLocationEnum.DB.getCode());
        request.setFileBucket("unit-test-bucket");
        request.setSecretFlag(YesOrNotEnum.N.getCode());

        MultipartFile multipartFile = mock(MultipartFile.class);
        when(multipartFile.getOriginalFilename()).thenReturn("contract.txt");
        when(multipartFile.getSize()).thenReturn((long) updatedBytes.length);
        when(multipartFile.getBytes()).thenReturn(updatedBytes);

        SysFileInfo oldFileInfo = new SysFileInfo();
        oldFileInfo.setFileId(501L);
        oldFileInfo.setFileCode(1001L);
        oldFileInfo.setFileVersion(1);
        oldFileInfo.setFileStatus(FileStatusEnum.NEW.getCode());
        oldFileInfo.setDelFlag(YesOrNotEnum.N.getCode());

        doReturn(oldFileInfo).when(sysFileInfoService).getOne(any());
        doReturn(Boolean.TRUE).when(sysFileInfoService).updateById(any(SysFileInfo.class));
        doReturn(Boolean.TRUE).when(sysFileInfoService).save(any(SysFileInfo.class));

        try (MockedStatic<FileConfigExpander> fileConfigMock = mockStatic(FileConfigExpander.class)) {
            fileConfigMock.when(FileConfigExpander::getDefaultBucket).thenReturn("default-bucket");

            sysFileInfoService.updateFile(multipartFile, request);
        }

        ArgumentCaptor<byte[]> fileBytesCaptor = ArgumentCaptor.forClass(byte[].class);
        verify(sysFileStorageService).saveFile(anyLong(), fileBytesCaptor.capture());
        org.junit.jupiter.api.Assertions.assertArrayEquals(updatedBytes, fileBytesCaptor.getValue());
    }

    @Test
    void shouldThrowWhenLatestFileVersionDoesNotExist() {
        SysFileInfoRequest request = new SysFileInfoRequest();
        request.setFileCode(999999L);
        request.setFileLocation(FileLocationEnum.DB.getCode());
        request.setFileBucket("unit-test-bucket");
        request.setSecretFlag(YesOrNotEnum.N.getCode());

        MultipartFile multipartFile = mock(MultipartFile.class);

        doReturn(null).when(sysFileInfoService).getOne(any());

        assertThrows(FileException.class, () -> sysFileInfoService.updateFile(multipartFile, request));
    }

    @Test
    void shouldPropagateStorageFailureWhenCreatingNewFileVersion() throws Exception {
        byte[] updatedBytes = "v2-data".getBytes(StandardCharsets.UTF_8);

        SysFileInfoRequest request = new SysFileInfoRequest();
        request.setFileCode(1001L);
        request.setFileLocation(FileLocationEnum.DB.getCode());
        request.setFileBucket("unit-test-bucket");
        request.setSecretFlag(YesOrNotEnum.N.getCode());

        MultipartFile multipartFile = mock(MultipartFile.class);
        when(multipartFile.getOriginalFilename()).thenReturn("contract.txt");
        when(multipartFile.getSize()).thenReturn((long) updatedBytes.length);
        when(multipartFile.getBytes()).thenReturn(updatedBytes);

        SysFileInfo oldFileInfo = new SysFileInfo();
        oldFileInfo.setFileId(501L);
        oldFileInfo.setFileCode(1001L);
        oldFileInfo.setFileVersion(1);
        oldFileInfo.setFileStatus(FileStatusEnum.NEW.getCode());
        oldFileInfo.setDelFlag(YesOrNotEnum.N.getCode());

        doReturn(oldFileInfo).when(sysFileInfoService).getOne(any());
        doReturn(Boolean.TRUE).when(sysFileInfoService).updateById(any(SysFileInfo.class));
        doReturn(Boolean.TRUE).when(sysFileInfoService).save(any(SysFileInfo.class));
        doThrow(new RuntimeException("storage down")).when(sysFileStorageService).saveFile(anyLong(), any(byte[].class));

        try (MockedStatic<FileConfigExpander> fileConfigMock = mockStatic(FileConfigExpander.class)) {
            fileConfigMock.when(FileConfigExpander::getDefaultBucket).thenReturn("default-bucket");

            assertThrows(RuntimeException.class, () -> sysFileInfoService.updateFile(multipartFile, request));
        }
    }

    private static Stream<byte[]> updatedFilePayloads() {
        return Stream.of("v2-data".getBytes(StandardCharsets.UTF_8), new byte[0]);
    }
}
