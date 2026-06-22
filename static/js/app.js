let sessionId = null;
let currentImageData = null;
let undoStack = [];
let redoStack = [];
let isGenerating = false;
let adjustTimeout = null;

const API_BASE = '/api';

function showToast(msg, duration = 2000) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  clearTimeout(t._timeout);
  t._timeout = setTimeout(() => t.classList.add('hidden'), duration);
}

function showLoading(text = 'Processing...') {
  document.getElementById('loadingText').textContent = text;
  document.getElementById('loadingOverlay').classList.remove('hidden');
}

function hideLoading() {
  document.getElementById('loadingOverlay').classList.add('hidden');
}

function switchTab(tab) {
  document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelector(`.sidebar-tab[data-tab="${tab}"]`).classList.add('active');
  document.getElementById(`tab-${tab}`).classList.add('active');
}

function updateImageDisplay(b64, w, h) {
  const img = document.getElementById('canvas');
  const placeholder = document.getElementById('canvasPlaceholder');
  img.src = 'data:image/png;base64,' + b64;
  img.classList.remove('hidden');
  placeholder.classList.add('hidden');
  document.getElementById('imageInfo').textContent = `${w} × ${h} px`;
  document.getElementById('statusText').textContent = 'Image loaded';
}

function clearCanvas() {
  document.getElementById('canvas').classList.add('hidden');
  document.getElementById('canvasPlaceholder').classList.remove('hidden');
  document.getElementById('imageInfo').textContent = 'No image loaded';
  currentImageData = null;
}

/* ==================== GENERATION ==================== */

