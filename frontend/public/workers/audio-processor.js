/**
 * AudioWorklet 处理器
 * 用于将麦克风采集的音频重采样为 16kHz PCM，并进行静音检测
 *
 * 功能：
 * 1. 将任意采样率重采样为 16kHz
 * 2. 静音检测（支持自动结束录音）
 * 3. 输出 Float32Array 音频块
 */

interface ProcessorOptions {
  nativeSampleRate: number;
  silenceThreshold?: number;
  silenceDuration?: number;
}

class AudioResamplerProcessor extends AudioWorkletProcessor {
  private targetSampleRate: number = 16000;
  private nativeSampleRate: number = 44100;
  private silenceThreshold: number = 0.01;
  private silenceDuration: number = 1.5;

  // 重采样状态
  private resampleRatio: number = 1;
  private lastSample: number = 0;

  // 静音检测状态
  private silenceStartTime: number | null = null;
  private isSilent: boolean = false;

  constructor(options: AudioWorkletNodeOptions) {
    super();

    if (options.processorOptions) {
      const opts = options.processorOptions as ProcessorOptions;
      this.nativeSampleRate = opts.nativeSampleRate || 44100;
      this.silenceThreshold = opts.silenceThreshold ?? 0.01;
      this.silenceDuration = opts.silenceDuration ?? 1.5;
    }

    this.resampleRatio = this.nativeSampleRate / this.targetSampleRate;
  }

  /**
   * 计算音频块的 RMS（均方根）音量
   */
  private calculateRMS(samples: Float32Array): number {
    let sumSquares = 0;
    for (let i = 0; i < samples.length; i++) {
      sumSquares += samples[i] * samples[i];
    }
    return Math.sqrt(sumSquares / samples.length);
  }

  /**
   * 线性插值重采样
   */
  private resample(input: Float32Array): Float32Array {
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
   * 处理音频数据
   */
  process(
    inputs: Float32Array[][],
    _outputs: Float32Array[][],
    _parameters: Record<string, Float32Array>
  ): boolean {
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
    const currentTime = currentTime;

    // 静音检测
    if (rms < this.silenceThreshold) {
      // 当前是静音
      if (this.silenceStartTime === null) {
        this.silenceStartTime = currentTime;
      }

      const silenceElapsed = currentTime - this.silenceStartTime;
      if (silenceElapsed >= this.silenceDuration && !this.isSilent) {
        this.isSilent = true;
        // 通知主线程检测到静音
        this.port.postMessage({ type: "silence-detected" });
      }
    } else {
      // 不是静音，重置静音计时
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

// 注册处理器
registerProcessor("audio-resampler", AudioResamplerProcessor);