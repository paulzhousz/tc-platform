import { onUnmounted, ref, type Ref } from "vue";

/**
 * FunASR WebSocket Composable
 *
 * 用于连接 FunASR Docker WebSocket 服务实现实时语音识别
 * 协议:
 * - 连接后立即发送: JSON初始化消息
 * - 发送: 二进制PCM数据 (Int16 16kHz)
 * - 结束: JSON结束信号
 * - 接收: {"text": "识别文本", "is_final": false/true, "mode": "..."}
 *
 * 服务端点: ws://host:10095
 */

interface FunASRStampSent {
  start: number;
  end: number;
  punc: string;
  text_seg: string;
  ts_list: number[][];
}

interface FunASRMessage {
  text?: string;
  is_final?: boolean;
  mode?: string;
  is_speaking?: boolean;
  timestamp?: number[][] | string;
  stamp_sents?: FunASRStampSent[];
  wav_name?: string;
}

interface UseFunASRWsOptions {
  serverUrl?: string;
  onResult?: (text: string, isFinal: boolean) => void;
  onError?: (error: Error) => void;
  /** 静音音量阈值，低于此值视为静音 */
  silenceThreshold?: number;
  /** 静音持续时间(秒)，超过此时间自动结束录音 */
  silenceDuration?: number;
}

