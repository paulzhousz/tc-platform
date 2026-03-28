<template>
  <EnhancedDrawer
    v-model="drawerVisible"
    :title="'【代码生成】' + info.table_name"
    size="85%"
    append-to-body
    @close="emit('close')"
  >
    <el-steps :active="activeStep" finish-status="success" simple>
      <el-step title="基础配置" />
      <el-step title="字段配置" />
      <el-step title="预览代码" />
    </el-steps>

    <div class="mt-5">
      <div v-show="activeStep === 0">
        <GenBasicStep
          :info="info"
          :rules="rules"
          :menu-options="menuOptions"
          @clear-master-sub="emit('clear-master-sub')"
          @master-sub-blur="emit('master-sub-blur')"
        />
      </div>

      <div v-show="activeStep === 1">
        <GenColumnsStep
          :info="info"
          :dict-options="dictOptions"
          :loading="loading"
          :bulk-set="bulkSet"
        />
      </div>

      <GenPreviewStep
        v-show="activeStep === 2"
        v-model:preview-scope="previewScope"
        v-model:preview-types="previewTypes"
        v-model:code="code"
        :preview-loading="previewLoading"
        :preview-type-options="previewTypeOptions"
        :filtered-tree-data="filteredTreeData"
        :cm-options="cmOptions"
        @file-click="emit('file-click', $event)"
        @copy-code="emit('copy-code')"
      />
    </div>

    <template #footer>
      <el-button :icon="Close" @click="emit('close')">关闭</el-button>
      <el-button v-if="activeStep !== 0" type="success" :icon="Back" @click="emit('prev-step')">
        上一步
      </el-button>
      <el-button
        v-if="activeStep !== 2"
        type="primary"
        :loading="nextStepLoading"
        @click="emit('next-step')"
      >
        下一步
        <el-icon class="el-icon--right"><Right /></el-icon>
      </el-button>
      <el-button
        v-if="activeStep === 2"
        type="warning"
        :icon="Download"
        :loading="loading"
        @click="emit('gen-download')"
      >
        下载代码
      </el-button>
      <el-button
        v-if="activeStep === 2"
        type="primary"
        :icon="FolderOpened"
        :loading="loading"
        @click="emit('gen-write')"
      >
        写入本地
      </el-button>
    </template>
  </EnhancedDrawer>
</template>

<script setup lang="ts">
import type { FormRules } from "element-plus";
import { Close, Right, FolderOpened, Back, Download } from "@element-plus/icons-vue";
import type { EditorConfiguration } from "codemirror";
import type { GenTableSchema } from "@/api/module_generator/gencode";
import type { DictTable } from "@/api/module_system/dict";
import EnhancedDrawer from "@/components/CURD/EnhancedDrawer.vue";
import type { TreeNode } from "../types";
import GenBasicStep from "./GenBasicStep.vue";
import GenColumnsStep from "./GenColumnsStep.vue";
import GenPreviewStep from "./GenPreviewStep.vue";

defineOptions({ name: "GenCodeDrawer" });

defineProps<{
  info: GenTableSchema;
  rules: FormRules;
  activeStep: number;
  menuOptions: OptionType[];
  dictOptions: DictTable[];
  loading: boolean;
  nextStepLoading: boolean;
  previewLoading: boolean;
  previewTypeOptions: string[];
  filteredTreeData: TreeNode[];
  cmOptions: EditorConfiguration;
  bulkSet: (field: string | string[], value: unknown) => void;
}>();

const drawerVisible = defineModel<boolean>({ required: true });

const previewScope = defineModel<"all" | "frontend" | "backend">("previewScope", {
  required: true,
});
const previewTypes = defineModel<string[]>("previewTypes", { required: true });
const code = defineModel<string>("code", { required: true });

const emit = defineEmits<{
  close: [];
  "prev-step": [];
  "next-step": [];
  "gen-download": [];
  "gen-write": [];
  "clear-master-sub": [];
  "master-sub-blur": [];
  "file-click": [data: TreeNode];
  "copy-code": [];
}>();
</script>
