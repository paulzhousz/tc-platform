<template>
  <el-form ref="formRef" :model="info" :rules="rules" label-width="150px">
    <el-row>
      <el-col :span="12">
        <el-form-item label="表名称" prop="table_name">
          <el-input v-model="info.table_name" placeholder="请输入表名称" />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item label="表描述" prop="table_comment">
          <el-input v-model="info.table_comment" placeholder="请输入表描述" />
        </el-form-item>
      </el-col>
      <el-col :span="24">
        <el-card shadow="never" class="master-sub-card mb-4">
          <template #header>
            <div class="flex flex-wrap items-center justify-between gap-2">
              <span class="font-medium">主子表（可选）</span>
              <el-button
                v-if="info.sub_table_name || info.sub_table_fk_name"
                text
                type="primary"
                size="small"
                @click="emit('clear-master-sub')"
              >
                清空主子表配置
              </el-button>
            </div>
          </template>
          <p class="mb-3 text-sm text-[var(--el-text-color-secondary)]">
            两项需同时填写或同时留空。保存后系统会从当前数据库读取子表结构；仅当子表已存在且外键列名正确时，预览与生成才会包含子表代码。
          </p>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item prop="sub_table_name">
                <template #label>
                  子表表名
                  <el-tooltip
                    content="数据库中已存在的物理表名，例如 gen_order_item"
                    placement="top"
                  >
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>
                <el-input
                  v-model="info.sub_table_name"
                  placeholder="与下栏同时填写，如 gen_order_item"
                  clearable
                  @blur="emit('master-sub-blur')"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item prop="sub_table_fk_name">
                <template #label>
                  子表外键列
                  <el-tooltip
                    content="子表中指向主表主键的列名，例如 order_id（类型需与主键匹配）"
                    placement="top"
                  >
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>
                <el-input
                  v-model="info.sub_table_fk_name"
                  placeholder="与上栏同时填写，如 order_id"
                  clearable
                  @blur="emit('master-sub-blur')"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-alert
            v-if="info.master_sub_hint"
            class="mt-1"
            type="warning"
            :closable="false"
            show-icon
            :title="info.master_sub_hint"
          />
          <el-alert
            v-else-if="info.sub && info.sub_table_name && info.sub_table_fk_name"
            class="mt-1"
            type="success"
            :closable="false"
            show-icon
            title="主子表结构已从数据库加载，预览与生成将包含子表代码。"
          />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-form-item label="实体类名称" prop="class_name">
          <el-input v-model="info.class_name" placeholder="请输入" />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item prop="package_name">
          <template #label>
            包名
            <el-tooltip content="生成在哪个python模块下，例如 module_gencode" placement="top">
              <el-icon><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-input v-model="info.package_name">
            <template #prepend>接口路径: api/v1/</template>
            <template #append>/{{ info.business_name }}</template>
          </el-input>
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item prop="module_name">
          <template #label>
            模块名
            <el-tooltip content="可理解为子系统名，例如 system" placement="top">
              <el-icon><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-input v-model="info.module_name" />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item prop="business_name">
          <template #label>
            业务名
            <el-tooltip content="可理解为功能英文名，例如 user" placement="top">
              <el-icon><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-input v-model="info.business_name" />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item prop="function_name">
          <template #label>
            功能名
            <el-tooltip content="用作类描述，例如 用户" placement="top">
              <el-icon><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-input v-model="info.function_name" />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item>
          <template #label>
            上级菜单
            <el-tooltip content="分配到指定菜单下，例如 系统管理" placement="top">
              <el-icon><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-tree-select
            v-model="info.parent_menu_id"
            :data="menuOptions"
            placeholder="请选择系统菜单,不选创建目录"
            check-strictly
            show-checkbox
            filterable
            :render-after-expand="false"
            clearable
          />
        </el-form-item>
      </el-col>
      <el-col :span="24">
        <el-form-item label="备注" prop="description">
          <el-input v-model="info.description" type="textarea" :rows="3"></el-input>
        </el-form-item>
      </el-col>

      <el-divider>生成文件路径</el-divider>
      <el-col
        v-if="info.sub_table_name && info.sub_table_fk_name && !info.master_sub_hint"
        :span="24"
        class="mb-2"
      >
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="将额外生成一套子表代码，目录名为子表表名（与主表共用模块名）。菜单仍只创建主表；子表路由需在插件中自行注册。"
        />
      </el-col>

      <el-col :span="24">
        <el-descriptions :column="2" border>
          <el-descriptions-item :label="info.function_name + '功能，后端控制层'">
            backend/app/plugin/{{ info.module_name }}/{{ info.business_name }}/controller.py
          </el-descriptions-item>
          <el-descriptions-item :label="info.function_name + '功能，后端业务层'">
            backend/app/plugin/{{ info.module_name }}/{{ info.business_name }}/service.py
          </el-descriptions-item>
          <el-descriptions-item :label="info.function_name + '功能，后端数据层'">
            backend/app/plugin/{{ info.module_name }}/{{ info.business_name }}/crud.py
          </el-descriptions-item>
          <el-descriptions-item :label="info.function_name + '功能，后端实体层'">
            backend/app/plugin/{{ info.module_name }}/{{ info.business_name }}/model.py
          </el-descriptions-item>
          <el-descriptions-item :label="info.function_name + '功能，后端序列化层'">
            backend/app/plugin/{{ info.module_name }}/{{ info.business_name }}/schema.py
          </el-descriptions-item>
          <el-descriptions-item :label="info.function_name + '功能，后端初始化'">
            backend/app/plugin/{{ info.module_name }}/{{ info.business_name }}/__init__.py
          </el-descriptions-item>
          <el-descriptions-item :label="info.function_name + '功能，前端接口层'">
            frontend/src/api/{{ info.module_name }}/{{ info.business_name }}.ts
          </el-descriptions-item>
          <el-descriptions-item :label="info.function_name + '功能，前端视图层'">
            frontend/src/views/{{ info.module_name }}/{{ info.business_name }}/index.vue
          </el-descriptions-item>
          <template v-if="info.sub_table_name && info.sub_table_fk_name">
            <el-descriptions-item label="子表 · 后端（示例）">
              backend/app/plugin/{{ info.module_name }}/{{ info.sub_table_name }}/
            </el-descriptions-item>
            <el-descriptions-item label="子表 · 前端（示例）">
              frontend/src/views/{{ info.module_name }}/{{ info.sub_table_name }}/index.vue
            </el-descriptions-item>
          </template>
        </el-descriptions>
      </el-col>
    </el-row>
  </el-form>
</template>

<script setup lang="ts">
import { inject, onUnmounted, ref, watch } from "vue";
import type { FormInstance, FormRules } from "element-plus";
import { QuestionFilled } from "@element-plus/icons-vue";
import type { GenTableSchema } from "@/api/module_generator/gencode";
import { GENCODE_BASIC_FORM_KEY } from "../gencodeInjectionKeys";

defineOptions({ name: "GenBasicStep" });

defineProps<{
  info: GenTableSchema;
  rules: FormRules;
  menuOptions: OptionType[];
}>();

const emit = defineEmits<{
  "clear-master-sub": [];
  "master-sub-blur": [];
}>();

const formRef = ref<FormInstance>();
const injected = inject(GENCODE_BASIC_FORM_KEY, undefined);

watch(
  formRef,
  (v) => {
    if (injected) injected.value = v;
  },
  { immediate: true }
);

onUnmounted(() => {
  if (injected) injected.value = undefined;
});
</script>

<style scoped lang="scss">
.master-sub-card {
  border: 1px solid var(--el-border-color-lighter);
}
</style>
