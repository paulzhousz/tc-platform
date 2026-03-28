<template>
  <EnhancedDialog
    v-model="visible"
    title="创建表"
    width="min(920px, 96vw)"
    append-to-body
    @opened="onDialogOpened"
  >
    <div class="create-table-toolbar mb-3 flex flex-wrap items-center gap-2">
      <span class="text-sm text-[var(--el-text-color-regular)] shrink-0">编辑方式</span>
      <el-radio-group v-model="editMode" size="small">
        <el-radio-button value="sql">SQL 语句</el-radio-button>
        <el-radio-button value="visual">表结构</el-radio-button>
      </el-radio-group>
      <el-divider direction="vertical" class="!mx-1" />
      <span class="text-xs text-[var(--el-text-color-secondary)]">
        表结构模式通过表单生成 DDL；SQL 模式可直接粘贴。支持多条语句。
      </span>
    </div>

    <div v-show="editMode === 'sql'" class="sql-pane">
      <div class="mb-2 flex flex-wrap items-center gap-2">
        <span class="text-sm shrink-0">快速示例</span>
        <el-button type="primary" size="small" @click="loadPresetSql('single', 'mysql')">
          单表 · MySQL
        </el-button>
        <el-button type="primary" size="small" @click="loadPresetSql('single', 'postgres')">
          单表 · PostgreSQL
        </el-button>
        <el-button type="success" size="small" @click="loadPresetSql('masterSub', 'mysql')">
          主子表 · MySQL
        </el-button>
        <el-button type="success" size="small" @click="loadPresetSql('masterSub', 'postgres')">
          主子表 · PostgreSQL
        </el-button>
        <el-dropdown trigger="click">
          <el-button size="small" type="warning">
            旧版示例（含用户外键）
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="sqlText = LEGACY_MYSQL_WITH_USER_FK">
                MySQL（需 sys_user）
              </el-dropdown-item>
              <el-dropdown-item @click="sqlText = LEGACY_POSTGRES_WITH_USER_FK">
                PostgreSQL（需 sys_user）
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      <el-scrollbar max-height="72vh">
        <div class="absolute z-36 right-5 top-2">
          <el-link type="primary" @click="copySql">
            <el-icon><CopyDocument /></el-icon>
            复制
          </el-link>
        </div>
        <Codemirror
          ref="sqlRef"
          v-model:value="sqlText"
          :options="sqlOptions"
          border
          height="400px"
          width="100%"
        />
      </el-scrollbar>
    </div>

    <div v-show="editMode === 'visual'" class="visual-pane">
      <el-form label-width="120px" class="max-w-3xl">
        <el-form-item label="数据库方言">
          <el-radio-group v-model="visual.dialect" size="small">
            <el-radio-button value="mysql">MySQL</el-radio-button>
            <el-radio-button value="postgres">PostgreSQL</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="模板">
          <el-button @click="applyVisualPreset('single')">单表模板</el-button>
          <el-button type="primary" @click="applyVisualPreset('masterSub')">主子表模板</el-button>
        </el-form-item>
        <el-divider content-position="left">主表</el-divider>
        <el-form-item label="表名">
          <el-input
            v-model="visual.mainTableName"
            placeholder="如 gen_demo_order_master"
            clearable
          />
        </el-form-item>
        <el-form-item label="表注释">
          <el-input v-model="visual.mainComment" placeholder="表注释" clearable />
        </el-form-item>
        <el-form-item label="启用子表">
          <el-switch v-model="visual.subEnabled" @change="onSubToggle" />
        </el-form-item>
        <template v-if="visual.subEnabled">
          <el-divider content-position="left">子表</el-divider>
          <el-form-item label="表名">
            <el-input
              v-model="visual.subTableName"
              placeholder="如 gen_demo_order_item"
              clearable
            />
          </el-form-item>
          <el-form-item label="表注释">
            <el-input v-model="visual.subComment" placeholder="表注释" clearable />
          </el-form-item>
          <el-form-item label="外键列名">
            <el-input
              v-model="visual.fkColumn"
              placeholder="子表上指向主表的列，如 order_id"
              clearable
            />
          </el-form-item>
          <el-form-item label="引用主表列">
            <el-input v-model="visual.fkRefColumn" placeholder="一般为 id" clearable />
          </el-form-item>
        </template>
        <el-form-item>
          <el-button type="primary" @click="syncVisualToSql">生成 SQL 并切到 SQL 模式</el-button>
          <el-button @click="previewSqlInPlace">仅预览 SQL（下方）</el-button>
        </el-form-item>
      </el-form>
      <el-input
        v-model="visualPreviewSql"
        type="textarea"
        :rows="12"
        readonly
        class="font-mono text-xs"
        placeholder="点击「仅预览 SQL」或切换模式时生成"
      />
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button type="primary" :loading="loading" @click="handleConfirm">确 定</el-button>
        <el-button @click="handleCancel">取 消</el-button>
      </div>
    </template>
  </EnhancedDialog>