const genParamDefs = {
  mandelbrot: `
    <div class="param-group"><label>Max Iterations</label><input type="range" id="p_max_iter" min="16" max="1024" value="256"><span id="p_max_iter_val">256</span></div>
    <div class="param-group"><label>Power</label><select id="p_power"><option value="2">2</option><option value="3">3</option><option value="4">4</option></select></div>
    <div class="param-group"><label>Coloring</label><select id="p_coloring"><option value="spectral">Spectral</option><option value="fire">Fire</option><option value="ocean">Ocean</option><option value="neon">Neon</option><option value="gray">Gray</option></select></div>
    <div class="param-group"><label>X Min</label><input type="number" id="p_x_min" value="-2.5" step="0.1"></div>
    <div class="param-group"><label>X Max</label><input type="number" id="p_x_max" value="1.5" step="0.1"></div>
    <div class="param-group"><label>Y Min</label><input type="number" id="p_y_min" value="-1.5" step="0.1"></div>
    <div class="param-group"><label>Y Max</label><input type="number" id="p_y_max" value="1.5" step="0.1"></div>
  `,
  julia: `
    <div class="param-group"><label>Max Iterations</label><input type="range" id="p_max_iter" min="16" max="1024" value="256"><span id="p_max_iter_val">256</span></div>
    <div class="param-group"><label>Power</label><select id="p_power"><option value="2">2</option><option value="3">3</option><option value="4">4</option></select></div>
    <div class="param-group"><label>Coloring</label><select id="p_coloring"><option value="spectral">Spectral</option><option value="fire">Fire</option><option value="ocean">Ocean</option><option value="neon">Neon</option><option value="gray">Gray</option></select></div>
    <div class="param-group"><label>Julia C Real</label><input type="range" id="p_julia_cr" min="-2" max="2" step="0.01" value="-0.7"><span id="p_julia_cr_val">-0.70</span></div>
    <div class="param-group"><label>Julia C Imag</label><input type="range" id="p_julia_ci" min="-2" max="2" step="0.01" value="0.27"><span id="p_julia_ci_val">0.27</span></div>
  `,
  perlin: `
    <div class="param-group"><label>Scale</label><input type="range" id="p_scale" min="10" max="200" value="50"><span id="p_scale_val">50</span></div>
    <div class="param-group"><label>Octaves</label><input type="range" id="p_octaves" min="1" max="12" value="6"><span id="p_octaves_val">6</span></div>
    <div class="param-group"><label>Color Mode</label><select id="p_color_mode"><option value="colorful">Colorful</option><option value="terrain">Terrain</option><option value="cloud">Cloud</option><option value="lava">Lava</option><option value="gray">Gray</option></select></div>
    <div class="param-group"><label>Seed</label><input type="number" id="p_seed" placeholder="Random" value="0"></div>
  `,
  plasma: `
    <div class="param-group"><label>Roughness</label><input type="range" id="p_roughness" min="0.1" max="1.5" step="0.05" value="0.7"><span id="p_roughness_val">0.70</span></div>
    <div class="param-group"><label>Color Scheme</label><select id="p_color_scheme"><option value="plasma">Plasma</option><option value="fire">Fire</option><option value="underwater">Underwater</option><option value="sunset">Sunset</option></select></div>
    <div class="param-group"><label>Seed</label><input type="number" id="p_seed" placeholder="Random" value="0"></div>
  `,
  cellular: `
    <div class="param-group"><label>Generations</label><input type="range" id="p_generations" min="10" max="200" value="50"><span id="p_generations_val">50</span></div>
    <div class="param-group"><label>Rule (0-255)</label><input type="number" id="p_rule" min="0" max="255" value="110"></div>
    <div class="param-group"><label><input type="checkbox" id="p_symmetric"> Symmetric Start</label></div>
  `,
  gradient: `
    <div class="param-group"><label>Colors (hex, comma separated)</label><input type="text" id="p_colors" value="#ff0000,#ff8800,#ffff00,#00ff00,#0000ff"></div>
    <div class="param-group"><label>Style</label><select id="p_gradient_style"><option value="linear">Linear</option><option value="radial">Radial</option><option value="angular">Angular</option><option value="diamond">Diamond</option></select></div>
    <div class="param-group"><label>Angle</label><input type="range" id="p_angle" min="0" max="360" value="0"><span id="p_angle_val">0°</span></div>
  `,
  geometric: `
    <div class="param-group"><label>Pattern</label><select id="p_pattern_type"><option value="circles">Circles</option><option value="squares">Squares</option><option value="triangles">Triangles</option><option value="hexagons">Hexagons</option><option value="stars">Stars</option><option value="waves">Waves</option></select></div>
    <div class="param-group"><label>Scale</label><input type="range" id="p_pattern_scale" min="10" max="200" value="50"><span id="p_pattern_scale_val">50</span></div>
    <div class="param-group"><label>Density</label><input type="range" id="p_density" min="0.1" max="2" step="0.1" value="0.8"><span id="p_density_val">0.8</span></div>
    <div class="param-group"><label>Rotation</label><input type="range" id="p_pattern_rotation" min="0" max="360" value="0"><span id="p_pattern_rotation_val">0°</span></div>
  `,
  spirograph: `
    <div class="param-group"><label>R (Fixed circle)</label><input type="range" id="p_R" min="20" max="300" value="100"><span id="p_R_val">100</span></div>
    <div class="param-group"><label>r (Rolling circle)</label><input type="range" id="p_r" min="10" max="200" value="50"><span id="p_r_val">50</span></div>
    <div class="param-group"><label>d (Pen offset)</label><input type="range" id="p_d" min="5" max="200" value="30"><span id="p_d_val">30</span></div>
  `,
  voronoi: `
    <div class="param-group"><label>Number of Points</label><input type="range" id="p_num_points" min="10" max="500" value="50"><span id="p_num_points_val">50</span></div>
    <div class="param-group"><label>Color Mode</label><select id="p_color_mode_v"><option value="random">Random</option><option value="pastel">Pastel</option><option value="dark">Dark</option><option value="hsv">HSV Spectrum</option></select></div>
    <div class="param-group"><label>Seed</label><input type="number" id="p_seed" placeholder="Random" value="0"></div>
  `,
  galaxy: `
    <div class="param-group"><label>Number of Stars</label><input type="range" id="p_num_stars" min="500" max="10000" step="100" value="3000"><span id="p_num_stars_val">3000</span></div>
    <div class="param-group"><label>Spiral Arms</label><input type="range" id="p_spiral_arms" min="1" max="8" value="3"><span id="p_spiral_arms_val">3</span></div>
    <div class="param-group"><label>Seed</label><input type="number" id="p_seed" placeholder="Random" value="0"></div>
  `,
  wave: `
    <div class="param-group"><label>Frequency</label><input type="range" id="p_freq" min="0.005" max="0.5" step="0.001" value="0.05"><span id="p_freq_val">0.050</span></div>
    <div class="param-group"><label>Amplitude</label><input type="range" id="p_amplitude" min="5" max="200" value="50"><span id="p_amplitude_val">50</span></div>
    <div class="param-group"><label>Wave Type</label><select id="p_wave_type"><option value="sine">Sine</option><option value="cosine">Cosine</option><option value="square_wave">Square</option><option value="triangle">Triangle</option><option value="sawtooth">Sawtooth</option></select></div>
  `,
  snowflake: `
    <div class="param-group"><label>Iterations</label><input type="range" id="p_iterations" min="1" max="7" value="4"><span id="p_iterations_val">4</span></div>
  `,
  abstract: `
    <div class="param-group"><label>Seed</label><input type="number" id="p_seed" placeholder="Random" value="0"></div>
  `
};

