/**
 * @agent-viz/core — Canvas 2D rendering engine
 * Handles high-performance rendering of 10w+ trajectory steps
 */

export interface RenderOptions {
  width: number;
  height: number;
  devicePixelRatio?: number;
}

export class CanvasRenderer {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private dpr: number;

  constructor(canvas: HTMLCanvasElement, options: RenderOptions) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d")!;
    this.dpr = options.devicePixelRatio || window.devicePixelRatio || 1;
    this.resize(options.width, options.height);
  }

  resize(width: number, height: number) {
    this.canvas.width = width * this.dpr;
    this.canvas.height = height * this.dpr;
    this.canvas.style.width = `${width}px`;
    this.canvas.style.height = `${height}px`;
    this.ctx.scale(this.dpr, this.dpr);
  }

  clear() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }

  drawStep(x: number, y: number, text: string, color: string) {
    this.ctx.fillStyle = color;
    this.ctx.fillRect(x, y - 4, 12, 12);
    this.ctx.fillStyle = "#333";
    this.ctx.font = "12px sans-serif";
    this.ctx.fillText(text, x + 18, y + 4);
  }

  getContext(): CanvasRenderingContext2D {
    return this.ctx;
  }

  getCanvas(): HTMLCanvasElement {
    return this.canvas;
  }
}
