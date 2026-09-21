import { textToSpeech } from '@kit.CoreSpeechKit';
import { BusinessError } from '@kit.BasicServicesKit';

@Entry
@Component
struct Index {
  @State status: string = '未检测英文音色';
  @State voiceInfo: string = '';
  @State ready: boolean = false;

  private ttsEngine: textToSpeech.TextToSpeechEngine | undefined = undefined;
  private readonly sampleText: string =
    'alternative. gratification. procreation. subconscious. in retrospect.';

  private async queryLaura(): Promise<void> {
    try {
      const query: textToSpeech.VoiceQuery = {
        requestId: 'query_' + Date.now(),
        online: 1,
        extraParams: {
          'language': 'en-US',
          'person': 8
        }
      };

      const voices: textToSpeech.VoiceInfo[] = await textToSpeech.listVoices(query);
      const laura: textToSpeech.VoiceInfo | undefined =
        voices.find((v: textToSpeech.VoiceInfo) => v.language === 'en-US' && v.person === 8);

      if (!laura) {
        this.status = '未查询到 en-US / person 8（Laura）';
        this.voiceInfo = JSON.stringify(voices);
        return;
      }

      this.voiceInfo = JSON.stringify(laura);
      if (laura.status === 'INSTALLED') {
        this.status = 'Laura 已安装，可以初始化';
      } else if (laura.status === 'GA') {
        this.status = 'Laura 可下载，先点“下载 Laura”';
      } else if (laura.status === 'EOM') {
        this.status = 'Laura 当前不可用';
      } else {
        this.status = '查询成功，状态：' + (laura.status ?? '未返回');
      }
    } catch (e) {
      const err = e as BusinessError;
      this.status = '查询失败：' + err.code + ' / ' + err.message;
    }
  }

  private downloadLaura(): void {
    this.status = '正在请求下载 Laura…';

    const request: textToSpeech.VoiceDownload = {
      requestId: 'download_' + Date.now(),
      language: 'en-US',
      person: 8,
      style: 'interaction-broadcast'
    };

    textToSpeech.downloadVoice(
      request,
      (error: BusinessError, response: textToSpeech.DownloadResponse) => {
        if (error) {
          if (error.code === 1002300010) {
            this.status = 'Laura 已经下载过，可以直接初始化';
          } else {
            this.status = '下载请求失败：' + error.code + ' / ' + error.message;
          }
          return;
        }

        if (!response) {
          this.status = '下载响应为空';
          return;
        }

        response.on('start', () => {
          this.status = '开始下载 Laura…';
        });

        response.on('progress', (progress: string) => {
          this.status = '下载中：' + progress;
        });

        response.on('complete', (voice: textToSpeech.VoiceInfo) => {
          this.status = 'Laura 下载完成：' + voice.language + ' / person ' + voice.person;
          this.voiceInfo = JSON.stringify(voice);
        });

        response.on('cancel', () => {
          this.status = '已取消下载';
        });

        response.on('error', (err: BusinessError) => {
          this.status = '下载过程失败：' + err.code + ' / ' + err.message;
        });
      }
    );
  }

  private async initEngine(): Promise<void> {
    try {
      if (this.ttsEngine) {
        this.ttsEngine.shutdown();
        this.ttsEngine = undefined;
      }

      const params: textToSpeech.CreateEngineParams = {
        language: 'en-US',
        person: 8,
        online: 1,
        extraParams: {
          'style': 'interaction-broadcast',
          'locate': 'CN',
          'name': 'WordCardLauraProbe',
          'isBackStage': false
        }
      };

      this.status = '正在初始化 Laura 引擎…';
      this.ttsEngine = await textToSpeech.createEngine(params);

      const listener: textToSpeech.SpeakListener = {
        onStart: (requestId: string, response: textToSpeech.StartResponse) => {
          this.status = '开始播报：' + requestId + ' / ' + JSON.stringify(response);
        },
        onComplete: (requestId: string, response: textToSpeech.CompleteResponse) => {
          if (response.type === 1) {
            this.status = '播报完成';
          }
        },
        onStop: (requestId: string, response: textToSpeech.StopResponse) => {
          this.status = '已停止：' + requestId + ' / ' + JSON.stringify(response);
        },
        onData: (_requestId: string, _audio: ArrayBuffer, _response: textToSpeech.SynthesisResponse) => {
        },
        onError: (requestId: string, errorCode: number, errorMessage: string) => {
          this.status = '播报失败：' + requestId + ' / ' + errorCode + ' / ' + errorMessage;
        }
      };

      this.ttsEngine.setListener(listener);
      this.ready = true;
      this.status = 'Laura 引擎已就绪';
    } catch (e) {
      const err = e as BusinessError;
      this.ready = false;
      this.status = '初始化失败：' + err.code + ' / ' + err.message;
    }
  }

  private speakSample(): void {
    if (!this.ttsEngine || !this.ready) {
      this.status = '请先初始化 Laura 引擎';
      return;
    }

    const extraParams: Record<string, Object> = {
      'queueMode': 0,
      'speed': 0.92,
      'volume': 1.2,
      'pitch': 1,
      'languageContext': 'en-US',
      'audioType': 'pcm',
      'soundChannel': 1,
      'playType': 1
    };

    const speakParams: textToSpeech.SpeakParams = {
      requestId: 'speak_' + Date.now(),
      extraParams: extraParams
    };

    try {
      this.ttsEngine.speak(this.sampleText, speakParams);
    } catch (e) {
      const err = e as BusinessError;
      this.status = '调用 speak 失败：' + err.code + ' / ' + err.message;
    }
  }

  aboutToDisappear(): void {
    if (this.ttsEngine) {
      this.ttsEngine.shutdown();
      this.ttsEngine = undefined;
    }
  }

  build() {
    Scroll() {
      Column({ space: 14 }) {
        Text('Word Card · HarmonyOS 原生英语 TTS Probe')
          .fontSize(22)
          .fontWeight(FontWeight.Bold)
          .width('100%')

        Text('目标音色：en-US / person 8 / Laura（劳拉女声）')
          .fontSize(15)
          .width('100%')

        Text(this.status)
          .fontSize(14)
          .fontColor('#666666')
          .width('100%')

        Button('1. 检测英文音色')
          .width('100%')
          .onClick(() => this.queryLaura())

        Button('2. 下载 Laura（如需要）')
          .width('100%')
          .onClick(() => this.downloadLaura())

        Button('3. 初始化 Laura')
          .width('100%')
          .onClick(() => this.initEngine())

        Button('4. 播放考研词样例')
          .width('100%')
          .onClick(() => this.speakSample())

        Button('停止')
          .width('100%')
          .onClick(() => {
            if (this.ttsEngine) {
              this.ttsEngine.stop();
            }
          })

        Text('试听文本')
          .fontWeight(FontWeight.Medium)
          .width('100%')

        Text(this.sampleText)
          .fontSize(18)
          .width('100%')

        Text('设备返回的 VoiceInfo')
          .fontWeight(FontWeight.Medium)
          .width('100%')

        Text(this.voiceInfo || '尚未查询')
          .fontSize(12)
          .fontColor('#777777')
          .width('100%')
      }
      .padding(24)
      .width('100%')
    }
    .width('100%')
    .height('100%')
  }
}
