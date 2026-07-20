import './style.css'
import deltaMapUrl from './assets/delta-map.png'

const MAP_NATURAL_WIDTH = 1026
const MAP_NATURAL_HEIGHT = 915

const app = document.querySelector('#app')

app.innerHTML = `
  <main class="page">
    <section class="panel">
      <div class="title-block">
        <h1>挂钩们都在干什么呢？</h1>
        <p class="desc">
          远程连接
        </p>
      </div>

      <div class="controls">
        <label class="field field-url">
          <span>服务器地址</span>
          <input id="wsUrl" type="text" spellcheck="false" value="ws://127.0.0.1:8081" />
        </label>

        <label class="field">
          <span>坐标模式</span>
          <select id="coordMode">
            <option value="pixel" selected>像素坐标：x/y 基于原图 1026×915</option>
            <option value="percent">百分比坐标：x/y 为 0-100</option>
            <option value="normalized">归一化坐标：x/y 为 0-1</option>
            <option value="auto">自动判断</option>
          </select>
        </label>

        <button id="connectBtn" class="btn primary">连接</button>
        <button id="requestBtn" class="btn" disabled>请求坐标</button>
        <button id="disconnectBtn" class="btn danger" disabled>断开</button>
      </div>

      <div class="status-row">
        <span id="statusDot" class="dot"></span>
        <span id="statusText">未连接</span>
        <span class="split"></span>
        <span>最近更新：<strong id="lastUpdate">--</strong></span>
      </div>
    </section>

    <section class="map-card">
      <div id="mapWrap" class="map-wrap">
        <img id="mapImage" src="${deltaMapUrl}" alt="三角洲行动地图" draggable="false" />
        <div id="markerLayer" class="marker-layer" aria-live="polite"></div>
        <div id="tooltip" class="tooltip" hidden></div>
      </div>
    </section>

    <section class="panel payload-panel">
      <div class="payload-title">
        <h2>最近一次服务器消息</h2>
      </div>
      <pre id="rawPayload">等待服务器数据...</pre>
    </section>
  </main>
`

const els = {
  wsUrl: document.getElementById('wsUrl'),
  coordMode: document.getElementById('coordMode'),
  connectBtn: document.getElementById('connectBtn'),
  requestBtn: document.getElementById('requestBtn'),
  disconnectBtn: document.getElementById('disconnectBtn'),
  statusDot: document.getElementById('statusDot'),
  statusText: document.getElementById('statusText'),
  lastUpdate: document.getElementById('lastUpdate'),
  markerLayer: document.getElementById('markerLayer'),
  tooltip: document.getElementById('tooltip'),
  rawPayload: document.getElementById('rawPayload'),
}

let socket = null
let latestPlayers = []

function setStatus(kind, text) {
  els.statusDot.className = 'dot'
  if (kind === 'connected') els.statusDot.classList.add('connected')
  if (kind === 'error') els.statusDot.classList.add('error')
  els.statusText.textContent = text
}

function setConnectedState(connected) {
  els.connectBtn.disabled = connected
  els.disconnectBtn.disabled = !connected
  els.requestBtn.disabled = !connected
  els.wsUrl.disabled = connected
}

