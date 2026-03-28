<!-- 菜单组件 -->
<template>
  <el-menu
    :default-active="activeMenuPath"
    :collapse="!appStore.sidebar.opened"
    :background-color="menuThemeProps.backgroundColor"
    :text-color="menuThemeProps.textColor"
    :active-text-color="menuThemeProps.activeTextColor"
    :popper-effect="theme"
    :unique-opened="false"
    :collapse-transition="false"
    :mode="menuMode"
  >
    <!-- 菜单项 -->
    <MenuItem
      v-for="route in data"
      :key="route.path"
      :item="route"
      :base-path="resolveFullPath(route.path)"
    />
  </el-menu>
</template>

<script lang="ts" setup>
import { useRoute } from "vue-router";
import path from "path-browserify";
import type { RouteRecordRaw } from "vue-router";
import { SidebarColor } from "@/enums/settings/theme.enum";
import { useSettingsStore, useAppStore } from "@/store";
import { isExternal } from "@/utils/index";
import MenuItem from "./components/MenuItem.vue";
import variables from "@/styles/variables.module.scss";

const props = defineProps({
  data: {
    type: Array as PropType<RouteRecordRaw[]>,
    default: () => [],
  },
  basePath: {
    type: String,
    required: true,
    example: "/system",
  },
  menuMode: {
    type: String as PropType<"vertical" | "horizontal">,
    default: "vertical",
    validator: (value: string) => ["vertical", "horizontal"].includes(value),
  },
});

const settingsStore = useSettingsStore();
const appStore = useAppStore();
const currentRoute = useRoute();

// 获取主题
const theme = computed(() => settingsStore.theme);

// 获取浅色主题下的侧边栏配色方案
const sidebarColorScheme = computed(() => settingsStore.sidebarColorScheme);

// 菜单主题属性
const menuThemeProps = computed(() => {
  const isDarkOrClassicBlue =
    theme.value === "dark" || sidebarColorScheme.value === SidebarColor.CLASSIC_BLUE;

  return {
    backgroundColor: isDarkOrClassicBlue ? variables["menu-background"] : undefined,
    textColor: isDarkOrClassicBlue ? variables["menu-text"] : undefined,
    activeTextColor: isDarkOrClassicBlue ? variables["menu-active-text"] : undefined,
  };
});

// 计算当前激活的菜单项
const activeMenuPath = computed((): string => {
  const { meta, path } = currentRoute;

  // 如果路由meta中设置了activeMenu，则使用它（用于处理一些特殊情况，如详情页）
  if (meta?.activeMenu && typeof meta.activeMenu === "string") {
    return meta.activeMenu;
  }

  // 否则使用当前路由路径
  return path;
});

/**
 * 获取完整路径
 *
 * @param routePath 当前路由的相对路径  /user
 * @returns 完整的绝对路径 D://vue3-element-admin/system/user
 */
function resolveFullPath(routePath: string) {
  if (isExternal(routePath)) {
    return routePath;
  }
  if (isExternal(props.basePath)) {
    return props.basePath;
  }

  // 如果 basePath 为空（顶部布局），直接返回 routePath
  if (!props.basePath || props.basePath === "") {
    return routePath;
  }

  // 解析路径，生成完整的绝对路径
  return path.resolve(props.basePath, routePath);
}

// 父级高亮（has-active-child）已改为由 MenuItem 依据路由状态计算并绑定 class，
// 不再依赖 DOM 查询，避免折叠/teleported 场景丢失。
</script>
