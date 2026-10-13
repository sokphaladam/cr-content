/** One scene on the timeline: its voiceover (`key`, null for a silent scene) and the stretches cut out of it. */
export interface PlayerSegment {
  length: number; // seconds on the video's timeline (0 = skipped)
  key: string | null;
  duration: number; // of the voiceover file
  cuts: [number, number][];
}

/**
 * Plays a draft's scenes back to back like the render will: each scene's voiceover with its cut pauses skipped,
 * the breath of silence after it, and silent scenes as time passing. Reports the playhead as (scene, seconds into
 * its voiceover). Plain class, so the audio clock lives outside React's render.
 */
export class TimelinePlayer {
  private segs: PlayerSegment[] = [];
  private pad = 0.25;
  private audio: HTMLAudioElement | null = null;
  private mode: "stopped" | "audio" | "silent" | "pad" = "stopped";
  private i = 0;
  private since = 0;
  private frame = 0;

  constructor(
    private url: (key: string) => string,
    private onPos: (i: number, t: number) => void,
    private onPlaying: (playing: boolean) => void,
  ) {}

  get playing() {
    return this.mode !== "stopped";
  }

  /** New timeline (after an edit). Stops when the voiceover under the playhead was replaced. */
  update(segs: PlayerSegment[], pad: number) {
    this.segs = segs;
    this.pad = pad;
    const seg = segs[this.i];
    if (this.mode === "audio" && (!seg?.key || this.audio?.src !== this.url(seg.key))) this.stop();
  }

  play(i: number, t: number) {
    this.onPlaying(true);
    this.startAt(i, t);
    cancelAnimationFrame(this.frame);
    this.frame = requestAnimationFrame(this.tick);
  }

  seek(i: number, t: number) {
    if (this.playing) this.startAt(i, t);
    else this.onPos(i, t);
  }

  stop() {
    cancelAnimationFrame(this.frame);
    this.mode = "stopped";
    this.audio?.pause();
    this.onPlaying(false);
  }

  private startAt(index: number, offset: number) {
    let i = index;
    let t = offset;
    while (i < this.segs.length && this.segs[i].length <= 0) {
      i += 1;
      t = 0;
    }
    if (i >= this.segs.length) {
      this.stop();
      this.onPos(0, 0);
      return;
    }
    const seg = this.segs[i];
    this.i = i;
    this.onPos(i, t);
    if (seg.key) {
      this.audio ??= new Audio();
      const src = this.url(seg.key);
      if (this.audio.src !== src) this.audio.src = src;
      this.audio.currentTime = t;
      this.mode = "audio";
      this.audio.play().catch(() => this.stop());
    } else {
      this.audio?.pause();
      this.mode = "silent";
      this.since = performance.now() - t * 1000;
    }
  }

  private tick = () => {
    if (this.mode === "stopped") return;
    const seg = this.segs[this.i];
    if (!seg) return this.stop();
    if (this.mode === "audio" && this.audio) {
      let t = this.audio.currentTime;
      const cut = seg.cuts.find(([a, b]) => t >= a && t < b);
      if (cut) {
        this.audio.currentTime = cut[1];
        t = cut[1];
      }
      this.onPos(this.i, t);
      if (this.audio.ended || t >= seg.duration - 0.02) {
        this.mode = "pad";
        this.since = performance.now();
      }
    } else if (this.mode === "pad") {
      if (performance.now() - this.since >= this.pad * 1000) this.startAt(this.i + 1, 0);
    } else if (this.mode === "silent") {
      const t = (performance.now() - this.since) / 1000;
      this.onPos(this.i, Math.min(t, seg.length));
      if (t >= seg.length) this.startAt(this.i + 1, 0);
    }
    this.frame = requestAnimationFrame(this.tick);
  };
}