function nowText() {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

function connect() {
  const url = els.wsUrl.value.trim()
  if (!url) {
    setStatus('error', '请填写 WebSocket 地址')
    return
  }

  disconnect(false)

  try {
    socket = new WebSocket(url)
  } catch (err) {
    setStatus('error', `连接创建失败：${err.message}`)
    return
  }

  setStatus('idle', '正在连接...')
  setConnectedState(true)

  socket.addEventListener('open', () => {
    setStatus('connected', `已连接：${url}`)
    sendRequest()
  })

  socket.addEventListener('message', async (event) => {
    const text = await readWsData(event.data)
    els.rawPayload.textContent = text

    try {
      const players = parseServerMessage(text)
      latestPlayers = players
      renderPlayers(players)
      els.lastUpdate.textContent = nowText()
      setStatus('connected', `已接收 ${players.length} 个坐标点`)
    } catch (err) {
      setStatus('error', `消息解析失败：${err.message}`)
      console.error(err)
    }
  })

  socket.addEventListener('close', () => {
    setConnectedState(false)
    setStatus('idle', '连接已关闭')
  })

  socket.addEventListener('error', () => {
    setStatus('error', 'WebSocket 连接错误')
  })
}

function disconnect(updateStatus = true) {
  if (socket) {
    socket.close()
    socket = null
  }
  setConnectedState(false)
  if (updateStatus) setStatus('idle', '未连接')
}

function sendRequest() {
  if (!socket || socket.readyState !== WebSocket.OPEN) return

  const request = {
    type: 'request_players',
    count: 3,
    map: 'delta',
    coordinate: els.coordMode.value,
    ts: Date.now(),
  }

  socket.send(JSON.stringify(request))
}

async function readWsData(data) {
  if (typeof data === 'string') return data
  if (data instanceof Blob) return await data.text()
  if (data instanceof ArrayBuffer) return new TextDecoder().decode(data)
  return String(data)
}

function parseServerMessage(text) {
  const trimmed = text.trim()

  try {
    const parsed = JSON.parse(trimmed)
    return normalizePayload(parsed)
  } catch (_) {
    return normalizePayload(parseBraceArrayFormat(trimmed))
  }
}

function normalizePayload(payload) {
  const rows =
    Array.isArray(payload) ? payload :
      Array.isArray(payload?.data) ? payload.data :
        Array.isArray(payload?.players) ? payload.players :
          Array.isArray(payload?.coordinates) ? payload.coordinates :
            null

  if (!rows) {
    throw new Error('消息不是坐标数组，也没有 data/players/coordinates 字段')
  }

  return rows.map((row, index) => {
    if (!Array.isArray(row) || row.length < 3) {
      throw new Error(`第 ${index + 1} 个坐标不是 [x,y,value]`)
    }

    const x = Number(row[0])
    const y = Number(row[1])

    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      throw new Error(`第 ${index + 1} 个坐标的 x/y 不是数字`)
    }

    return {
      x,
      y,
      value: row[2],
    }
  })
}

function parseBraceArrayFormat(text) {
  if (!text.startsWith('{') || !text.endsWith('}')) {
    throw new Error('既不是 JSON，也不是 {[x,y,value],...} 格式')
  }

  const body = text.slice(1, -1).trim()
  const groups = extractTopLevelBracketGroups(body)

  if (groups.length === 0) {
    throw new Error('没有找到 [x,y,value] 坐标组')
  }

  return groups.map((group) => {
    const inner = group.slice(1, -1)
    const parts = splitFirstTwoCommas(inner)

    const x = Number(parts[0].trim())
    const y = Number(parts[1].trim())
    const valueRaw = parts[2].trim()

    let value
    try {
      value = JSON.parse(valueRaw)
    } catch (_) {
      value = stripQuotes(valueRaw)
    }

    return [x, y, value]
  })
}

function extractTopLevelBracketGroups(input) {
  const groups = []
  let start = -1
  let depth = 0
  let inString = false
  let quote = ''
  let escaped = false

  for (let i = 0; i < input.length; i++) {
    const ch = input[i]

    if (inString) {
      if (escaped) {
        escaped = false
      } else if (ch === '\\') {
        escaped = true
      } else if (ch === quote) {
        inString = false
      }
      continue
    }

    if (ch === '"' || ch === "'") {
      inString = true
      quote = ch
      continue
    }

    if (ch === '[') {
      if (depth === 0) start = i
      depth++
    } else if (ch === ']') {
      depth--
      if (depth === 0 && start !== -1) {
        groups.push(input.slice(start, i + 1))
        start = -1
      }
    }
  }

  return groups
}