export function useFunASRWs(options: UseFunASRWsOptions = {}) {
  const {
    serverUrl = getDefaultFunASRUrl(),
    onResult,
    onError,
    silenceThreshold = 0.01,
    silenceDuration = 1.5,
  } = options;

  const ws: Ref<WebSocket | null> = ref(null);
  const isConnected = ref(false);
  const isRecording = ref(false);
  const tempResult = ref("");
  const finalResult = ref("");

  // 累积的识别文本（2pass 模式需要累积）
  let accumulatedText = "";
  // 当前句子的起始时间戳（用于判断是否是新句子）
  let currentSentenceStart = -1;

  // 静音检测配置（可动态更新）
  const silenceConfig = {
    threshold: silenceThreshold,
    duration: silenceDuration,
  };

  // 录音相关
  let audioContext: AudioContext | null = null;
  let mediaStream: MediaStream | null = null;
  let workletNode: AudioWorkletNode | null = null;

  /**
   * 获取 FunASR WebSocket URL
   */
  function getDefaultFunASRUrl(): string {
    // 开发环境直连 Docker 服务
    if (import.meta.env.DEV) {
      return "ws://localhost:10095";
    }
    // 生产环境通过 Nginx 代理
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    return `${protocol}//${host}/funasr-ws`;
  }

  /**
   * 连接 WebSocket
   */
  async function connect(): Promise<boolean> {
    return new Promise((resolve) => {
      try {
        console.log("连接 FunASR 服务:", serverUrl);
        ws.value = new WebSocket(serverUrl);

        ws.value.onopen = () => {
          isConnected.value = true;
          console.log("FunASR WebSocket 连接成功");
          resolve(true);
        };

        ws.value.onmessage = (event) => {
          try {
            const rawData = event.data;

            // 确保是 JSON 字符串
            if (typeof rawData === "string" && rawData.startsWith("{")) {
              const data: FunASRMessage = JSON.parse(rawData);

              if (data.is_final === true) {
                // 最终结束信号
                if (accumulatedText) {
                  finalResult.value = accumulatedText;
                  onResult?.(accumulatedText, true);
                  console.log("语音识别完成:", accumulatedText);
                }
                tempResult.value = "";
              } else if (data.text) {
                // 识别结果
                if (
                  data.mode === "2pass-offline" &&
                  data.stamp_sents &&
                  data.stamp_sents.length > 0
                ) {
                  // 2pass-offline: 离线修正结果
                  const validStamp = data.stamp_sents.find((s) => s.start >= 0);
                  const newStart = validStamp ? validStamp.start : -1;

                  if (newStart >= 0 && newStart !== currentSentenceStart) {
                    // 新句子开始，直接追加到累积文本
                    accumulatedText += data.text;
                    currentSentenceStart = newStart;
                  } else {
                    // 同一句子的更新
                    if (newStart < 0 && currentSentenceStart >= 0) {
                      // 这是带标点前缀的 continuation
                      accumulatedText += data.text;
                    }
                  }
                  tempResult.value = accumulatedText;
                } else {
                  // 2pass-online: 实时流式结果，追加显示
                  tempResult.value = accumulatedText + data.text;
                }
                onResult?.(tempResult.value, false);
              }
            }
          } catch (e) {
            console.error("解析 FunASR 消息失败:", e);
          }
        };

        ws.value.onclose = (event) => {
          isConnected.value = false;
          isRecording.value = false;
          console.log("FunASR WebSocket 断开:", event.code, event.reason);
        };

        ws.value.onerror = () => {
          console.error("FunASR WebSocket 错误");
          isConnected.value = false;
          onError?.(new Error("WebSocket 连接失败"));
          resolve(false);
        };
      } catch (e) {
        console.error("创建 WebSocket 失败:", e);
        resolve(false);
      }
    });
  }

  /**
   * 断开连接
   */
  function disconnect() {
    stopRecording();

    if (ws.value) {
      ws.value.close();
      ws.value = null;
    }
    isConnected.value = false;
  }

  /**
   * 发送初始化消息 - 开始录音时发送
   * 2pass-offline 模式：实时流式识别 + 离线修正
   */
  function sendStartMessage() {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      const msg = JSON.stringify({
        mode: "2pass-offline",
        wav_name: "modbus_voice_input",
        is_speaking: true,
        audio_fs: 16000,
        wav_format: "pcm",
        chunk_size: [5, 10, 5],
      });
      ws.value.send(msg);
    }
  }

  /**
   * 发送音频块 - FunASR 需要 Int16 PCM (16-bit)
   */
  function sendAudioChunk(chunk: Float32Array) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      // 转换 Float32 到 Int16 PCM
      const int16Data = float32ToInt16(chunk);
      ws.value.send(int16Data.buffer);
    }
  }

  /**
   * Float32 转 Int16 PCM
   */
  function float32ToInt16(float32: Float32Array): Int16Array {
    const int16 = new Int16Array(float32.length);
    for (let i = 0; i < float32.length; i++) {
      const s = Math.max(-1, Math.min(1, float32[i]));
      int16[i] = s < 0 ? Math.floor(s * 0x8000) : Math.floor(s * 0x7fff);
    }
    return int16;
  }

  /**
   * 发送结束信号
   */
  function sendEndSignal() {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ is_speaking: false }));
    }
  }

  /**
   * 开始录音
   */
  async function startRecording(): Promise<boolean> {
    if (!isConnected.value) {
      const connected = await connect();
      if (!connected) {
        onError?.(new Error("无法连接语音服务"));
        return false;
      }
    }

    try {
      // 获取麦克风权限
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        },
      });

      // 创建 AudioContext
      const AudioContextClass =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext })
          .webkitAudioContext;
      audioContext = new AudioContextClass();

      if (audioContext.state === "suspended") {
        await audioContext.resume();
      }

      const nativeSampleRate = audioContext.sampleRate;

      // 加载 AudioWorklet
      const workletUrl = "/workers/audio-processor.js";
      await audioContext.audioWorklet.addModule(workletUrl);

      // 创建音频源和 Worklet 节点
      const source = audioContext.createMediaStreamSource(mediaStream);
      workletNode = new AudioWorkletNode(audioContext, "audio-resampler", {
        processorOptions: {
          nativeSampleRate,
          silenceThreshold: silenceConfig.threshold,
          silenceDuration: silenceConfig.duration,
        },
      });

      // 监听音频块和静音检测事件
      workletNode.port.onmessage = (event) => {
        if (event.data.type === "audio-chunk") {
          const chunk = new Float32Array(event.data.data);
          if (chunk.length > 0) {
            sendAudioChunk(chunk);
          }
        } else if (event.data.type === "silence-detected") {
          // 静音检测到，自动结束录音
          console.log("检测到静音，自动结束录音");
          stopRecording();
        }
      };

      // 连接节点
      source.connect(workletNode);
      workletNode.connect(audioContext.destination);

      // 发送初始化消息（开始录音）
      sendStartMessage();

      // 清空结果
      tempResult.value = "";
      finalResult.value = "";
      accumulatedText = "";
      currentSentenceStart = -1;
      isRecording.value = true;

      console.log("开始录音");
      return true;
    } catch (e: unknown) {
      console.error("启动录音失败:", e);
      const errorMessage =
        e instanceof Error ? e.message : "无法访问麦克风";
      onError?.(new Error(errorMessage));
      return false;
    }
  }

  /**
   * 停止录音
   */
  function stopRecording() {
    if (!isRecording.value) return;

    // 发送结束信号
    sendEndSignal();

    // 清理录音资源
    if (workletNode) {
      workletNode.port.close();
      workletNode.disconnect();
      workletNode = null;
    }

    if (audioContext) {
      audioContext.close();
      audioContext = null;
    }

    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
      mediaStream = null;
    }

    isRecording.value = false;
    console.log("停止录音");
  }

  /**
   * 更新静音检测配置
   * @param threshold 静音音量阈值
   * @param duration 静音持续时间(秒)
   */
  function updateSilenceConfig(threshold: number, duration: number) {
    silenceConfig.threshold = threshold;
    silenceConfig.duration = duration;
    console.log("更新静音检测配置:", { threshold, duration });
  }

  // 组件卸载时清理
  onUnmounted(() => {
    disconnect();
  });

  return {
    isConnected,
    isRecording,
    tempResult,
    finalResult,
    connect,
    disconnect,
    startRecording,
    stopRecording,
    updateSilenceConfig,
  };
}

export default useFunASRWs;