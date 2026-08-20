"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import * as Ably from "ably";
import {
  prepareZXingModule,
  readBarcodes,
  type ReadResult,
} from "zxing-wasm/reader";
import {
  mergeReceiver,
  receiverConnectionLabel,
  type Receiver,
} from "./receiverTransport";
import {
  coverTargetSourceRect,
  selectCenteredBarcode,
} from "./scanTarget";
import {
  edgeSharpnessScore,
  normalizeBlueChannel,
} from "./imageVariants";
import { vaccineNameForBarcode } from "./vaccineCatalog";
import { PWA_RELEASE } from "./release";

prepareZXingModule({
  overrides: {
    locateFile: (path, prefix) =>
      path.endsWith(".wasm") ? "/zxing_reader.wasm" : `${prefix}${path}`,
  },
});

type CameraCapabilitySet = MediaTrackCapabilities & {
  focusMode?: string[];
  torch?: boolean;
  zoom?: { min: number; max: number; step: number };
};

type CameraSettingSet = MediaTrackSettings & {
  zoom?: number;
};

const SAVED_CAMERA_KEY = "asi-pwa-camera-id";
const ABLY_CLIENT_KEY = "asi-android-pwa-ably-client-id";
const WORKSPACE_ID = "4232a7f478a64df09506dc7919c1821b";
const CHANNEL_PREFIX = `asi-barkod:${WORKSPACE_ID}`;
const DISCOVERY_WAIT_MS = 2800;
const PWA_UPDATE_MIN_INTERVAL_MS = 30 * 60 * 1000;
const PWA_SHORT_VERSION = `v${PWA_RELEASE.split(".").slice(-2).join(".")}`;

type ScanFormat = "DATA_MATRIX" | "QR_CODE";

function printableBarcode(value: string) {
  return value.replace(/\u001d/g, "<GS>");
}

function bytesToRaw(result: ReadResult) {
  if (result.text) return result.text;
  return Array.from(result.bytes, (byte) => String.fromCharCode(byte)).join("");
}

function scanFormatFor(result: ReadResult): ScanFormat {
  return result.format === "DataMatrix" ? "DATA_MATRIX" : "QR_CODE";
}

function beep() {
  const AudioContextClass =
    window.AudioContext ||
    (window as typeof window & { webkitAudioContext?: typeof AudioContext })
      .webkitAudioContext;
  if (!AudioContextClass) return;
  const context = new AudioContextClass();
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.frequency.value = 920;
  gain.gain.setValueAtTime(0.12, context.currentTime);
  gain.gain.exponentialRampToValueAtTime(
    0.001,
    context.currentTime + 0.14,
  );
  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start();
  oscillator.stop(context.currentTime + 0.14);
  oscillator.addEventListener("ended", () => void context.close());
}

function wait(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function captureRegion(
  video: HTMLVideoElement,
  target: HTMLElement,
  enhanced: boolean,
) {
  const videoRect = video.getBoundingClientRect();
  const targetRect = target.getBoundingClientRect();
  const region = coverTargetSourceRect(
    video.videoWidth,
    video.videoHeight,
    videoRect.width,
    videoRect.height,
    {
      x: targetRect.left - videoRect.left,
      y: targetRect.top - videoRect.top,
      width: targetRect.width,
      height: targetRect.height,
    },
  );
  const scale = Math.min(
    1600 / region.width,
    Math.max(1, 1200 / region.width),
  );
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(region.width * scale));
  canvas.height = Math.max(1, Math.round(region.height * scale));
  const context = canvas.getContext("2d", {
    alpha: false,
    willReadFrequently: true,
  });
  if (!context) throw new Error("Görüntü işleme alanı açılamadı.");
  context.imageSmoothingEnabled = false;
  if (enhanced) context.filter = "grayscale(1) contrast(1.35)";
  context.drawImage(
    video,
    region.x,
    region.y,
    region.width,
    region.height,
    0,
    0,
    canvas.width,
    canvas.height,
  );
  return context.getImageData(0, 0, canvas.width, canvas.height);
}