function updateGenParams() {
  const type = document.getElementById('genType').value;
  const container = document.getElementById('genParams');
  container.innerHTML = genParamDefs[type] || '';

  container.querySelectorAll('input[type="range"]').forEach(el => {
    const valId = el.id + '_val';
    const valSpan = document.getElementById(valId);
    if (valSpan) {
      valSpan.textContent = el.value;
      el.addEventListener('input', () => {
        valSpan.textContent = el.type === 'range' && el.step && el.step.includes('.')
          ? parseFloat(el.value).toFixed(2)
          : el.value;
      });
    }
  });
}

function gatherGenParams() {
  const params = { type: document.getElementById('genType').value };
  document.querySelectorAll('#genParams input, #genParams select').forEach(el => {
    const key = el.id.replace(/^p_/, '');
    if (el.type === 'checkbox') {
      params[key] = el.checked ? 'true' : 'false';
    } else {
      params[key] = el.value;
    }
  });
  params.width = parseInt(document.getElementById('genWidth').value) || 1920;
  params.height = parseInt(document.getElementById('genHeight').value) || 1080;
  return params;
}

async function generate() {
  if (isGenerating) return;
  isGenerating = true;
  showLoading('Generating image...');

  try {
    const params = gatherGenParams();
    const resp = await fetch(API_BASE + '/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    const data = await resp.json();
    if (data.success) {
      sessionId = data.session_id;
      currentImageData = data.image;
      updateImageDisplay(data.image, data.width, data.height);
      showToast('Image generated successfully!');
    } else {
      showToast('Error: ' + (data.error || 'Generation failed'), 3000);
    }
  } catch (e) {
    showToast('Error: ' + e.message, 3000);
  } finally {
    isGenerating = false;
    hideLoading();
  }
}

/* ==================== UPLOAD ==================== */

async function uploadImage(input) {
  const file = input.files[0];
  if (!file) return;

  showLoading('Uploading image...');
  const formData = new FormData();
  formData.append('image', file);

  try {
    const resp = await fetch(API_BASE + '/upload', {
      method: 'POST',
      body: formData
    });
    const data = await resp.json();
    if (data.success) {
      sessionId = data.session_id;
      currentImageData = data.image;
      updateImageDisplay(data.image, data.width, data.height);
      showToast('Image uploaded!');
    } else {
      showToast('Error: ' + (data.error || 'Upload failed'), 3000);
    }
  } catch (e) {
    showToast('Error: ' + e.message, 3000);
  } finally {
    hideLoading();
  }
}

/* ==================== EDITING ==================== */

async function editOperation(operations) {
  if (!sessionId) {
    showToast('No image loaded', 1500);
    return null;
  }

  showLoading('Applying...');
  try {
    const resp = await fetch(API_BASE + '/edit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, operations })
    });
    const data = await resp.json();
    if (data.success) {
      currentImageData = data.image;
      updateImageDisplay(data.image, data.width, data.height);
      return data;
    } else {
      showToast('Error: ' + (data.error || 'Operation failed'), 3000);
      return null;
    }
  } catch (e) {
    showToast('Error: ' + e.message, 3000);
    return null;
  } finally {
    hideLoading();
  }
}

async function applyFilter(filterType, params = {}) {
  params.filter_type = filterType;
  await editOperation([{ type: 'filter', params }]);
}

async function applyCustomKernel() {
  const kernel = document.getElementById('customKernel').value;
  await applyFilter('custom_kernel', { kernel, kernel_size: 3 });
}

