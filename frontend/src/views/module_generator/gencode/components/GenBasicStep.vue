<template>
  <el-form ref="formRef" class="gen-basic-step" :model="info" :rules="rules" label-width="120px">
    <!-- 顶部：对照 + 生成回显（各一块） -->
    <el-row :gutter="12" class="mb-3">
      <el-col :span="8">
        <el-card shadow="never" class="gen-compare-card">
          <div class="gen-compare-card__title">对照（写入本地时）</div>
          <div class="gen-compare-card__body">
            <div class="gen-compare-row">
              <div class="gen-compare-row__k">有上级</div>
              <div class="gen-compare-row__v">侧栏：上级 → 短包名 → 菜单 → 按钮</div>
            </div>
            <div class="gen-compare-row">
              <div class="gen-compare-row__k">路由</div>
              <div class="gen-compare-row__v"><code>/包名/模块/业务?</code></div>
            </div>
            <div class="gen-compare-row">
              <div class="gen-compare-row__k">API</div>
              <div class="gen-compare-row__v">
                <code>{{ apiPathPreview }}</code>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card shadow="never" class="gen-echo-card">
          <div class="gen-echo-card__title">生成回显 / 生成文件路径</div>
          <div class="gen-echo-grid">
            <div class="gen-echo-item">
              <div class="gen-echo-item__k">后端目录</div>
              <code class="gen-echo-item__v">{{ backendDirPreview }}</code>
            </div>
            <div class="gen-echo-item">
              <div class="gen-echo-item__k">API</div>
              <code class="gen-echo-item__v">{{ apiPathPreview }}</code>
            </div>
            <div class="gen-echo-item">
              <div class="gen-echo-item__k">权限前缀</div>
              <code class="gen-echo-item__v">{{ permissionPrefixPreview }}</code>
            </div>
            <div class="gen-echo-item">
              <div class="gen-echo-item__k">后端路径</div>
              <code class="gen-echo-item__v">{{ backendModuleDirPreview }}</code>
            </div>
            <div class="gen-echo-item">
              <div class="gen-echo-item__k">前端视图路径</div>
              <code class="gen-echo-item__v">{{ frontendViewDirPreview }}</code>
            </div>
            <div class="gen-echo-item">
              <div class="gen-echo-item__k">前端 API 文件</div>
              <code class="gen-echo-item__v">{{ frontendApiFilePreview }}</code>
            </div>
          </div>
          <div
            v-if="info.sub_table_name && info.sub_table_fk_name && !info.master_sub_hint"
            class="gen-echo-warn"
          >
            将额外生成子表代码（不创建子表菜单）
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="gen-layout-row">
      <el-col :span="24" class="gen-layout-left">
        <el-card shadow="never" class="gen-form-card">
          <template #header>
            <div class="gen-form-card__header">
              <span class="font-medium">基础信息</span>
              <span class="gen-form-card__hint">切换步骤会先保存当前页</span>
            </div>
          </template>
          <el-row :gutter="16">
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
            <el-col :span="12">
              <el-form-item label="实体类名称" prop="class_name">
                <el-input v-model="info.class_name" placeholder="请输入" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item prop="package_name">
                <template #label>
                  包名
                  <el-tooltip
                    content="插件包名（plugin 顶层目录）。三段式示例：module_example"
                    placement="top"
                  >
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>
                <div class="gen-package-row">
                  <el-input
                    v-model="info.package_name"
                    class="gen-package-row__input"
                    placeholder="例如 module_example"
                    clearable
                  />
                  <el-tooltip
                    content="优先用模块名生成 module_模块名；未填模块名时按表名推导（去掉 gen_/tb_ 前缀后转合法目录名）"
                    placement="top"
                  >
                    <el-button type="primary" plain @click="applySuggestedPackageName">
                      生成包名
                    </el-button>
                  </el-tooltip>
                </div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item prop="module_name">
                <template #label>
                  模块名
                  <el-tooltip content="包名下第二层目录。示例：demo / gen_demo02" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>
                <el-input v-model="info.module_name" placeholder="例如 demo" clearable />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item prop="business_name">
                <template #label>
                  业务名
                  <el-tooltip
                    content="模块下第三层目录（可为空）。示例：demo01；留空表示仅到模块目录"
                    placement="top"
                  >
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>
                <el-input
                  v-model="info.business_name"
                  placeholder="例如 demo01（可留空）"
                  clearable
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item prop="function_name">
                <template #label>
                  功能名
                  <el-tooltip content="写入本地时作为菜单名称，例如 用户管理" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>
                <el-input v-model="info.function_name" placeholder="例如 用户管理" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item>
                <template #label>
                  上级菜单
                  <el-tooltip content="仅可选目录；留空则在侧栏根下创建模块目录" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>
                <el-tree-select
                  v-model="info.parent_menu_id"
                  :data="menuOptions"
                  placeholder="不选=根目录下挂模块目录；选=挂到该目录下"
                  check-strictly
                  filterable
                  default-expand-all
                  :render-after-expand="false"
                  clearable
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="24">
              <el-form-item label="备注" prop="description">
                <el-input v-model="info.description" type="textarea" :rows="3"></el-input>
              </el-form-item>
            </el-col>
            <el-col :span="24">
              <el-card shadow="never" class="master-sub-card mb-4">
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
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </el-form>
</template>

