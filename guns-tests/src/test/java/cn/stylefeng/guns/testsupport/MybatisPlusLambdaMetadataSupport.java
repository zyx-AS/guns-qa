package cn.stylefeng.guns.testsupport;

import com.baomidou.mybatisplus.core.MybatisConfiguration;
import com.baomidou.mybatisplus.core.metadata.TableInfo;
import com.baomidou.mybatisplus.core.metadata.TableInfoHelper;
import com.baomidou.mybatisplus.core.toolkit.LambdaUtils;
import org.apache.ibatis.builder.MapperBuilderAssistant;

public final class MybatisPlusLambdaMetadataSupport {

    private MybatisPlusLambdaMetadataSupport() {
    }

    public static void initEntityMetadata(Class<?>... entityClasses) {
        for (Class<?> entityClass : entityClasses) {
            TableInfo tableInfo = TableInfoHelper.getTableInfo(entityClass);
            if (tableInfo == null) {
                tableInfo = TableInfoHelper.initTableInfo(
                        new MapperBuilderAssistant(new MybatisConfiguration(), "test-resource"),
                        entityClass
                );
            }
            LambdaUtils.installCache(tableInfo);
        }
    }
}