async function applyAdjustments() {
  const ops = [];
  const b = parseInt(document.getElementById('adjBrightness').value) / 100;
  const c = parseInt(document.getElementById('adjContrast').value) / 100;
  const s = parseInt(document.getElementById('adjSaturation').value) / 100;
  const sh = parseInt(document.getElementById('adjSharpness').value) / 100;
  const g = parseInt(document.getElementById('adjGamma').value) / 100;
  const e = parseInt(document.getElementById('adjExposure').value) / 100;
  const v = parseInt(document.getElementById('adjVibrance').value) / 100;
  const t = parseInt(document.getElementById('adjTemp').value) / 100;
  const h = parseInt(document.getElementById('adjHue').value) / 100;
  const hl = parseInt(document.getElementById('adjHighlights').value);
  const sd = parseInt(document.getElementById('adjShadows').value);

  if (b !== 1) ops.push({ type: 'adjust', params: { adjustment_type: 'brightness', value: b } });
  if (c !== 1) ops.push({ type: 'adjust', params: { adjustment_type: 'contrast', value: c } });
  if (s !== 1) ops.push({ type: 'adjust', params: { adjustment_type: 'saturation', value: s } });
  if (sh !== 1) ops.push({ type: 'adjust', params: { adjustment_type: 'sharpness', value: sh } });
  if (g !== 1) ops.push({ type: 'adjust', params: { adjustment_type: 'gamma', value: g } });
  if (e !== 0) ops.push({ type: 'adjust', params: { adjustment_type: 'exposure', value: e } });
  if (v !== 0) ops.push({ type: 'adjust', params: { adjustment_type: 'vibrance', value: v } });
  if (t !== 0) ops.push({ type: 'adjust', params: { adjustment_type: 'temperature', value: t } });
  if (h !== 0) ops.push({ type: 'adjust', params: { adjustment_type: 'hue', value: h } });
  if (hl !== 0) ops.push({ type: 'adjust', params: { adjustment_type: 'highlights', value: hl } });
  if (sd !== 0) ops.push({ type: 'adjust', params: { adjustment_type: 'shadows', value: sd } });

  if (ops.length === 0) {
    showToast('No adjustments changed', 1000);
    return;
  }
  await editOperation(ops);
}

function liveAdjust() {
  clearTimeout(adjustTimeout);
  adjustTimeout = setTimeout(applyAdjustments, 500);
}

async function applyTransform(transformType, params = {}) {
  params.transform_type = transformType;
  await editOperation([{ type: 'transform', params }]);
}

async function applyEffect(effectType, params = {}) {
  await editOperation([{ type: effectType, params }]);
}

async function applyGradientMap(hexColors) {
  const colors = hexColors.map(h => {
    h = h.replace('#', '');
    return [parseInt(h.substr(0,2),16), parseInt(h.substr(2,2),16), parseInt(h.substr(4,2),16)];
  });
  await editOperation([{ type: 'gradient_map', params: { colors } }]);
}

async function applyChannelMixer(r, g, b) {
  await editOperation([{ type: 'channel_mixer', params: { red: r, green: g, blue: b } }]);
}

async function applyText() {
  const params = {
    text: document.getElementById('drawText').value,
    x: parseInt(document.getElementById('textX').value),
    y: parseInt(document.getElementById('textY').value),
    size: parseInt(document.getElementById('textSize').value),
    color: document.getElementById('textColor').value,
    rotation: parseFloat(document.getElementById('textRot').value),
    stroke_width: parseInt(document.getElementById('textStroke').value)
  };
  await editOperation([{ type: 'text', params }]);
}

async function applyShape() {
  const params = {
    shape: document.getElementById('shapeType').value,
    x1: parseInt(document.getElementById('shapeX1').value),
    y1: parseInt(document.getElementById('shapeY1').value),
    x2: parseInt(document.getElementById('shapeX2').value),
    y2: parseInt(document.getElementById('shapeY2').value),
    color: document.getElementById('shapeColor').value,
    fill: document.getElementById('shapeFill').value,
    width: parseInt(document.getElementById('shapeWidth').value),
    sides: parseInt(document.getElementById('shapeSides').value)
  };
  await editOperation([{ type: 'shape', params }]);
}