<script setup lang="ts">
import { computed, inject, onUnmounted, ref, watch } from "vue";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";
import { QuestionFilled } from "@element-plus/icons-vue";
import type { GenTableSchema } from "@/api/module_generator/gencode";
import { GENCODE_BASIC_FORM_KEY } from "../gencodeInjectionKeys";

defineOptions({ name: "GenBasicStep" });

const props = defineProps<{
  info: GenTableSchema;
  rules: FormRules;
  menuOptions: OptionType[];
}>();

type GenMode = "example" | "legacy";

const genMode = computed<GenMode>(() => {
  const pkg = (props.info.package_name || "").trim();
  const mod = (props.info.module_name || "").trim();
  if (pkg.startsWith("module_") && mod && !mod.startsWith("module_")) return "example";
  return "legacy";
});

function apiRoutePrefix(name: string): string {
  const n = (name || "").trim();
  if (!n) return "";
  return n.startsWith("module_") ? n.slice(7) : n;
}

const backendDirPreview = computed(() => {
  const pkg = (props.info.package_name || "").trim();
  const mod = (props.info.module_name || "").trim();
  const biz = (props.info.business_name || "").trim();
  if (genMode.value === "example")
    return `backend/app/plugin/${pkg}/${mod}${biz ? `/${biz}` : ""}/`;
  return `backend/app/plugin/${mod}/${biz}/`;
});

const apiPathPreview = computed(() => {
  const pkg = (props.info.package_name || "").trim();
  const mod = (props.info.module_name || "").trim();
  const biz = (props.info.business_name || "").trim();
  if (genMode.value === "example")
    return `/${apiRoutePrefix(pkg)}/${mod}${biz ? `/${biz.toLowerCase()}` : ""}`;
  return `/${apiRoutePrefix(mod)}/${biz.toLowerCase()}`;
});

const permissionPrefixPreview = computed(() => {
  const pkg = (props.info.package_name || "").trim();
  const mod = (props.info.module_name || "").trim();
  const biz = (props.info.business_name || "").trim();
  if (genMode.value === "example") {
    const segs = [pkg, mod, ...biz.split("/").filter(Boolean)];
    return segs.filter(Boolean).join(":");
  }
  const b = biz.replaceAll("/", ":");
  return b ? `${mod}:${b}` : mod;
});

const backendModuleDirPreview = computed(() => {
  const pkg = (props.info.package_name || "").trim();
  const mod = (props.info.module_name || "").trim();
  const biz = (props.info.business_name || "").trim();
  return `backend/app/plugin/${pkg}/${mod}${biz ? `/${biz}` : ""}/`;
});

const frontendViewDirPreview = computed(() => {
  const pkg = (props.info.package_name || "").trim();
  const mod = (props.info.module_name || "").trim();
  const biz = (props.info.business_name || "").trim();
  return `frontend/src/views/${pkg}/${mod}${biz ? `/${biz}` : ""}/`;
});