</template>

<script setup lang="ts">
import "codemirror/mode/sql/sql.js";
import "codemirror/theme/dracula.css";
import { ref, watch, nextTick } from "vue";
import Codemirror from "codemirror-editor-vue3";
import type { EditorConfiguration } from "codemirror";
import type { CmComponentRef } from "codemirror-editor-vue3";
import { ElMessage } from "element-plus";
import { ArrowDown, CopyDocument } from "@element-plus/icons-vue";
import { useClipboard } from "@vueuse/core";
import EnhancedDialog from "@/components/CURD/EnhancedDialog.vue";
import { useSettingsStore } from "@/store";
import { ThemeMode } from "@/enums/settings/theme.enum";
import { buildSqlFromVisual } from "../utils/buildCreateTableSql";
import type { SqlDialect, VisualBuildState } from "../utils/buildCreateTableSql";
import {
  applySubColumns,
  mergeGenTableLinkIntoVisual,
  visualPresetMasterSub,
  visualPresetSingle,
  type GenTableCreateLink,
} from "../utils/createTableVisualPresets";
import {
  getExampleFromPresetMasterSub,
  getExampleFromPresetSingle,
  LEGACY_MYSQL_WITH_USER_FK,
  LEGACY_POSTGRES_WITH_USER_FK,
} from "../utils/createTableSqlExamples";

defineOptions({ name: "CreateTableDialog" });

const visible = defineModel<boolean>({ default: false });

export interface CreateTableSubmitMeta {
  fromVisual: boolean;
  visualSnapshot?: VisualBuildState;
}

const props = withDefaults(
  defineProps<{
    loading?: boolean;
    /** 代码生成抽屉第三步打开时传入，用于预填「表结构」主/子表名 */
    linkFromGen?: GenTableCreateLink | null;
  }>(),
  { loading: false, linkFromGen: null }
);

const emit = defineEmits<{
  submit: [sql: string, meta?: CreateTableSubmitMeta];
}>();

const { copy } = useClipboard();
const settingsStore = useSettingsStore();

const editMode = ref<"sql" | "visual">("sql");
const sqlText = ref("");
const sqlRef = ref<CmComponentRef>();
const visual = ref<VisualBuildState>(visualPresetSingle("mysql"));
const visualPreviewSql = ref("");

const codeTheme = ref(settingsStore.theme === ThemeMode.DARK ? "dracula" : "default");

const sqlOptions: EditorConfiguration = {
  mode: "text/x-sql",
  lineNumbers: true,
  smartIndent: true,
  indentUnit: 2,
  tabSize: 2,
  readOnly: false,
  theme: codeTheme.value,
  lineWrapping: true,
  autofocus: false,
};

watch(
  () => settingsStore.theme,
  (t) => {
    const newTheme = t === ThemeMode.DARK ? "dracula" : "default";
    codeTheme.value = newTheme;
    sqlOptions.theme = newTheme;
    if (sqlRef.value?.cminstance) {
      sqlRef.value.cminstance.setOption("theme", newTheme);
    }
  }
);

