/* TutorDraw lesson player. Plain JavaScript, no dependencies.
 *
 *   const player = new TutorDrawPlayer(element, {width, height, title});
 *   player.append(step);   // a Tutorial.web_step() payload, as soon as it exists
 *   player.play();
 *
 * Steps may arrive while the lesson plays: the player plays what it has and
 * waits at the end of the last one until the next arrives, which is how a
 * lesson streams while a model is still writing it.
 *
 * Each step carries its finished frame as SVG and, when it animates, its
 * earlier `frames`. Elements present in all of them are matched by
 * data-drawcv-id and every numeric attribute whose shape matches is
 * interpolated (transforms, path data, positions, colours, opacity): with one
 * earlier frame through DrawCV's own easing curve sampled into `easing`, with
 * several (a moving camera) piecewise between evenly timed keyframes. Reveals and draw-on come from data-td-at and
 * data-td-draw. The SVG is drawn at its native size and scaled with a CSS
 * transform, because DrawCV strokes are non-scaling: scaling the viewBox
 * instead would fatten every line on a small screen.
 */
(function (global) {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";
  const NUMBER = /-?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?/gi;
  const TWEENED = ["transform", "d", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r",
    "rx", "ry", "width", "height", "points", "fill", "stroke", "opacity",
    "fill-opacity", "stroke-opacity", "stroke-width", "textLength", "font-size"];
  const DRAWABLE = "path, line, polyline, polygon, rect, circle, ellipse";

  function parse(svgText) {
    const doc = new DOMParser().parseFromString(svgText, "image/svg+xml");
    return document.importNode(doc.documentElement, true);
  }

  function template(value) {
    return value.replace(NUMBER, "#");
  }

  function numbers(value) {
    return (value.match(NUMBER) || []).map(Number);
  }

  function fill(skeleton, values) {
    let i = 0;
    return skeleton.replace(/#/g, () => {
      const v = values[i++];
      return Number.isInteger(v) ? String(v) : v.toFixed(3);
    });
  }

  function elementsOf(group) {
    return [group, ...group.querySelectorAll("*")];
  }

  /* Pair every element of the live (final) frame with its counterparts in the
   * earlier frames, and record each attribute whose shape matches in all of
   * them: values[k] holds its numbers in frame k, the last being the final. */
  function buildTweens(live, earlier) {
    const tweens = [];
    const indexes = earlier.map(frame => {
      const map = new Map();
      frame.querySelectorAll("[data-drawcv-id]").forEach(g => map.set(g.getAttribute("data-drawcv-id"), g));
      return map;
    });
    live.querySelectorAll("[data-drawcv-id]").forEach(group => {
      const id = group.getAttribute("data-drawcv-id");
      const final = elementsOf(group);
      const others = indexes.map(map => map.get(id));
      if (others.some(g => !g)) return;
      const lists = others.map(elementsOf);
      if (lists.some(list => list.length !== final.length ||
          list.some((el, i) => el.tagName !== final[i].tagName))) return;
      final.forEach((el, i) => {
        for (const name of TWEENED) {
          const to = el.getAttribute(name);
          if (to === null) continue;
          const froms = lists.map(list => list[i].getAttribute(name));
          if (froms.some(v => v === null || template(v) !== template(to))) continue;
          if (froms.every(v => v === to)) continue;
          const values = [...froms.map(numbers), numbers(to)];
          if (values.some(v => v.length !== values[0].length)) continue;
          tweens.push({el, name, skeleton: template(to), values});
        }
      });
    });
    return tweens;
  }

  function ease(table, p) {
    if (!table) return 1;
    const x = Math.min(Math.max(p, 0), 1) * (table.length - 1);
    const i = Math.min(Math.floor(x), table.length - 2);
    return table[i] + (table[i + 1] - table[i]) * (x - i);
  }

  class TutorDrawPlayer {
    constructor(root, options = {}) {
      this.root = root;
      this.width = options.width || 800;
      this.height = options.height || 450;
      this.steps = [];
      this.index = 0;
      this.time = 0;
      this.playing = false;
      this.loaded = -1;
      this.last = null;
      this.onstep = null;
      this._build(options.title || "");
      this._tick = this._tick.bind(this);
    }

    /* ---- public API ---- */

    append(step) {
      this.steps[step.index === undefined ? this.steps.length : step.index] = step;
      this._renderDots();
      if (this.loaded < 0 && this.steps[0]) this._load(0);
      this._status();
    }

    play() {
      if (this.playing) return;
      this.playing = true;
      this.last = null;
      requestAnimationFrame(this._tick);
      this._status();
    }

    pause() {
      this.playing = false;
      this._status();
    }

    seek(index, time = 0) {
      if (!this.steps[index]) return;
      this._load(index);
      this.time = time;
      this._apply();
    }

    /* ---- internals ---- */

    _build(title) {
      this.root.innerHTML = "";
      const style = document.createElement("style");
      style.textContent = `
        .td-player{font:14px system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:#e8ecf3}
        .td-frame{position:relative;overflow:hidden;background:#fff;border-radius:6px}
        .td-frame > div{position:absolute;left:0;top:0;transform-origin:0 0}
        .td-bar{display:flex;align-items:center;gap:10px;padding:10px 2px}
        .td-bar button{background:#2c3442;color:#e8ecf3;border:0;border-radius:4px;padding:6px 12px;cursor:pointer;font:inherit}
        .td-bar button:hover{background:#3a4557}
        .td-title{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .td-dots{display:flex;gap:4px;padding:0 2px 6px}
        .td-dot{flex:1;height:4px;border-radius:2px;background:#3a4557;cursor:pointer;position:relative;overflow:hidden}
        .td-dot i{position:absolute;left:0;top:0;bottom:0;background:#e8a53a}
        .td-dot.pending{background:#2a303b;cursor:default}
        .td-status{color:#9aa6b8;font-size:12px}`;
      const wrap = document.createElement("div");
      wrap.className = "td-player";
      wrap.setAttribute("aria-label", title);
      this.frame = document.createElement("div");
      this.frame.className = "td-frame";
      this.stage = document.createElement("div");
      this.stage.style.width = this.width + "px";
      this.stage.style.height = this.height + "px";
      this.frame.appendChild(this.stage);
      this.dots = document.createElement("div");
      this.dots.className = "td-dots";
      const bar = document.createElement("div");
      bar.className = "td-bar";
      const button = (label, action) => {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = label;
        b.addEventListener("click", action);
        bar.appendChild(b);
        return b;
      };
      button("◀", () => this.seek(Math.max(this.index - 1, 0)));
      this.toggle = button("Play", () => (this.playing ? this.pause() : this.play()));
      button("▶", () => this.seek(Math.min(this.index + 1, this.steps.length - 1)));
      this.titleEl = document.createElement("div");
      this.titleEl.className = "td-title";
      bar.appendChild(this.titleEl);
      this.statusEl = document.createElement("div");
      this.statusEl.className = "td-status";
      bar.appendChild(this.statusEl);
      wrap.append(style, this.frame, this.dots, bar);
      this.root.appendChild(wrap);
      const resize = () => {
        const scale = this.frame.clientWidth / this.width;
        this.stage.style.transform = `scale(${scale})`;
        this.frame.style.height = this.height * scale + "px";
      };
      new ResizeObserver(resize).observe(this.frame);
      resize();
    }

    _renderDots() {
      this.dots.innerHTML = "";
      this.steps.forEach((step, i) => {
        const dot = document.createElement("div");
        dot.className = "td-dot" + (step ? "" : " pending");
        dot.title = step ? step.title : "not yet received";
        dot.appendChild(document.createElement("i"));
        if (step) dot.addEventListener("click", () => this.seek(i));
        this.dots.appendChild(dot);
      });
    }

    _load(index) {
      const step = this.steps[index];
      this.index = index;
      this.loaded = index;
      this.time = 0;
      this.svg = parse(step.svg);
      this.stage.replaceChildren(this.svg);
      this.tweens = step.frames && step.frames.length ? buildTweens(this.svg, step.frames.map(parse)) : [];
      this.timed = [...this.svg.querySelectorAll("[data-td-at]")].map(group => {
        const draw = parseFloat(group.getAttribute("data-td-draw") || "0");
        const shapes = draw ? [...group.querySelectorAll(DRAWABLE)].filter(s => s.getTotalLength) : [];
        return {
          group, at: parseFloat(group.getAttribute("data-td-at")), draw,
          shapes: shapes.map(s => ({el: s, length: s.getTotalLength() || 0}))
        };
      });
      this.titleEl.textContent = `${index + 1}. ${step.title}`;
      if (this.onstep) this.onstep(index, step);
      this._apply();
    }

    _apply() {
      const step = this.steps[this.index];
      const t = this.time, done = t >= step.duration;
      // One earlier frame eases toward the final one with DrawCV's curve;
      // several are evenly timed with easing applied, so blend neighbours.
      const segments = step.frames ? step.frames.length : 0;
      let seg = Math.max(segments - 1, 0), local = 1;
      if (!done && segments) {
        const p = Math.max(t / step.duration, 0);
        if (segments === 1) {
          seg = 0;
          local = ease(step.easing, p);
        } else {
          const position = p * segments;
          seg = Math.min(Math.floor(position), segments - 1);
          local = position - seg;
        }
      }
      for (const tw of this.tweens) {
        const a = tw.values[seg], b = tw.values[seg + 1];
        tw.el.setAttribute(tw.name, fill(tw.skeleton, a.map((v, i) => v + (b[i] - v) * local)));
      }
      for (const item of this.timed) {
        const shown = done || t >= item.at;
        item.group.style.visibility = shown ? "" : "hidden";
        const p = done ? 1 : item.draw ? Math.min(Math.max((t - item.at) / item.draw, 0), 1) : 1;
        for (const s of item.shapes) {
          if (p >= 1) {
            s.el.style.strokeDasharray = "";
            s.el.style.strokeDashoffset = "";
          } else {
            s.el.style.strokeDasharray = `${s.length} ${s.length}`;
            s.el.style.strokeDashoffset = String(s.length * (1 - p));
          }
        }
      }
      [...this.dots.children].forEach((dot, i) => {
        const s = this.steps[i];
        const fillBar = dot.firstChild;
        const total = s ? s.duration + s.pause : 1;
        fillBar.style.width = i < this.index ? "100%" : i > this.index ? "0" :
          Math.min(100, (t / total) * 100) + "%";
      });
    }

    _status() {
      const waiting = this.playing && !this.steps[this.index + 1] &&
        this.steps[this.index] && this.time >= this.steps[this.index].duration + this.steps[this.index].pause;
      this.toggle.textContent = this.playing ? "Pause" : "Play";
      this.statusEl.textContent = this.loaded < 0 ? "waiting for the first step…" :
        waiting ? "waiting for the next step…" : "";
    }

    _tick(now) {
      if (!this.playing) return;
      if (this.loaded >= 0) {
        const dt = this.last === null ? 0 : (now - this.last) / 1000;
        this.time += dt;
        const step = this.steps[this.index];
        if (this.time >= step.duration + step.pause) {
          if (this.steps[this.index + 1]) {
            this._load(this.index + 1);
          } else {
            this.time = step.duration + step.pause;  // hold on the last frame
          }
        }
        this._apply();
        this._status();
      }
      this.last = now;
      requestAnimationFrame(this._tick);
    }
  }

  global.TutorDrawPlayer = TutorDrawPlayer;
})(typeof window !== "undefined" ? window : globalThis);