async function undo() {
  if (!sessionId) return;
  showLoading('Undo...');
  try {
    const resp = await fetch(API_BASE + '/undo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    });
    const data = await resp.json();
    if (data.success && data.image) {
      currentImageData = data.image;
      updateImageDisplay(data.image, data.width, data.height);
    }
  } catch (e) {
    showToast('Error: ' + e.message, 2000);
  } finally {
    hideLoading();
  }
}

async function redo() {
  if (!sessionId) return;
  showLoading('Redo...');
  try {
    const resp = await fetch(API_BASE + '/redo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    });
    const data = await resp.json();
    if (data.success && data.image) {
      currentImageData = data.image;
      updateImageDisplay(data.image, data.width, data.height);
    }
  } catch (e) {
    showToast('Error: ' + e.message, 2000);
  } finally {
    hideLoading();
  }
}

async function resetEditor() {
  if (!sessionId) return;
  showLoading('Resetting...');
  try {
    await fetch(API_BASE + '/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    });
    clearCanvas();
    showToast('Reset complete');
  } catch (e) {
    showToast('Error: ' + e.message, 2000);
  } finally {
    hideLoading();
  }
}

async function resizeCanvas() {
  const w = parseInt(document.getElementById('canvasW').value) || 1920;
  const h = parseInt(document.getElementById('canvasH').value) || 1080;
  if (!sessionId) {
    showLoading('Creating canvas...');
    try {
      const resp = await fetch(API_BASE + '/canvas_resize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: 'new', width: w, height: h })
      });
      const data = await resp.json();
      if (data.success) {
        sessionId = data.session_id || sessionId;
        currentImageData = data.image;
        updateImageDisplay(data.image, data.width, data.height);
        showToast('Canvas created');
      }
    } catch (e) {
      showToast('Error: ' + e.message, 2000);
    } finally {
      hideLoading();
    }
    return;
  }

  showLoading('Resizing canvas...');
  try {
    const resp = await fetch(API_BASE + '/canvas_resize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, width: w, height: h })
    });
    const data = await resp.json();
    if (data.success) {
      currentImageData = data.image;
      updateImageDisplay(data.image, data.width, data.height);
      showToast('Canvas resized');
    }
  } catch (e) {
    showToast('Error: ' + e.message, 2000);
  } finally {
    hideLoading();
  }
}

/* ==================== BLEND / LAYERS ==================== */

let overlayImageData = null;

function uploadOverlay(input) {
  const file = input.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(e) {
    overlayImageData = e.target.result.split(',')[1];
    showToast('Overlay loaded');
  };
  reader.readAsDataURL(file);
}

async function applyBlend() {
  if (!sessionId || !overlayImageData) {
    showToast('Need an image and an overlay', 2000);
    return;
  }

  showLoading('Blending layers...');
  try {
    const blendMode = document.getElementById('blendMode').value;
    const opacity = parseInt(document.getElementById('layerOpacity').value) / 100;

    const resp = await fetch(API_BASE + '/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: overlayImageData })
    });
    const overlayData = await resp.json();
    if (!overlayData.success) {
      showToast('Overlay upload failed', 2000);
      hideLoading();
      return;
    }

    const overlaySessionId = overlayData.session_id;
    const blendResult = await fetch(API_BASE + '/edit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: overlaySessionId,
        operations: [{ type: 'transform', params: {
          transform_type: 'resize',
          width: 1920,
          height: 1080,
          keep_aspect: 'true'
        }}]
      })
    });
    const resizedData = await blendResult.json();
    if (!resizedData.success) {
      showToast('Resize failed', 2000);
      hideLoading();
      return;
    }

    const img1Data = currentImageData;
    const img2Data = resizedData.image;

    const canvas = document.createElement('canvas');
    canvas.width = 1920;
    canvas.height = 1080;
    const ctx = canvas.getContext('2d');

    const img1 = new Image();
    const img2 = new Image();
    const load1 = new Promise(resolve => { img1.onload = resolve; img1.src = 'data:image/png;base64,' + img1Data; });
    const load2 = new Promise(resolve => { img2.onload = resolve; img2.src = 'data:image/png;base64,' + img2Data; });
    await Promise.all([load1, load2]);

    ctx.globalAlpha = 1;
    ctx.drawImage(img1, 0, 0, 1920, 1080);
    ctx.globalAlpha = opacity;

    if (blendMode === 'normal') {
      ctx.drawImage(img2, 0, 0, 1920, 1080);
    } else if (blendMode === 'multiply') {
      ctx.globalCompositeOperation = 'multiply';
      ctx.drawImage(img2, 0, 0, 1920, 1080);
      ctx.globalCompositeOperation = 'source-over';
    } else if (blendMode === 'screen') {
      ctx.globalCompositeOperation = 'screen';
      ctx.drawImage(img2, 0, 0, 1920, 1080);
      ctx.globalCompositeOperation = 'source-over';
    } else if (blendMode === 'overlay') {
      ctx.globalCompositeOperation = 'overlay';
      ctx.drawImage(img2, 0, 0, 1920, 1080);
      ctx.globalCompositeOperation = 'source-over';
    } else if (blendMode === 'darken') {
      ctx.globalCompositeOperation = 'darken';
      ctx.drawImage(img2, 0, 0, 1920, 1080);
      ctx.globalCompositeOperation = 'source-over';
    } else if (blendMode === 'lighten') {
      ctx.globalCompositeOperation = 'lighten';
      ctx.drawImage(img2, 0, 0, 1920, 1080);
      ctx.globalCompositeOperation = 'source-over';
    } else if (blendMode === 'difference') {
      ctx.globalCompositeOperation = 'difference';
      ctx.drawImage(img2, 0, 0, 1920, 1080);
      ctx.globalCompositeOperation = 'source-over';
    } else if (blendMode === 'exclusion') {
      ctx.globalCompositeOperation = 'exclusion';
      ctx.drawImage(img2, 0, 0, 1920, 1080);
      ctx.globalCompositeOperation = 'source-over';
    } else if (blendMode === 'color_dodge') {
      ctx.globalCompositeOperation = 'color-dodge';
      ctx.drawImage(img2, 0, 0, 1920, 1080);
      ctx.globalCompositeOperation = 'source-over';
    } else if (blendMode === 'color_burn') {
      ctx.globalCompositeOperation = 'color-burn';
      ctx.drawImage(img2, 0, 0, 1920, 1080);
      ctx.globalCompositeOperation = 'source-over';
    } else if (blendMode === 'hard_light') {
      ctx.globalCompositeOperation = 'hard-light';
      ctx.drawImage(img2, 0, 0, 1920, 1080);
      ctx.globalCompositeOperation = 'source-over';
    } else if (blendMode === 'soft_light') {
      ctx.globalCompositeOperation = 'soft-light';
      ctx.drawImage(img2, 0, 0, 1920, 1080);
      ctx.globalCompositeOperation = 'source-over';
    } else {
      ctx.drawImage(img2, 0, 0, 1920, 1080);
    }

    const b64 = canvas.toDataURL('image/png').split(',')[1];

    const uploadResp = await fetch(API_BASE + '/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: b64 })
    });
    const finalData = await uploadResp.json();
    if (finalData.success) {
      sessionId = finalData.session_id;
      currentImageData = finalData.image;
      updateImageDisplay(finalData.image, finalData.width, finalData.height);
      showToast('Blend applied!');
    }
  } catch (e) {
    showToast('Error: ' + e.message, 3000);
  } finally {
    hideLoading();
  }
}

