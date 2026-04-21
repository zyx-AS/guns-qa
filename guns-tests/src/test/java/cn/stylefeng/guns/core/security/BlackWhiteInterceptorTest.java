package cn.stylefeng.guns.core.security;

import cn.stylefeng.roses.kernel.security.blackwhite.BlackWhiteValidateService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.verify;

@ExtendWith(MockitoExtension.class)
class BlackWhiteInterceptorTest {

    @Mock
    private BlackWhiteValidateService blackWhiteValidateService;

    @InjectMocks
    private BlackWhiteInterceptor blackWhiteInterceptor;

    @Test
    void shouldValidateClientIpBeforeRequestPassesThrough() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr("127.0.0.1");
        MockHttpServletResponse response = new MockHttpServletResponse();

        boolean result = blackWhiteInterceptor.preHandle(request, response, new Object());

        assertTrue(result);
        verify(blackWhiteValidateService).totalValidate("127.0.0.1");
    }
}
