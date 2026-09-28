const template = document.createElement("template");
const stylesheetUrl = new URL("./pysplashx-splash.css", import.meta.url).href;

template.innerHTML = `
  <link rel="stylesheet" href="${stylesheetUrl}">
  <div class="media-frame">
    <video aria-hidden="true" preload="auto"></video>
    <img aria-hidden="true" hidden alt="">
    <button type="button" aria-label="Skip startup video">Skip</button>
  </div>
`;

class PySplashXSplash extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.append(template.content.cloneNode(true));
    this.mediaFrame = this.shadowRoot.querySelector(".media-frame");
    this.video = this.shadowRoot.querySelector("video");
    this.image = this.shadowRoot.querySelector('img');
    this.skipButton = this.shadowRoot.querySelector("button");
    this.timeoutId = null;
    this.finished = false;
    this.onEnded = () => this.endMedia();
    this.onError = () => this.finish("media-error");
    this.onSkip = () => this.finish("skipped");
    this.onLoadedMetadata = () => {
      this.video.currentTime = this.boundedInteger('start-pos-ms', 0, 0, 86400000) / 1000;
      this.applyMediaGeometry();
    };
    this.onImageLoad = () => this.applyMediaGeometry();
    this.onTimeUpdate = () => {
      const end = this.boundedInteger('end-pos-ms', 0, 0, 86400000) / 1000;
      if (end && this.video.currentTime >= end) this.endMedia();
    };
    this.onMediaClick = () => {
      if (this.getAttribute('close-on-click') !== 'false') this.finish('clicked');
    };
    this.onResize = () => this.applyMediaGeometry();
    this.onKeyDown = (event) => {
      if (event.key === "Escape") {
        this.finish("skipped");
      }
    };
  }

  connectedCallback() {
    if (this.getAttribute("enabled")?.toLowerCase() === "false") {
      this.finish("disabled");
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      this.finish("reduced-motion");
      return;
    }
    if (this.oncePerSession && this.wasShownThisSession()) {
      this.finish("already-shown");
      return;
    }

    const source = this.getAttribute("src");
    if (!source) {
      this.finish("missing-source");
      return;
    }

    this.applyShape();
    this.applyMask();
    this.applyMediaGeometry();
    const isImage = this.getAttribute('media-type') === 'image';
    this.video.hidden = isImage;
    this.image.hidden = !isImage;
    this.mediaFrame.addEventListener('click', this.onMediaClick);
    this.video.autoplay = true;
    this.video.muted = true;
    this.video.defaultMuted = true;
    this.video.playsInline = true;
    this.video.poster = this.getAttribute("poster") || "";
    if (isImage) {
      this.image.addEventListener('load', this.onImageLoad);
      this.image.addEventListener('error', this.onError);
      this.image.src = source;
    } else this.video.src = source;
    this.video.addEventListener("ended", this.onEnded);
    this.video.addEventListener("error", this.onError, { once: true });
    this.video.addEventListener("loadedmetadata", this.onLoadedMetadata);
    this.video.addEventListener('timeupdate', this.onTimeUpdate);
    this.skipButton.addEventListener("click", this.onSkip);
    document.addEventListener("keydown", this.onKeyDown);
    window.addEventListener("resize", this.onResize);
    this.markShownThisSession();

    const duration = Number.parseInt(this.getAttribute("max-duration-ms") || "15000", 10);
    const boundedDuration = Number.isFinite(duration) && duration > 0 ? duration : 15000;
    const imageDuration = this.boundedInteger('static-duration-ms', 5000, 0, 86400000);
    const durationLimit = isImage && imageDuration > 0
      ? Math.min(boundedDuration, imageDuration)
      : boundedDuration;
    this.timeoutId = window.setTimeout(() => this.finish("timeout"), durationLimit);

    if (isImage) return;

    try {
      const playback = this.video.play();
      if (playback && typeof playback.catch === "function") {
        playback.catch(() => this.finish("autoplay-blocked"));
      }
    } catch (_error) {
      this.finish("autoplay-blocked");
    }
  }

  disconnectedCallback() {
    this.cleanup();
  }

  get oncePerSession() {
    return this.getAttribute("once-per-session")?.toLowerCase() !== "false";
  }

  get sessionKey() {
    return this.getAttribute("session-key") || "pysplashx:shown";
  }

  wasShownThisSession() {
    try {
      return window.sessionStorage.getItem(this.sessionKey) === "1";
    } catch (_error) {
      return false;
    }
  }

  markShownThisSession() {
    if (!this.oncePerSession) {
      return;
    }
    try {
      window.sessionStorage.setItem(this.sessionKey, "1");
    } catch (_error) {
      // Storage can be unavailable in privacy-restricted contexts.
    }
  }

  boundedInteger(name, fallback, minimum, maximum) {
    const parsed = Number.parseInt(this.getAttribute(name) || "", 10);
    if (!Number.isFinite(parsed)) {
      return fallback;
    }
    return Math.min(maximum, Math.max(minimum, parsed));
  }

  applyShape() {
    const shape = (this.getAttribute("shape") || "rect").toLowerCase();
    const radius = this.boundedInteger("radius-px", 0, 0, 1000);
    if (shape === "oval") {
      this.mediaFrame.style.borderRadius = "50%";
    } else if (shape === "rounded") {
      this.mediaFrame.style.borderRadius = `${radius}px`;
    } else {
      this.mediaFrame.style.borderRadius = "0";
    }
  }

  applyMediaGeometry() {
    const scalePercent = this.boundedInteger("scale-percent", 45, 1, 100);
    const percent = scalePercent;
    this.style.setProperty('--pysplashx-scale-percent', percent);
    const maximumWidth = Math.max(1, window.innerWidth * percent / 100);
    const maximumHeight = Math.max(1, window.innerHeight * percent / 100);
    const isImage = this.getAttribute('media-type') === 'image';
    const nativeWidth = (isImage ? this.image.naturalWidth : this.video.videoWidth) || 1;
    const nativeHeight = (isImage ? this.image.naturalHeight : this.video.videoHeight) || 1;
    const fitScale = isImage
      ? Math.min(scalePercent / 100, window.innerWidth * 0.95 / nativeWidth, window.innerHeight * 0.95 / nativeHeight)
      : Math.min(maximumWidth / nativeWidth, maximumHeight / nativeHeight);
    this.mediaFrame.style.width = `${Math.max(1, Math.floor(nativeWidth * fitScale))}px`;
    this.mediaFrame.style.height = `${Math.max(1, Math.floor(nativeHeight * fitScale))}px`;

    const aspectMode = (this.getAttribute("aspect-ratio-mode") || "fit").toLowerCase();
    this.video.style.objectFit = aspectMode === "expand"
      ? "cover"
      : aspectMode === "ignore" ? "fill" : "contain";
  }

  endMedia() {
    const behavior = this.getAttribute('loop-behavior') || 'close';
    if (behavior === 'replay') {
      this.video.currentTime = this.boundedInteger('start-pos-ms', 0, 0, 86400000) / 1000;
      this.video.play().catch(() => this.finish('playback-error'));
    } else if (behavior === 'freeze') this.video.pause();
    else this.finish('ended');
  }

  applyMask() {
    if (this.getAttribute('shape') !== 'png_mask') return;
    const source = this.getAttribute('mask-src');
    if (!source) return;
    const mask = new Image();
    mask.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = mask.naturalWidth; canvas.height = mask.naturalHeight;
      const context = canvas.getContext('2d');
      context.drawImage(mask, 0, 0);
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height);
      const threshold = this.boundedInteger('mask-threshold', 128, 0, 255);
      for (let index = 3; index < pixels.data.length; index += 4) {
        pixels.data[index] = pixels.data[index] >= threshold ? 255 : 0;
      }
      context.putImageData(pixels, 0, 0);
      this.mediaFrame.style.maskImage = `url("${canvas.toDataURL()}")`;
      this.mediaFrame.style.maskSize = '100% 100%';
    };
    mask.onerror = () => this.finish('mask-error');
    mask.src = source;
  }

  skip() {
    this.finish("skipped");
  }

  finish(reason) {
    if (this.finished) {
      return;
    }
    this.finished = true;
    this.cleanup();
    this.hidden = true;
    this.dispatchEvent(
      new CustomEvent("pysplashx-complete", {
        bubbles: true,
        composed: true,
        detail: { reason },
      }),
    );
  }

  cleanup() {
    if (this.timeoutId !== null) {
      window.clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }
    this.video.pause();
    this.video.removeEventListener("ended", this.onEnded);
    this.video.removeEventListener("error", this.onError);
    this.video.removeEventListener("loadedmetadata", this.onLoadedMetadata);
    this.video.removeEventListener('timeupdate', this.onTimeUpdate);
    this.image.removeEventListener('load', this.onImageLoad);
    this.image.removeEventListener('error', this.onError);
    this.mediaFrame.removeEventListener('click', this.onMediaClick);
    this.skipButton.removeEventListener("click", this.onSkip);
    document.removeEventListener("keydown", this.onKeyDown);
    window.removeEventListener("resize", this.onResize);
  }
}

if (!customElements.get("pysplashx-splash")) {
  customElements.define("pysplashx-splash", PySplashXSplash);
}
