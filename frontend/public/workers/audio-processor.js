/**
 * AudioWorklet 处理器
 * 用于将麦克风采集的音频重采样为 16kHz PCM，并进行静音检测
 *
 * 功能：
 * 1. 将任意采样率重采样为 16kHz
 * 2. 静音检测（支持自动结束录音）
 * 3. 输出 Float32Array 音频块
 */

/**
 * @typedef {Object} ProcessorOptions
 * @property {number} nativeSampleRate - 原始采样率
 * @property {number} [silenceThreshold] - 静音音量阈值
 * @property {number} [silenceDuration] - 静音持续时间（秒）
 */

class AudioResamplerProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();

    /** @type {number} 目标采样率 */
    this.targetSampleRate = 16000;

    /** @type {number} 原始采样率 */
    this.nativeSampleRate = 44100;

    /** @type {number} 静音音量阈值 */
    this.silenceThreshold = 0.03;

    /** @type {number} 静音持续时间（秒） */
    this.silenceDuration = 1.5;

    /** @type {number} 重采样比例 */
    this.resampleRatio = 1;

    /** @type {number} 上一个采样值 */
    this.lastSample = 0;

    /** @type {number|null} 静音开始时间 */
    this.silenceStartTime = null;

    /** @type {boolean} 是否处于静音状态 */
    this.isSilent = false;

    /** @type {boolean} 是否已检测到语音（预热期标志） */
    this.hasSpoken = false;

    // 初始化配置
    if (options && options.processorOptions) {
      const opts = options.processorOptions;
      this.nativeSampleRate = opts.nativeSampleRate || 44100;
      this.silenceThreshold = opts.silenceThreshold ?? 0.03;
      this.silenceDuration = opts.silenceDuration ?? 5;
      // 输出配置日志
      this.port.postMessage({
        type: "config",
        silenceThreshold: this.silenceThreshold,
        silenceDuration: this.silenceDuration,
        nativeSampleRate: this.nativeSampleRate
      });
    }

    this.resampleRatio = this.nativeSampleRate / this.targetSampleRate;
  }

  /**
   * 计算音频块的 RMS（均方根）音量
   * @param {Float32Array} samples - 音频采样数据
   * @returns {number} RMS 音量值
   */
  calculateRMS(samples) {
    let sumSquares = 0;
    for (let i = 0; i < samples.length; i++) {
      sumSquares += samples[i] * samples[i];
    }
    return Math.sqrt(sumSquares / samples.length);
  }

  /**
   * 线性插值重采样
   * @param {Float32Array} input - 输入音频数据
   * @returns {Float32Array} 重采样后的音频数据
   */
  resample(input) {
    const outputLength = Math.floor(input.length / this.resampleRatio);
    const output = new Float32Array(outputLength);

    for (let i = 0; i < outputLength; i++) {
      const srcIndex = i * this.resampleRatio;
      const srcIndexFloor = Math.floor(srcIndex);
      const fraction = srcIndex - srcIndexFloor;

      if (srcIndexFloor + 1 < input.length) {
        // 线性插值
        output[i] =
          input[srcIndexFloor] * (1 - fraction) +
          input[srcIndexFloor + 1] * fraction;
      } else {
        output[i] = input[srcIndexFloor] || this.lastSample;
      }
    }

    // 保存最后一个采样值用于下次插值
    if (input.length > 0) {
      this.lastSample = input[input.length - 1];
    }

    return output;
  }

  /**
   * 处理音频数据（AudioWorklet 生命周期方法）
   * @param {Float32Array[][]} inputs - 输入音频数据
   * @param {Float32Array[][]} _outputs - 输出音频数据（未使用）
   * @param {Record<string, Float32Array>} _parameters - 参数（未使用）
   * @returns {boolean} 是否保持处理器活跃
   */
  process(inputs, _outputs, _parameters) {
    const input = inputs[0];
    if (!input || input.length === 0) {
      return true;
    }

    // 使用第一个通道（单声道）
    const channelData = input[0];
    if (!channelData || channelData.length === 0) {
      return true;
    }

    // 计算音量
    const rms = this.calculateRMS(channelData);

    // 静音检测（只在检测到语音后才启动静音计时）
    if (rms < this.silenceThreshold) {
      // 当前是静音
      if (this.hasSpoken && this.silenceStartTime === null) {
        this.silenceStartTime = currentTime;
      }

      const silenceElapsed = this.silenceStartTime !== null ? currentTime - this.silenceStartTime : 0;
      if (this.hasSpoken && silenceElapsed >= this.silenceDuration && !this.isSilent) {
        this.isSilent = true;
        // 通知主线程检测到静音
        this.port.postMessage({ type: "silence-detected" });
      }
    } else {
      // 检测到语音，标记已开始说话，重置静音计时
      if (!this.hasSpoken) {
        // 首次检测到语音，发送日志
        this.port.postMessage({ type: "voice-detected", rms: rms });
      }
      this.hasSpoken = true;
      this.silenceStartTime = null;
      this.isSilent = false;
    }

    // 重采样到 16kHz
    const resampled = this.resample(channelData);

    // 发送重采样后的音频数据
    if (resampled.length > 0) {
      this.port.postMessage(
        {
          type: "audio-chunk",
          data: resampled.buffer,
        },
        [resampled.buffer]
      );
    }

    return true;
  }
}

// 注册处理器（带版本号）
registerProcessor("audio-resampler-v6", AudioResamplerProcessor);