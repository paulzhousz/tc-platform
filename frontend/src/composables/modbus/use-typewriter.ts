/**
 * 打字机效果 Composable
 *
 * 用于实现流式文本的打字机光标效果
 */

import { onUnmounted, ref, watch } from "vue";

export function useTypewriter(isTyping: () => boolean) {
  // 光标可见性状态
  const cursorVisible = ref(true);
  let cursorInterval: ReturnType<typeof setInterval> | null = null;

  // 开始光标闪烁
  function startCursorBlink() {
    if (cursorInterval) return;

    cursorVisible.value = true;
    cursorInterval = setInterval(() => {
      cursorVisible.value = !cursorVisible.value;
    }, 530); // 530ms 闪烁间隔
  }

  // 停止光标闪烁
  function stopCursorBlink() {
    if (cursorInterval) {
      clearInterval(cursorInterval);
      cursorInterval = null;
    }
    cursorVisible.value = false;
  }

  // 监听打字状态
  watch(
    () => isTyping(),
    (typing) => {
      if (typing) {
        startCursorBlink();
      } else {
        stopCursorBlink();
      }
    },
    { immediate: true }
  );

  // 组件卸载时清理
  onUnmounted(() => {
    stopCursorBlink();
  });

  return {
    cursorVisible,
    startCursorBlink,
    stopCursorBlink,
  };
}

/**
 * 创建打字机效果的 CSS 类
 * 可在组件样式中使用
 */
export const typewriterStyles = `
/* 打字机光标效果 */
.typewriter-cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background-color: currentColor;
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: cursor-blink 1s step-end infinite;
}

.typewriter-cursor.hidden {
  opacity: 0;
}

@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* 打字机文本容器 */
.typewriter-text {
  display: inline;
}

/* 流式文本淡入效果 */
.stream-text {
  animation: text-fade-in 0.1s ease-in;
}

@keyframes text-fade-in {
  from { opacity: 0.7; }
  to { opacity: 1; }
}
`;