function splitFirstTwoCommas(input) {
  const commaIndexes = []
  let depth = 0
  let inString = false
  let quote = ''
  let escaped = false

  for (let i = 0; i < input.length; i++) {
    const ch = input[i]

    if (inString) {
      if (escaped) {
        escaped = false
      } else if (ch === '\\') {
        escaped = true
      } else if (ch === quote) {
        inString = false
      }
      continue
    }

    if (ch === '"' || ch === "'") {
      inString = true
      quote = ch
      continue
    }

    if (ch === '[' || ch === '{' || ch === '(') depth++
    if (ch === ']' || ch === '}' || ch === ')') depth--

    if (ch === ',' && depth === 0) {
      commaIndexes.push(i)
      if (commaIndexes.length === 2) break
    }
  }

  if (commaIndexes.length < 2) {
    throw new Error(`坐标组缺少字段：${input}`)
  }

  const [a, b] = commaIndexes
  return [
    input.slice(0, a),
    input.slice(a + 1, b),
    input.slice(b + 1),
  ]
}

function stripQuotes(s) {
  const t = s.trim()
  if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) {
    return t.slice(1, -1)
  }
  return t
}

function toPercent(x, y) {
  const mode = els.coordMode.value

  if (mode === 'normalized') {
    return [x * 100, y * 100]
  }

  if (mode === 'percent') {
    return [x, y]
  }

  if (mode === 'auto') {
    if (Math.abs(x) <= 1 && Math.abs(y) <= 1) return [x * 100, y * 100]
    if (Math.abs(x) <= 100 && Math.abs(y) <= 100) return [x, y]
  }

  return [
    (x / MAP_NATURAL_WIDTH) * 100,
    (y / MAP_NATURAL_HEIGHT) * 100,
  ]
}

function renderPlayers(players) {
  els.markerLayer.innerHTML = ''

  players.slice(0, 3).forEach((player, index) => {
    const [left, top] = toPercent(player.x, player.y)

    const marker = document.createElement('button')
    marker.className = 'marker'
    marker.type = 'button'
    marker.style.left = `${clamp(left, 0, 100)}%`
    marker.style.top = `${clamp(top, 0, 100)}%`
    marker.innerHTML = `<span>${index + 1}</span>`
    marker.setAttribute('aria-label', `坐标点 ${index + 1}`)

    marker.addEventListener('mouseenter', (e) => showTooltip(e, player, index))
    marker.addEventListener('mousemove', (e) => moveTooltip(e))
    marker.addEventListener('mouseleave', hideTooltip)

    els.markerLayer.appendChild(marker)
  })
}

function showTooltip(event, player, index) {
  const value = formatValue(player.value)
  els.tooltip.innerHTML = `
    <div class="tip-title">目标 ${index + 1} · x=${player.x}, y=${player.y}</div>
    <div>${escapeHtml(value)}</div>
  `
  els.tooltip.hidden = false
  moveTooltip(event)
}

function moveTooltip(event) {
  const offset = 16
  const rect = els.tooltip.getBoundingClientRect()

  let x = event.clientX + offset
  let y = event.clientY + offset

  if (x + rect.width > window.innerWidth - 8) {
    x = event.clientX - rect.width - offset
  }

  if (y + rect.height > window.innerHeight - 8) {
    y = event.clientY - rect.height - offset
  }

  els.tooltip.style.left = `${Math.max(8, x)}px`
  els.tooltip.style.top = `${Math.max(8, y)}px`
}

function hideTooltip() {
  els.tooltip.hidden = true
}

function formatValue(value) {
  if (typeof value === 'string') return value
  return JSON.stringify(value, null, 2)
}

function escapeHtml(input) {
  return String(input)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

els.connectBtn.addEventListener('click', connect)
els.disconnectBtn.addEventListener('click', () => disconnect(true))
els.requestBtn.addEventListener('click', sendRequest)
els.coordMode.addEventListener('change', () => renderPlayers(latestPlayers))

setConnectedState(false)