/* ==================== DOWNLOAD ==================== */

async function downloadImage(fmt) {
  if (!currentImageData) {
    showToast('No image to download', 1500);
    return;
  }

  const canvas = document.createElement('canvas');
  const img = new Image();
  img.onload = function() {
    canvas.width = img.width;
    canvas.height = img.height;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0);
    const link = document.createElement('a');
    link.download = `image_genius_${Date.now()}.${fmt.toLowerCase()}`;
    if (fmt === 'JPEG') {
      link.href = canvas.toDataURL('image/jpeg', 0.95);
    } else {
      link.href = canvas.toDataURL('image/png');
    }
    link.click();
    showToast(`Downloaded as ${fmt}`);
  };
  img.src = 'data:image/png;base64,' + currentImageData;
}

/* ==================== KEYBOARD SHORTCUTS ==================== */

document.addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
    e.preventDefault();
    if (e.shiftKey) redo();
    else undo();
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault();
    downloadImage('PNG');
  }
});

/* ==================== FILE DRAG & DROP ==================== */

const container = document.getElementById('canvasContainer');
container.addEventListener('dragover', function(e) {
  e.preventDefault();
  this.style.borderColor = 'var(--accent)';
});
container.addEventListener('dragleave', function(e) {
  e.preventDefault();
  this.style.borderColor = '';
});
container.addEventListener('drop', function(e) {
  e.preventDefault();
  this.style.borderColor = '';
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    const input = document.getElementById('fileInput');
    const dt = new DataTransfer();
    dt.items.add(files[0]);
    input.files = dt.files;
    uploadImage(input);
  }
});

/* ==================== INIT ==================== */

updateGenParams();
document.getElementById('genWidth').addEventListener('change', function() {
  document.getElementById('canvasW').value = this.value;
});
document.getElementById('genHeight').addEventListener('change', function() {
  document.getElementById('canvasH').value = this.value;
});

document.querySelectorAll('#genParams input[type="range"]').forEach(el => {
  el.addEventListener('input', function() {
    const valEl = document.getElementById(this.id + '_val');
    if (valEl) valEl.textContent = this.value;
  });
});

document.getElementById('canvas').addEventListener('load', function() {
  document.getElementById('statusText').textContent = 'Ready';
  this.style.width = '';
  this.style.height = '';
});

showToast('IMAGE GENIUS ready — generate or upload an image to begin', 3000);