const frontendApiFilePreview = computed(() => {
  const pkg = (props.info.package_name || "").trim();
  const mod = (props.info.module_name || "").trim();
  const biz = (props.info.business_name || "").trim();
  if (biz) return `frontend/src/api/${pkg}/${biz}/${biz}.ts`;
  return `frontend/src/api/${pkg}/${mod}.ts`;
});

const emit = defineEmits<{
  "clear-master-sub": [];
  "master-sub-blur": [];
}>();

const formRef = ref<FormInstance>();
const injected = inject(GENCODE_BASIC_FORM_KEY, undefined);

/** 表名 → 合法目录片段（小写、下划线），用于无模块名时推导包名 */
function slugFromTableName(table: string): string {
  let s = table.trim().toLowerCase();
  if (!s) return "";
  if (s.startsWith("gen_")) s = s.slice(4);
  else if (s.startsWith("tb_")) s = s.slice(3);
  s = s
    .replace(/[^a-z0-9_]/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_|_$/g, "");
  return s || "table";
}

/** 生成包名：有模块名 → module_模块名；否则 → module_<表名推导> */
function suggestedPackageName(): string {
  const mod = (props.info.module_name || "").trim();
  if (mod) return mod.startsWith("module_") ? mod : `module_${mod}`;
  const tn = (props.info.table_name || "").trim();
  if (!tn) return "";
  const slug = slugFromTableName(tn);
  return slug ? `module_${slug}` : "";
}

function applySuggestedPackageName() {
  const next = suggestedPackageName();
  if (next) {
    props.info.package_name = next;
    ElMessage.success("已填入包名");
  } else {
    ElMessage.warning("请先填写模块名或表名称");
  }
}

watch(
  () => [props.info.parent_menu_id, props.info.module_name, props.info.table_name] as const,
  () => {
    if (props.info.parent_menu_id != null) return;
    const current = (props.info.package_name || "").trim();
    if (current && current !== "gencode" && current !== "module_gencode") return;
    const next = suggestedPackageName();
    if (next) props.info.package_name = next;
  },
  { immediate: true }
);

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
.gen-basic-step {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.gen-basic-step :deep(.el-col) {
  min-width: 0;
}

.gen-basic-step :deep(.el-form-item__content) {
  min-width: 0;
}

.gen-basic-step :deep(.el-input-group) {
  width: 100%;
  max-width: 100%;
  min-width: 0;
}

.gen-package-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-width: 0;
}

.gen-package-row__input {
  flex: 1;
  min-width: 0;
}

.master-sub-card {
  border: 1px solid var(--el-border-color-lighter);
}

.master-sub-card :deep(.el-card__header) {
  padding: 8px 10px;
}

.master-sub-card :deep(.el-card__body) {
  padding: 10px;
}

.gen-form-card {
  border: 1px solid var(--el-border-color-lighter);
  overflow-x: hidden;
}

.gen-form-card :deep(.el-card__body) {
  overflow-x: hidden;
}

.gen-form-card__header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.gen-form-card__hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.gen-compare-card,
.gen-echo-card {
  border: 1px solid var(--el-border-color-lighter);
}

.gen-compare-card__title,
.gen-echo-card__title {
  padding: 6px 8px;
  font-size: 11px;
  font-weight: 600;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
}

.gen-compare-card__body,
.gen-echo-card :deep(.el-card__body) {
  padding: 6px 8px;
}

.gen-compare-row {
  display: grid;
  grid-template-columns: 52px 1fr;
  gap: 8px;
  font-size: 11px;
  margin-bottom: 4px;
}

.gen-compare-row:last-child {
  margin-bottom: 0;
}

.gen-compare-row__k {
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.gen-compare-row__v {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gen-echo-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  padding: 6px 8px;
}

.gen-echo-item__k {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin-bottom: 2px;
  white-space: nowrap;
}

.gen-echo-item__v {
  display: block;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  background: var(--el-fill-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gen-echo-warn {
  padding: 0 8px 6px;
  font-size: 11px;
  color: var(--el-color-warning);
}
</style>