async function imageDataFromFile(file: File) {
  const objectUrl = URL.createObjectURL(file);
  try {
    const image = new Image();
    image.src = objectUrl;
    await image.decode();
    if (!image.naturalWidth || !image.naturalHeight) {
      throw new Error("Seçilen fotoğraf açılamadı.");
    }
    // Ekran görüntülerinin çözünürlüğü zaten yeterli; aşırı büyük fotoğrafları
    // tarayıcıyı yormadan QR modüllerini koruyacak boyuta indiriyoruz.
    const scale = Math.min(1, 2048 / Math.max(image.naturalWidth, image.naturalHeight));
    const width = Math.max(1, Math.round(image.naturalWidth * scale));
    const height = Math.max(1, Math.round(image.naturalHeight * scale));
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d", {
      alpha: false,
      willReadFrequently: true,
    });
    if (!context) throw new Error("Fotoğraf işleme alanı açılamadı.");
    context.drawImage(image, 0, 0, width, height);
    return context.getImageData(0, 0, width, height);
  } catch {
    throw new Error("Fotoğraf okunamadı. WhatsApp ekran görüntüsünü PNG veya JPG olarak seçin.");
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

export default function Home() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const scanTargetRef = useRef<HTMLDivElement>(null);
  const photoInputRef = useRef<HTMLInputElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const scanningRef = useRef(false);
  const searchingPcRef = useRef(false);
  const initialStartRef = useRef(false);
  const lastPwaUpdateCheckRef = useRef(0);
  const pendingPwaReloadRef = useRef(false);
  const ablyRef = useRef<Ably.Realtime | null>(null);
  const clientIdRef = useRef("");
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState("");
  const [status, setStatus] = useState("Kamera hazırlanıyor");
  const [cameraDetail, setCameraDetail] = useState("");
  const [cameras, setCameras] = useState<MediaDeviceInfo[]>([]);
  const [activeCameraId, setActiveCameraId] = useState("");
  const [torchAvailable, setTorchAvailable] = useState(false);
  const [torchOn, setTorchOn] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [lastRead, setLastRead] = useState("");
  const [lastRaw, setLastRaw] = useState("");
  const [receivers, setReceivers] = useState<Receiver[]>([]);
  const [selectedReceiver, setSelectedReceiver] = useState<Receiver | null>(null);
  const [pcPickerOpen, setPcPickerOpen] = useState(false);
  const [searchingPc, setSearchingPc] = useState(false);
  const [pcSearchText, setPcSearchText] = useState("PC aranıyor");

  const ensureAbly = useCallback(async () => {
    if (ablyRef.current?.connection.state === "connected") {
      return ablyRef.current;
    }
    if (
      ablyRef.current &&
      ["failed", "closed"].includes(ablyRef.current.connection.state)
    ) {
      void ablyRef.current.close();
      ablyRef.current = null;
    }
    if (!clientIdRef.current) {
      clientIdRef.current =
        localStorage.getItem(ABLY_CLIENT_KEY) || `phone-pwa-${crypto.randomUUID()}`;
      localStorage.setItem(ABLY_CLIENT_KEY, clientIdRef.current);
    }
    if (!ablyRef.current) {
      ablyRef.current = new Ably.Realtime({
        authUrl: `/api/ably-token?clientId=${encodeURIComponent(clientIdRef.current)}`,
        echoMessages: false,
      });
    }
    const client = ablyRef.current;
    if (client.connection.state === "connected") return client;
    await new Promise<void>((resolve, reject) => {
      const timer = window.setTimeout(
        () => reject(new Error("Ably bağlantısı zaman aşımına uğradı.")),
        10000,
      );
      client.connection.once("connected", () => {
        window.clearTimeout(timer);
        resolve();
      });
      client.connection.once("failed", (change) => {
        window.clearTimeout(timer);
        reject(new Error(change.reason?.message || "Ably bağlantısı kurulamadı."));
      });
    });
    return client;
  }, []);

  const reloadForPwaUpdate = useCallback(() => {
    if (document.hidden || scanningRef.current) {
      pendingPwaReloadRef.current = true;
      return;
    }
    window.setTimeout(() => window.location.reload(), 80);
  }, []);

  const checkForPwaUpdate = useCallback(
    async (force = false) => {
      const now = Date.now();
      if (
        !force &&
        now - lastPwaUpdateCheckRef.current < PWA_UPDATE_MIN_INTERVAL_MS
      ) {
        return;
      }
      lastPwaUpdateCheckRef.current = now;
      try {
        const registration = await navigator.serviceWorker?.getRegistration();
        await registration?.update();
        const response = await fetch("/api/release?at=" + now, {
          cache: "no-store",
          credentials: "omit",
        });
        const payload = (await response.json()) as { release?: string };
        if (payload.release && payload.release !== PWA_RELEASE) {
          reloadForPwaUpdate();
        }
      } catch {
        // Güncelleme kontrolü barkod kullanımını engellemez.
      }
    },
    [reloadForPwaUpdate],
  );

  const findPcs = useCallback(async () => {
    if (searchingPcRef.current) return;
    void checkForPwaUpdate(true);
    searchingPcRef.current = true;
    setSearchingPc(true);
    setPcPickerOpen(true);
    setPcSearchText("Ably üzerinden PC’ler aranıyor…");
    setReceivers([]);
    setSelectedReceiver(null);
    const found = new Map<string, Receiver>();
    let cloudError = "";

    const publishFound = () => {
      setReceivers(
        [...found.values()].sort((a, b) => a.name.localeCompare(b.name, "tr")),
      );
    };
    const addReceiver = (receiver: Receiver) => {
      found.set(receiver.id, mergeReceiver(found.get(receiver.id), receiver));
      publishFound();
    };
    try {
      const client = await ensureAbly();
      const discovery = client.channels.get(`${CHANNEL_PREFIX}:discovery`);
      const listener = (message: Ably.Message) => {
        if (message.name !== "receiver") return;
        let payload: Partial<Receiver>;
        try {
          payload =
            typeof message.data === "string"
              ? (JSON.parse(message.data) as typeof payload)
              : (message.data as typeof payload);
        } catch {
          return;
        }
        if (!payload?.id || !payload.name || payload.online === false) return;
        addReceiver({
          id: String(payload.id),
          name: String(payload.name),
          online: true,
          lastSeen: Number(payload.lastSeen || Date.now()),
          cloud: true,
        });
      };
      await discovery.subscribe("receiver", listener);
      await discovery.publish("discover", {
        clientId: clientIdRef.current,
        requestId: crypto.randomUUID(),
        sentAt: Date.now(),
      });
      await wait(DISCOVERY_WAIT_MS);
      await discovery.unsubscribe("receiver", listener);
    } catch (error) {
      cloudError = error instanceof Error ? error.message : String(error);
    }

    const finalReceivers = [...found.values()].sort((a, b) =>
      a.name.localeCompare(b.name, "tr"),
    );
    setReceivers(finalReceivers);
    setPcSearchText(
      finalReceivers.length
        ? `${finalReceivers.length} çevrimiçi PC bulundu`
        : cloudError
          ? "Ably bağlantısı kurulamadı"
          : "Çevrimiçi PC bulunamadı",
    );
    if (cloudError && !finalReceivers.length) setCameraError(cloudError);
    searchingPcRef.current = false;
    setSearchingPc(false);
  }, [checkForPwaUpdate, ensureAbly]);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setCameraReady(false);
    setTorchOn(false);
  }, []);

  const startCamera = useCallback(
    async (requestedDeviceId?: string) => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setCameraError("Bu tarayıcı canlı kamerayı desteklemiyor.");
        setStatus("Kamera kullanılamıyor");
        return;
      }

      stopCamera();
      setCameraError("");
      setCameraReady(false);
      setStatus("Arka kamera açılıyor");

      const savedDeviceId =
        requestedDeviceId || localStorage.getItem(SAVED_CAMERA_KEY) || "";
      const preferredVideo: MediaTrackConstraints = savedDeviceId
        ? {
            deviceId: { exact: savedDeviceId },
            width: { ideal: 1920 },
            height: { ideal: 1080 },
            frameRate: { ideal: 24, max: 30 },
          }
        : {
            facingMode: { ideal: "environment" },
            width: { ideal: 1920 },
            height: { ideal: 1080 },
            frameRate: { ideal: 24, max: 30 },
          };

      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: preferredVideo,
        });
      } catch (firstError) {
        if (savedDeviceId) {
          localStorage.removeItem(SAVED_CAMERA_KEY);
          try {
            stream = await navigator.mediaDevices.getUserMedia({
              audio: false,
              video: {
                facingMode: { ideal: "environment" },
                width: { ideal: 1920 },
                height: { ideal: 1080 },
              },
            });
          } catch (fallbackError) {
            const reason =
              fallbackError instanceof Error
                ? fallbackError.message
                : String(fallbackError);
            setCameraError(`Kamera açılamadı: ${reason}`);
            setStatus("Kamera izni gerekli");
            return;
          }
        } else {
          const reason =
            firstError instanceof Error ? firstError.message : String(firstError);
          setCameraError(`Kamera açılamadı: ${reason}`);
          setStatus("Kamera izni gerekli");
          return;
        }
      }

      streamRef.current = stream;
      const track = stream.getVideoTracks()[0];
      const video = videoRef.current;
      if (!track || !video) {
        stopCamera();
        setCameraError("Kamera görüntüsü başlatılamadı.");
        return;
      }

      video.srcObject = stream;
      await video.play();

      try {
        const capabilities = track.getCapabilities() as CameraCapabilitySet;
        const advanced: Record<string, unknown> = {};
        if (capabilities.focusMode?.includes("continuous")) {
          advanced.focusMode = "continuous";
        }
        if (capabilities.zoom && capabilities.zoom.max > capabilities.zoom.min) {
          advanced.zoom = Math.min(
            capabilities.zoom.max,
            Math.max(capabilities.zoom.min, 1),
          );
        }
        if (Object.keys(advanced).length) {
          await track.applyConstraints({
            advanced: [advanced],
          } as unknown as MediaTrackConstraints);
        }
        setTorchAvailable(Boolean(capabilities.torch));
      } catch {
        setTorchAvailable(false);
      }

      const settings = track.getSettings() as CameraSettingSet;
      const currentDeviceId = settings.deviceId || "";
      if (currentDeviceId) {
        setActiveCameraId(currentDeviceId);
        localStorage.setItem(SAVED_CAMERA_KEY, currentDeviceId);
      }
      const resolution =
        settings.width && settings.height
          ? `${settings.width}×${settings.height}`
          : "çözünürlük bilinmiyor";
      const zoom = settings.zoom ? ` · ${settings.zoom.toFixed(1)}×` : "";
      setCameraDetail(`${track.label || "Arka kamera"} · ${resolution}${zoom}`);

      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const allVideo = devices.filter((device) => device.kind === "videoinput");
        const rearPattern =
          /back|rear|arka|environment|triple|dual|wide|telephoto|ultra/i;
        const frontPattern = /front|ön|user|facetime/i;
        const rearVideo = allVideo.filter(
          (device) =>
            rearPattern.test(device.label) && !frontPattern.test(device.label),
        );
        setCameras(rearVideo.length ? rearVideo : allVideo);
      } catch {
        setCameras([]);
      }

      setCameraReady(true);
      setStatus("Hazır — barkodu hizalayıp OKU’ya basın");
    },
    [stopCamera],
  );

  useEffect(() => {
    if (!initialStartRef.current) {
      initialStartRef.current = true;
      void startCamera();
      void findPcs();
    }
    if ("serviceWorker" in navigator) {
      void navigator.serviceWorker.register(`/sw.js?release=${PWA_RELEASE}`);
    }
    const visibilityHandler = () => {
      if (document.hidden) stopCamera();
      else {
        if (!streamRef.current) void startCamera();
        void checkForPwaUpdate();
      }
    };
    document.addEventListener("visibilitychange", visibilityHandler);
    return () => {
      document.removeEventListener("visibilitychange", visibilityHandler);
      stopCamera();
      void ablyRef.current?.close();
      ablyRef.current = null;
    };
  }, [checkForPwaUpdate, findPcs, startCamera, stopCamera]);

  const selectPc = (receiver: Receiver) => {
    setSelectedReceiver(receiver);
    setPcPickerOpen(false);
    setStatus(`Hazır — ${receiver.name} seçildi`);
  };

  const sendViaCloud = async (
    receiver: Receiver,
    raw: string,
    format: ScanFormat,
  ) => {
    const client = await ensureAbly();
    const jobId = crypto.randomUUID();
    const replyName = `${CHANNEL_PREFIX}:client:${clientIdRef.current}`;
    const reply = client.channels.get(replyName);
    const scanChannel = client.channels.get(
      `${CHANNEL_PREFIX}:receiver:${receiver.id}`,
    );
    const delivered = new Promise<void>((resolve, reject) => {
      const timer = window.setTimeout(
        () => reject(new Error("PC teslim onayı vermedi.")),
        10000,
      );
      const listener = async (message: Ably.Message) => {
        const payload =
          typeof message.data === "string"
            ? JSON.parse(message.data)
            : message.data;
        if (!payload || payload.id !== jobId) return;
        window.clearTimeout(timer);
        await reply.unsubscribe("delivery", listener);
        if (payload.status === "delivered") resolve();
        else reject(new Error(payload.error || "PC barkodu teslim edemedi."));
      };
      void reply.subscribe("delivery", listener).then(() =>
        scanChannel.publish("scan", {
          id: jobId,
          data: raw,
          format,
          device: "Telefon PWA",
          createdAt: Date.now(),
          replyChannel: replyName,
        }),
      ).catch((error) => {
        window.clearTimeout(timer);
        reject(error);
      });
    });
    await delivered;
  };

  const sendToPc = async (raw: string, format: ScanFormat) => {
    if (!selectedReceiver) {
      throw new Error("Önce PC BUL ile bir bilgisayar seçin.");
    }
    if (!selectedReceiver.cloud) {
      throw new Error("Seçili PC’ye ulaşılamadı.");
    }
    await sendViaCloud(selectedReceiver, raw, format);
    return "ably" as const;
  };

  const changeCamera = async () => {
    if (cameras.length < 2) return;
    const currentIndex = cameras.findIndex(
      (camera) => camera.deviceId === activeCameraId,
    );
    const next = cameras[(currentIndex + 1 + cameras.length) % cameras.length];
    if (next) await startCamera(next.deviceId);
  };

  const toggleTorch = async () => {
    const track = streamRef.current?.getVideoTracks()[0];
    if (!track || !torchAvailable) return;
    const nextValue = !torchOn;
    try {
      await track.applyConstraints({
        advanced: [{ torch: nextValue }],
      } as unknown as MediaTrackConstraints);
      setTorchOn(nextValue);
    } catch {
      setCameraError("Bu kamera ışığı web uygulamasına açmadı.");
    }
  };

  const scan = async () => {
    const video = videoRef.current;
    const scanTarget = scanTargetRef.current;
    if (!video || !scanTarget || !cameraReady || scanningRef.current) return;
    scanningRef.current = true;
    setScanning(true);
    setLastRead("");
    setLastRaw("");
    setCameraError("");
    setStatus("Aşı barkodu aranıyor");

    try {
      await new Promise<void>((resolve) =>
        window.requestAnimationFrame(() => resolve()),
      );
      const imageData = captureRegion(video, scanTarget, false);
      const results = await readBarcodes(imageData, {
        formats: ["DataMatrix", "QRCode"],
        maxNumberOfSymbols: 4,
        tryHarder: true,
        tryRotate: true,
        tryInvert: true,
        tryDownscale: true,
        tryDenoise: true,
        textMode: "Plain",
      });
      let found: ReadResult | undefined = selectCenteredBarcode(
        results,
        imageData.width,
        imageData.height,
      );
      if (!found) {
        setStatus("Hasarlı barkod için en net kare seçiliyor");
        const rescueFrames = [imageData];
        for (let frame = 0; frame < 2; frame += 1) {
          await wait(80);
          rescueFrames.push(captureRegion(video, scanTarget, false));
        }
        const rescueFrame = rescueFrames.reduce((sharpest, candidate) =>
          edgeSharpnessScore(candidate.data, candidate.width, candidate.height) >
          edgeSharpnessScore(sharpest.data, sharpest.width, sharpest.height)
            ? candidate
            : sharpest,
        );
        const rescueImage = new ImageData(
          normalizeBlueChannel(rescueFrame.data),
          rescueFrame.width,
          rescueFrame.height,
        );
        const rescueResults = await readBarcodes(rescueImage, {
          formats: ["DataMatrix", "QRCode"],
          maxNumberOfSymbols: 4,
          tryHarder: true,
          tryRotate: true,
          tryInvert: true,
          tryDownscale: true,
          tryDenoise: true,
          textMode: "Plain",
        });
        found = selectCenteredBarcode(
          rescueResults,
          rescueImage.width,
          rescueImage.height,
        );
      }

      if (!found) {
        setStatus("Okunamadı — biraz uzaklaştırıp yeniden deneyin");
        setCameraError(
          "Barkodu hedefin ortasında ve kenarlara değmeden tutun; telefonu etikete fazla yaklaştırmayın.",
        );
        return;
      }

      const raw = bytesToRaw(found);
      const format = scanFormatFor(found);
      const vaccineName = vaccineNameForBarcode(raw);
      setStatus(`${selectedReceiver?.name || "PC"} bilgisayarına gönderiliyor`);
      await sendToPc(raw, format);
      setLastRead(vaccineName || "Aşı barkodu okundu");
      setLastRaw(printableBarcode(raw));
      setStatus(
        vaccineName
          ? `Başarılı — ${vaccineName} Ably üzerinden yazıldı`
          : `Başarılı — ${selectedReceiver?.name} bilgisayarına Ably üzerinden yazıldı`,
      );
      navigator.vibrate?.(80);
      beep();
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      setStatus("Okuma sırasında hata oluştu");
      setCameraError(reason);
    } finally {
      setScanning(false);
      scanningRef.current = false;
      if (pendingPwaReloadRef.current && !document.hidden) {
        pendingPwaReloadRef.current = false;
        reloadForPwaUpdate();
      }
    }
  };

  const scanPhoto = async (file: File) => {
    if (scanningRef.current || !selectedReceiver) return;
    scanningRef.current = true;
    setScanning(true);
    setLastRead("");
    setLastRaw("");
    setCameraError("");
    setStatus("Fotoğraftaki QR kod aranıyor");

    try {
      const imageData = await imageDataFromFile(file);
      const results = await readBarcodes(imageData, {
        formats: ["QRCode"],
        maxNumberOfSymbols: 4,
        tryHarder: true,
        tryRotate: true,
        tryInvert: true,
        tryDownscale: true,
        tryDenoise: true,
        textMode: "Plain",
      });
      const found = results.find((result) => result.isValid && result.bytes.length);
      if (!found) {
        throw new Error("QR kod bulunamadı. WhatsApp ekran görüntüsünde kodun tamamı görünmelidir.");
      }

      const raw = bytesToRaw(found);
      const vaccineName = vaccineNameForBarcode(raw);
      setStatus(`${selectedReceiver.name} bilgisayarına gönderiliyor`);
      await sendToPc(raw, "QR_CODE");
      setLastRead(vaccineName || "QR kod okundu");
      setLastRaw(printableBarcode(raw));
      setStatus(`Başarılı — ${selectedReceiver.name} bilgisayarına Ably üzerinden yazıldı`);
      navigator.vibrate?.(80);
      beep();
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      setStatus("Fotoğraftaki QR kod okunamadı");
      setCameraError(reason);
    } finally {
      setScanning(false);
      scanningRef.current = false;
      if (pendingPwaReloadRef.current && !document.hidden) {
        pendingPwaReloadRef.current = false;
        reloadForPwaUpdate();
      }
    }
  };

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">TELEFON BARKOD OKUYUCU</p>
          <h1>Aşı Barkod PWA</h1>
        </div>
        <div className="header-meta">
          <span className="test-badge">ABLY BULUT</span>
          <small className="version-badge">{PWA_SHORT_VERSION}</small>
        </div>
      </header>

      <section className="pc-panel">
        <div>
          <small>BAĞLI PC</small>
          <strong>{selectedReceiver?.name || "PC seçilmedi"}</strong>
          <small>DataMatrix · QR Kod</small>
        </div>
        <button type="button" onClick={() => void findPcs()} disabled={searchingPc}>
          {searchingPc ? "ARIYOR" : "PC BUL"}
        </button>
      </section>

      <section className="status-panel" aria-live="polite">
        <span className={`status-dot ${cameraReady ? "ready" : ""}`} />
        <div>
          <strong>{status}</strong>
          <small>{cameraDetail || "Yüksek çözünürlüklü arka kamera seçiliyor"}</small>
        </div>
      </section>

      <section className="camera-stage" aria-label="Kamera ve okuma kontrolleri">
        <div className="camera-card" aria-label="Kamera görüntüsü">
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            aria-label="Aşı barkodu kamera görüntüsü"
          />
          {!cameraReady && (
            <div className="camera-placeholder">
              <span className="camera-glyph" aria-hidden="true" />
              <strong>Kamera bekleniyor</strong>
            </div>
          )}
          <div ref={scanTargetRef} className="scan-target" aria-hidden="true">
            <i className="corner top-left" />
            <i className="corner top-right" />
            <i className="corner bottom-left" />
            <i className="corner bottom-right" />
            <span>BARKOD KAREYE DEĞMESİN</span>
          </div>
          {scanning && (
            <div className="scan-progress">
              <span />
              <strong>Barkod okunuyor</strong>
            </div>
          )}
        </div>
        <input
          ref={photoInputRef}
          className="photo-input"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={(event) => {
            const file = event.currentTarget.files?.[0];
            event.currentTarget.value = "";
            if (file) void scanPhoto(file);
          }}
        />
        <button
          type="button"
          className="photo-qr-button"
          onClick={() => photoInputRef.current?.click()}
          disabled={scanning || !selectedReceiver}
        >
          FOTOĞRAFTAN QR
        </button>
        <div className="controls" aria-label="Kamera kontrolleri">
          <div className="secondary-controls">
            <button
              type="button"
              className="secondary-button"
              onClick={() => void toggleTorch()}
              disabled={!torchAvailable || !cameraReady}
            >
              {torchOn ? "IŞIK KAPAT" : "IŞIK AÇ"}
            </button>
            {cameras.length > 1 && (
              <button
                type="button"
                className="secondary-button"
                onClick={() => void changeCamera()}
                disabled={!cameraReady}
              >
                KAMERA
              </button>
            )}
            {!cameraReady && (
              <button
                type="button"
                className="secondary-button"
                onClick={() => void startCamera()}
              >
                TEKRAR AÇ
              </button>
            )}
          </div>
          <button
            type="button"
            className="scan-button"
            onClick={() => void scan()}
            disabled={!cameraReady || scanning || !selectedReceiver}
          >
            {scanning ? "ARIYOR" : "OKU"}
          </button>
        </div>
      </section>

      <section className={`result-card ${lastRead ? "success" : ""}`}>
        <p>Son okuma</p>
        <strong>{lastRead || "Henüz barkod okunmadı"}</strong>
        {lastRaw && <code>{lastRaw}</code>}
        {cameraError && <span className="error-message">{cameraError}</span>}
      </section>

      <footer>
        Aynı ağda doğrudan, farklı ağda internet üzerinden gönderir.
      </footer>

      {pcPickerOpen && (
        <div className="picker-backdrop" role="presentation">
          <section className="pc-picker" role="dialog" aria-modal="true" aria-label="PC seç">
            <div className="picker-title">
              <div>
                <h2>PC seç</h2>
                <p>{pcSearchText}</p>
              </div>
              {!searchingPc && (
                <button type="button" onClick={() => setPcPickerOpen(false)} aria-label="Kapat">
                  ×
                </button>
              )}
            </div>
            <div className="pc-list">
              {receivers.map((receiver) => (
                <button
                  type="button"
                  className="pc-row"
                  key={receiver.id}
                  onClick={() => selectPc(receiver)}
                >
                  <span>
                    <strong>{receiver.name}</strong>
                    <small>{receiverConnectionLabel(receiver)}</small>
                  </span>
                  <i aria-hidden="true">›</i>
                </button>
              ))}
              {searchingPc && !receivers.length && <div className="search-spinner" />}
              {!searchingPc && !receivers.length && (
                <p className="empty-pcs">
                  PC uygulaması kapalı veya telefonun internet bağlantısı yok.
                </p>
              )}
            </div>
            {!searchingPc && (
              <button type="button" className="search-again" onClick={() => void findPcs()}>
                TEKRAR ARA
              </button>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
