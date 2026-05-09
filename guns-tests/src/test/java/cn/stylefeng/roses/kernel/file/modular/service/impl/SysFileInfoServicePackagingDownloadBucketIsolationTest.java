package cn.stylefeng.roses.kernel.file.modular.service.impl;

import cn.stylefeng.roses.kernel.file.api.FileOperatorApi;
import cn.stylefeng.roses.kernel.file.api.exception.FileException;
import cn.stylefeng.roses.kernel.file.api.expander.FileConfigExpander;
import cn.stylefeng.roses.kernel.file.api.pojo.response.SysFileInfoResponse;
import cn.stylefeng.roses.kernel.rule.enums.YesOrNotEnum;
import org.junit.jupiter.api.Assertions;
import jakarta.servlet.ServletOutputStream;
import jakarta.servlet.WriteListener;
import jakarta.servlet.http.HttpServletResponse;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.ZipInputStream;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class SysFileInfoServicePackagingDownloadBucketIsolationTest {

    @Mock
    private FileOperatorApi fileOperatorApi;

    @Spy
    @InjectMocks
    private SysFileInfoServiceImpl sysFileInfoService;

    @ParameterizedTest
    @ValueSource(booleans = {false, true})
    void shouldReadEachPackagedFileFromItsOwnBucket(boolean includeThirdBucket) throws Exception {
        SysFileInfoResponse firstFile = new SysFileInfoResponse();
        firstFile.setFileId(11L);
        firstFile.setFileBucket("bucketA");
        firstFile.setFileObjectName("object-1");
        firstFile.setFileOriginName("first.txt");
        firstFile.setSecretFlag(YesOrNotEnum.N.getCode());

        SysFileInfoResponse secondFile = new SysFileInfoResponse();
        secondFile.setFileId(22L);
        secondFile.setFileBucket("bucketB");
        secondFile.setFileObjectName("object-2");
        secondFile.setFileOriginName("second.txt");
        secondFile.setSecretFlag(YesOrNotEnum.N.getCode());

        List<SysFileInfoResponse> files = new ArrayList<>();
        files.add(firstFile);
        files.add(secondFile);

        if (includeThirdBucket) {
            SysFileInfoResponse thirdFile = new SysFileInfoResponse();
            thirdFile.setFileId(33L);
            thirdFile.setFileBucket("bucketC");
            thirdFile.setFileObjectName("object-3");
            thirdFile.setFileOriginName("third.txt");
            thirdFile.setSecretFlag(YesOrNotEnum.N.getCode());
            files.add(thirdFile);
            when(fileOperatorApi.getFileBytes("bucketA", "object-3")).thenReturn("WRONG-C".getBytes(StandardCharsets.UTF_8));
            when(fileOperatorApi.getFileBytes("bucketC", "object-3")).thenReturn("C".getBytes(StandardCharsets.UTF_8));
        }

        doReturn(files).when(sysFileInfoService).getFileInfoListByFileIds(anyList());

        when(fileOperatorApi.getFileBytes("bucketA", "object-1")).thenReturn("A".getBytes(StandardCharsets.UTF_8));
        when(fileOperatorApi.getFileBytes("bucketA", "object-2")).thenReturn("WRONG".getBytes(StandardCharsets.UTF_8));
        when(fileOperatorApi.getFileBytes("bucketB", "object-2")).thenReturn("B".getBytes(StandardCharsets.UTF_8));

        HttpServletResponse response = mock(HttpServletResponse.class);
        when(response.getOutputStream()).thenReturn(new InMemoryServletOutputStream());

        try (MockedStatic<FileConfigExpander> fileConfigMock = mockStatic(FileConfigExpander.class)) {
            fileConfigMock.when(FileConfigExpander::getDefaultBucket).thenReturn("default-bucket");

            sysFileInfoService.packagingDownload("11,22", YesOrNotEnum.N.getCode(), response);
        }

        verify(fileOperatorApi).getFileBytes("bucketA", "object-1");
        verify(fileOperatorApi).getFileBytes("bucketB", "object-2");
        if (includeThirdBucket) {
            verify(fileOperatorApi).getFileBytes("bucketC", "object-3");
        }
    }

    @Test
    void shouldRejectSecretFlagMismatchDuringPackagingDownload() throws Exception {
        SysFileInfoResponse secretFile = new SysFileInfoResponse();
        secretFile.setFileId(11L);
        secretFile.setFileBucket("bucketA");
        secretFile.setFileObjectName("object-1");
        secretFile.setFileOriginName("secret.txt");
        secretFile.setSecretFlag(YesOrNotEnum.Y.getCode());

        doReturn(List.of(secretFile)).when(sysFileInfoService).getFileInfoListByFileIds(anyList());

        HttpServletResponse response = mock(HttpServletResponse.class);
        when(response.getOutputStream()).thenReturn(new InMemoryServletOutputStream());

        try (MockedStatic<FileConfigExpander> fileConfigMock = mockStatic(FileConfigExpander.class)) {
            fileConfigMock.when(FileConfigExpander::getDefaultBucket).thenReturn("default-bucket");

            assertThrows(
                    FileException.class,
                    () -> sysFileInfoService.packagingDownload("11", YesOrNotEnum.N.getCode(), response)
            );
        }
    }

    @Test
    void shouldKeepDuplicateFileNamesDistinctInZip() throws Exception {
        SysFileInfoResponse firstFile = new SysFileInfoResponse();
        firstFile.setFileId(11L);
        firstFile.setFileBucket("bucketA");
        firstFile.setFileObjectName("object-1");
        firstFile.setFileOriginName("duplicate.txt");
        firstFile.setSecretFlag(YesOrNotEnum.N.getCode());

        SysFileInfoResponse secondFile = new SysFileInfoResponse();
        secondFile.setFileId(22L);
        secondFile.setFileBucket("bucketA");
        secondFile.setFileObjectName("object-2");
        secondFile.setFileOriginName("duplicate.txt");
        secondFile.setSecretFlag(YesOrNotEnum.N.getCode());

        doReturn(List.of(firstFile, secondFile)).when(sysFileInfoService).getFileInfoListByFileIds(anyList());
        when(fileOperatorApi.getFileBytes("bucketA", "object-1")).thenReturn("A".getBytes(StandardCharsets.UTF_8));
        when(fileOperatorApi.getFileBytes("bucketA", "object-2")).thenReturn("B".getBytes(StandardCharsets.UTF_8));

        InMemoryServletOutputStream outputStream = new InMemoryServletOutputStream();
        HttpServletResponse response = mock(HttpServletResponse.class);
        when(response.getOutputStream()).thenReturn(outputStream);

        try (MockedStatic<FileConfigExpander> fileConfigMock = mockStatic(FileConfigExpander.class)) {
            fileConfigMock.when(FileConfigExpander::getDefaultBucket).thenReturn("default-bucket");

            sysFileInfoService.packagingDownload("11,22", YesOrNotEnum.N.getCode(), response);
        }

        List<String> entryNames = new ArrayList<>();
        try (ZipInputStream zipInputStream = new ZipInputStream(new ByteArrayInputStream(outputStream.toByteArray()))) {
            java.util.zip.ZipEntry entry;
            while ((entry = zipInputStream.getNextEntry()) != null) {
                entryNames.add(entry.getName());
            }
        }

        Assertions.assertEquals(List.of("1-duplicate.txt", "2-duplicate.txt"), entryNames);
    }

    private static final class InMemoryServletOutputStream extends ServletOutputStream {

        private final ByteArrayOutputStream delegate = new ByteArrayOutputStream();

        @Override
        public void write(int b) throws IOException {
            delegate.write(b);
        }

        @Override
        public boolean isReady() {
            return true;
        }

        @Override
        public void setWriteListener(WriteListener writeListener) {
        }

        private byte[] toByteArray() {
            return delegate.toByteArray();
        }
    }
}
