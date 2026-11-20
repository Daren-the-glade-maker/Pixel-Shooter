import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import zlib from "node:zlib";

// Official Thumby Color button bitmasks from TinyCircuits-MicroPython-Editor
// (app/src/components/SimulatorPanel.jsx)
export const BUTTONS = {
    A:            0b0000000000000001,
    B:            0b0000000000000010,
    UP:           0b0000000000000100,
    DOWN:         0b0000000000001000,
    LEFT:         0b0000000000010000,
    RIGHT:        0b0000000000100000,
    LB:           0b0000000001000000,
    RB:           0b0000000010000000,
    MENU:         0b0000000100000000,
};

const OFFICIAL_REPO = "TinyCircuits/TinyCircuits-MicroPython-Editor";
const EMULATOR_FILES = [
    { name: "micropython.mjs", repoPath: "app/src/js/micropython.mjs" },
    { name: "micropython.wasm", repoPath: "app/src/js/micropython.wasm" },
];

/**
 * Ensures the official Thumby Color WebAssembly emulator files from
 * TinyCircuits/TinyCircuits-MicroPython-Editor exist in cacheDir.
 */
export async function ensureOfficialEmulator(cacheDir) {
    fs.mkdirSync(cacheDir, { recursive: true });
    for (const file of EMULATOR_FILES) {
        const dest = path.join(cacheDir, file.name);
        if (fs.existsSync(dest) && fs.statSync(dest).size > 1024) {
            continue;
        }
        // Prefer gh CLI (works through api.github.com), fall back to fetch
        let downloaded = false;
        try {
            const buf = execFileSync(
                "gh",
                ["api", "-H", "Accept: application/vnd.github.raw+json", `repos/${OFFICIAL_REPO}/contents/${file.repoPath}`],
                { maxBuffer: 16 * 1024 * 1024 }
            );
            fs.writeFileSync(dest, buf);
            downloaded = true;
        } catch {
            // Fall back to direct GitHub raw download
        }
        if (!downloaded) {
            const url = `https://github.com/${OFFICIAL_REPO}/raw/master/${file.repoPath}`;
            const res = await fetch(url);
            if (!res.ok) {
                throw new Error(`Failed to fetch ${url}: HTTP ${res.status}`);
            }
            const ab = await res.arrayBuffer();
            fs.writeFileSync(dest, Buffer.from(ab));
        }
    }
    return {
        mjsPath: path.join(cacheDir, "micropython.mjs"),
        wasmPath: path.join(cacheDir, "micropython.wasm"),
    };
}

// Minimal CRC32 + PNG writer (zero external npm dependencies)
const CRC_TABLE = (() => {
    const tbl = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
        let c = n;
        for (let k = 0; k < 8; k++) {
            c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
        }
        tbl[n] = c >>> 0;
    }
    return tbl;
})();

function crc32(buf) {
    let c = 0xFFFFFFFF;
    for (let i = 0; i < buf.length; i++) {
        c = CRC_TABLE[(c ^ buf[i]) & 0xFF] ^ (c >>> 8);
    }
    return (c ^ 0xFFFFFFFF) >>> 0;
}

function pngChunk(type, data) {
    const typeBuf = Buffer.from(type, "ascii");
    const lenBuf = Buffer.alloc(4);
    lenBuf.writeUInt32BE(data.length, 0);
    const crcInput = Buffer.concat([typeBuf, data]);
    const crcBuf = Buffer.alloc(4);
    crcBuf.writeUInt32BE(crc32(crcInput), 0);
    return Buffer.concat([lenBuf, typeBuf, data, crcBuf]);
}

export function rgb565ToRgba(rgb565Bytes) {
    const rgba = new Uint8Array(128 * 128 * 4);
    for (let i = 0; i < 128 * 128; i++) {
        const px = rgb565Bytes[i * 2] | (rgb565Bytes[i * 2 + 1] << 8);
        const r5 = (px >> 11) & 0x1F;
        const g6 = (px >> 5) & 0x3F;
        const b5 = px & 0x1F;
        rgba[i * 4]     = (r5 << 3) | (r5 >> 2);
        rgba[i * 4 + 1] = (g6 << 2) | (g6 >> 4);
        rgba[i * 4 + 2] = (b5 << 3) | (b5 >> 2);
        rgba[i * 4 + 3] = 255;
    }
    return rgba;
}

export function saveRgb565AsPng(rgb565Bytes, outPath, scale = 1) {
    const rgba = rgb565ToRgba(rgb565Bytes);
    const w = 128 * scale;
    const h = 128 * scale;
    const raw = Buffer.alloc(h * (1 + w * 4));
    for (let y = 0; y < h; y++) {
        const sy = Math.floor(y / scale);
        const rowOff = y * (1 + w * 4);
        raw[rowOff] = 0; // filter: None
        for (let x = 0; x < w; x++) {
            const sx = Math.floor(x / scale);
            const src = (sy * 128 + sx) * 4;
            const dst = rowOff + 1 + x * 4;
            raw[dst]     = rgba[src];
            raw[dst + 1] = rgba[src + 1];
            raw[dst + 2] = rgba[src + 2];
            raw[dst + 3] = rgba[src + 3];
        }
    }
    const ihdr = Buffer.alloc(13);
    ihdr.writeUInt32BE(w, 0);
    ihdr.writeUInt32BE(h, 4);
    ihdr[8] = 8;  // bit depth
    ihdr[9] = 6;  // RGBA
    ihdr[10] = 0;
    ihdr[11] = 0;
    ihdr[12] = 0;

    const idat = zlib.deflateSync(raw, { level: 6 });
    const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
    const png = Buffer.concat([
        sig,
        pngChunk("IHDR", ihdr),
        pngChunk("IDAT", idat),
        pngChunk("IEND", Buffer.alloc(0)),
    ]);
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, png);
}