function onDialogOpened() {
  dialectWatchSkip = true;
  editMode.value = "sql";
  sqlText.value = "";
  visual.value = visualPresetSingle("mysql");
  visualPreviewSql.value = "";
  void nextTick(() => {
    dialectWatchSkip = false;
    applyLinkFromGenIfAny();
  });
}

/** 第三步已填主表/子表时：切到表结构模式并带入名称，减少重复输入 */
function applyLinkFromGenIfAny() {
  const link = props.linkFromGen;
  if (!link) return;
  const touched =
    (link.table_name || "").trim() ||
    (link.table_comment || "").trim() ||
    ((link.sub_table_name || "").trim() && (link.sub_table_fk_name || "").trim());
  if (!touched) return;
  visual.value = mergeGenTableLinkIntoVisual(link, visual.value.dialect);
  editMode.value = "visual";
  visualPreviewSql.value = buildSqlFromVisual(applySubColumns(visual.value));
  ElMessage.info({
    message: "已从代码生成第三步带入主表/子表名，可在表结构模式中修改后执行创建",
    duration: 3200,
  });
}

watch(editMode, (m) => {
  if (m === "sql") {
    sqlText.value = buildSqlFromVisual(applySubColumns(visual.value));
    void nextTick(() => sqlRef.value?.cminstance?.refresh());
  } else {
    visualPreviewSql.value = buildSqlFromVisual(applySubColumns(visual.value));
  }
});

let dialectWatchSkip = false;
watch(
  () => visual.value.dialect,
  (_d, prev) => {
    if (dialectWatchSkip) return;
    if (prev === undefined) return;
    const d = visual.value.dialect;
    visual.value = visual.value.subEnabled
      ? applySubColumns(visualPresetMasterSub(d))
      : visualPresetSingle(d);
    visualPreviewSql.value = buildSqlFromVisual(applySubColumns(visual.value));
  }
);

function onSubToggle() {
  visual.value = applySubColumns(visual.value);
  visualPreviewSql.value = buildSqlFromVisual(applySubColumns(visual.value));
}

function applyVisualPreset(kind: "single" | "masterSub") {
  const d = visual.value.dialect;
  visual.value =
    kind === "single" ? visualPresetSingle(d) : applySubColumns(visualPresetMasterSub(d));
  visualPreviewSql.value = buildSqlFromVisual(applySubColumns(visual.value));
}

function syncVisualToSql() {
  sqlText.value = buildSqlFromVisual(applySubColumns(visual.value));
  editMode.value = "sql";
  void nextTick(() => {
    sqlRef.value?.cminstance?.refresh();
  });
  ElMessage.success("已生成 SQL，可在 SQL 模式中继续编辑");
}

function previewSqlInPlace() {
  visualPreviewSql.value = buildSqlFromVisual(applySubColumns(visual.value));
}

function loadPresetSql(kind: "single" | "masterSub", dialect: SqlDialect) {
  sqlText.value =
    kind === "single"
      ? getExampleFromPresetSingle(dialect)
      : getExampleFromPresetMasterSub(dialect);
}

function copySql() {
  if (!sqlText.value) {
    ElMessage.warning("没有可复制的内容");
    return;
  }
  copy(sqlText.value);
  ElMessage.success("已复制");
}

function handleConfirm() {
  const sql =
    editMode.value === "sql"
      ? sqlText.value.trim()
      : buildSqlFromVisual(applySubColumns(visual.value)).trim();
  if (!sql) {
    ElMessage.error("请填写 SQL，或在表结构中选择模板并生成");
    return;
  }
  if (editMode.value === "visual") {
    emit("submit", sql, {
      fromVisual: true,
      visualSnapshot: applySubColumns(visual.value),
    });
  } else {
    emit("submit", sql);
  }
}

function handleCancel() {
  visible.value = false;
}
</script>

<style scoped lang="scss">
.visual-pane :deep(.el-textarea__inner) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
</style>
