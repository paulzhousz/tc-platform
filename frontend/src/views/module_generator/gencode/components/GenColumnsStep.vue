<template>
  <div class="elTableCustom">
    <el-alert
      v-if="info.sub && !info.master_sub_hint && info.sub_table_name"
      class="mb-3"
      type="success"
      :closable="false"
      show-icon
      title="当前已启用主子表：以下为「主表」字段配置；子表字段来自数据库结构，保存后可在预览中查看子表生成代码。"
    />
    <el-alert
      v-else-if="info.master_sub_hint"
      class="mb-3"
      type="warning"
      :closable="false"
      show-icon
      :title="info.master_sub_hint"
    />
    <div class="mb-2 flex items-center gap-2">
      <el-tag size="small" type="info">批量设置</el-tag>
      <el-space size="small">
        <el-dropdown>
          <el-button size="small" type="primary" plain>查询</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="bulkSet('is_query', true)">全选</el-dropdown-item>
              <el-dropdown-item @click="bulkSet('is_query', false)">全不选</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-dropdown>
          <el-button size="small" type="success" plain>列表</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="bulkSet('is_list', true)">全选</el-dropdown-item>
              <el-dropdown-item @click="bulkSet('is_list', false)">全不选</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-dropdown>
          <el-button size="small" type="warning" plain>新增</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="bulkSet('is_insert', true)">全选</el-dropdown-item>
              <el-dropdown-item @click="bulkSet('is_insert', false)">全不选</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-dropdown>
          <el-button size="small" type="danger" plain>编辑</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="bulkSet('is_edit', true)">全选</el-dropdown-item>
              <el-dropdown-item @click="bulkSet('is_edit', false)">全不选</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-space>
    </div>
    <div class="data-table__content">
      <el-table
        ref="dragTable"
        v-loading="loading"
        :data="info.columns"
        row-key="id"
        max-height="680"
        highlight--currentrow
        border
        stripe
      >
        <template #empty>
          <el-empty :image-size="80" description="暂无数据" />
        </template>
        <el-table-column label="序号" type="index" width="60" fixed />
        <el-table-column
          label="列名"
          prop="column_name"
          min-width="60"
          :show-overflow-tooltip="true"
        />
        <el-table-column
          label="类型"
          prop="column_type"
          min-width="60"
          :show-overflow-tooltip="true"
        />
        <el-table-column label="长度" prop="column_length" width="80" :show-overflow-tooltip="true">
          <template #default="scope">
            <el-input v-model="scope.row.column_length" :disabled="scope.row.is_pk === '1'" />
          </template>
        </el-table-column>
        <el-table-column label="注释" min-width="60">
          <template #default="scope">
            <el-input v-model="scope.row.column_comment"></el-input>
          </template>
        </el-table-column>
        <el-table-column label="后端类型" min-width="60">
          <template #default="scope">
            <el-select v-model="scope.row.python_type">
              <el-option label="str" value="str" />
              <el-option label="int" value="int" />
              <el-option label="float" value="float" />
              <el-option label="Decimal" value="Decimal" />
              <el-option label="date" value="date" />
              <el-option label="time" value="time" />
              <el-option label="datetime" value="datetime" />
              <el-option label="bytes" value="bytes" />
              <el-option label="dict" value="dict" />
              <el-option label="list" value="list" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="后端属性" min-width="60">
          <template #default="scope">
            <el-input v-model="scope.row.python_field"></el-input>
          </template>
        </el-table-column>
        <el-table-column label="新增" width="60">
          <template #default="scope">
            <el-checkbox v-model="scope.row.is_insert" />
          </template>
        </el-table-column>
        <el-table-column label="编辑" width="60">
          <template #default="scope">
            <el-checkbox v-model="scope.row.is_edit" />
          </template>
        </el-table-column>
        <el-table-column label="列表" width="60">
          <template #default="scope">
            <el-checkbox v-model="scope.row.is_list" />
          </template>
        </el-table-column>
        <el-table-column label="查询" width="60">
          <template #default="scope">
            <el-checkbox v-model="scope.row.is_query" />
          </template>
        </el-table-column>
        <el-table-column label="查询方式" min-width="60">
          <template #default="scope">
            <el-select v-model="scope.row.query_type">
              <el-option label="=" value="EQ" />
              <el-option label="!=" value="NE" />
              <el-option label=">" value="GT" />
              <el-option label=">=" value="GTE" />
              <el-option label="<" value="LT" />
              <el-option label="<=" value="LTE" />
              <el-option label="LIKE" value="LIKE" />
              <el-option label="BETWEEN" value="BETWEEN" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column
          label="默认值"
          prop="column_default"
          min-width="60"
          :show-overflow-tooltip="true"
        >
          <template #default="scope">
            <el-input v-model="scope.row.column_default" :disabled="scope.row.is_pk === '1'" />
          </template>
        </el-table-column>
        <el-table-column label="自增" width="60">
          <template #default="scope">
            <el-checkbox v-model="scope.row.is_increment" />
          </template>
        </el-table-column>
        <el-table-column label="可空" width="60">
          <template #default="scope">
            <el-checkbox v-model="scope.row.is_nullable" />
          </template>
        </el-table-column>
        <el-table-column label="唯一" width="60">
          <template #default="scope">
            <el-checkbox v-model="scope.row.is_unique" />
          </template>
        </el-table-column>
        <el-table-column label="主键" width="60">
          <template #default="scope">
            <el-checkbox v-model="scope.row.is_pk" />
          </template>
        </el-table-column>
        <el-table-column label="表单类型">
          <template #default="scope">
            <el-select v-model="scope.row.html_type">
              <el-option label="文本框" value="input" />
              <el-option label="文本域" value="textarea" />
              <el-option label="下拉框" value="select" />
              <el-option label="单选框" value="radio" />
              <el-option label="复选框" value="checkbox" />
              <el-option label="日期控件" value="datetime" />
              <el-option label="图片上传" value="imageUpload" />
              <el-option label="文件上传" value="fileUpload" />
              <el-option label="富文本控件" value="editor" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="字典类型" fixed="right">
          <template #default="scope">
            <el-select v-model="scope.row.dict_type" clearable filterable placeholder="请选择">
              <el-option
                v-for="dict in dictOptions"
                :key="dict.dict_type"
                :label="dict.dict_name"
                :value="dict.dict_type || ''"
              >
                <span style="float: left">{{ dict.dict_name }}</span>
                <span style="float: right; font-size: 13px; color: #8492a6">
                  {{ dict.dict_type }}
                </span>
              </el-option>
            </el-select>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { GenTableSchema } from "@/api/module_generator/gencode";
import type { DictTable } from "@/api/module_system/dict";

defineOptions({ name: "GenColumnsStep" });

defineProps<{
  info: GenTableSchema;
  dictOptions: DictTable[];
  loading: boolean;
  bulkSet: (field: string | string[], value: unknown) => void;
}>();
</script>