/**
 * Headless Node.js host for the official TinyCircuits Thumby Color WebAssembly emulator.
 */
export class ThumbyColorHeadlessEmulator {
    constructor({ cacheDir }) {
        this.cacheDir = cacheDir;
        this.mp = null;
        this.pressedMask = 0;
        this.frameCount = 0;
        this.lastFrame = new Uint8Array(128 * 128 * 2);
        this.stdoutLines = [];
        this.stderrLines = [];
        this.onFrame = null;
    }

    async init() {
        const { mjsPath } = await ensureOfficialEmulator(this.cacheDir);
        const { loadMicroPython } = await import(pathToFileURL(mjsPath).href);

        globalThis.self = globalThis;
        globalThis.main_call = () => {};
        globalThis.get_pressed_buttons = () => this.pressedMask;
        globalThis.update_display = (ptr) => {
            this.frameCount++;
            this.lastFrame = new Uint8Array(
                this.mp._module.HEAPU8.subarray(ptr, ptr + 128 * 128 * 2)
            );
            if (this.onFrame) {
                this.onFrame(this.frameCount, this.lastFrame);
            }
        };

        this.mp = await loadMicroPython({
            stdout: (line) => this.stdoutLines.push(line),
            stderr: (line) => this.stderrLines.push(line),
            // Exact hardware SRAM (520KB) + flash scratch (2MiB) heapsize from simulator-worker.js
            heapsize: (520 * 1000) + (2 * 1024 * 1024),
            linebuffer: true,
        });

        this.mp.FS.mkdirTree("/system");
        this.mp.FS.mkdirTree("/Games");
        this.mp.FS.mkdirTree("/Saves");
    }

    mountDirectory(hostDir, virtualDir) {
        this.mp.FS.mkdirTree(virtualDir);
        for (const entry of fs.readdirSync(hostDir, { withFileTypes: true })) {
            const srcPath = path.join(hostDir, entry.name);
            const dstPath = `${virtualDir}/${entry.name}`;
            if (entry.isDirectory()) {
                this.mountDirectory(srcPath, dstPath);
            } else if (entry.isFile()) {
                this.mp.FS.writeFile(dstPath, fs.readFileSync(srcPath));
            }
        }
    }

    setButtons(mask) {
        this.pressedMask = mask;
    }

    async runPython(code) {
        // Use mp_js_do_exec_async with proper await on the Emscripten ASYNCIFY
        // Promise (upstream micropython.mjs omits await, causing premature reads
        // whenever MicroPython's GC triggers an ASYNCIFY yield).
        const M = this.mp._module;
        const len = M.lengthBytesUTF8(code);
        const buf = M._malloc(len + 1);
        M.stringToUTF8(code, buf, len + 1);
        const value = M._malloc(3 * 4);
        M.setValue(value, 0, "i32");
        try {
            await M.ccall(
                "mp_js_do_exec_async",
                "number",
                ["pointer", "number", "pointer"],
                [buf, len, value],
                { async: true }
            );
            const kind = M.getValue(value, "i32");
            if (kind === -1) { // PROXY_KIND_MP_EXCEPTION
                const strLen = M.getValue(value + 4, "i32");
                const strPtr = M.getValue(value + 8, "i32");
                const str = M.UTF8ToString(strPtr, strLen);
                M._free(strPtr);
                const [errType, errMsg] = str.split("\x04");
                const err = new Error(errMsg || errType || "PythonError");
                err.name = errType || "PythonError";
                throw err;
            }
            if (kind === 5) { // PROXY_KIND_MP_STR
                const strLen = M.getValue(value + 4, "i32");
                const strPtr = M.getValue(value + 8, "i32");
                const str = M.UTF8ToString(strPtr, strLen);
                M._free(strPtr);
                return str;
            }
            return null;
        } catch (err) {
            console.error("[EMU ERROR] code:", code.slice(0, 120));
            console.error("[EMU ERROR] stdout tail:", this.stdoutLines.slice(-8));
            console.error("[EMU ERROR] stderr tail:", this.stderrLines.slice(-8));
            throw err;
        } finally {
            M._free(buf);
            M._free(value);
        }
    }

    getFrameCopy() {
        return new Uint8Array(this.lastFrame);
    }

    saveScreenshot(outPath, scale = 4) {
        saveRgb565AsPng(this.lastFrame, outPath, scale);
    }
}
