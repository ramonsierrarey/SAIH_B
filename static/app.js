"use strict";

export default function ({ data: input, parentElement, setTriggerValue }) {
const cards = [
  ["E_17VPCT01", "◔"],
  ["E_17VICT01", "≈"],
  ["E_17LICT01", "↕"],
  ["E_17FICT95", "↗"],
];
const contextStations = [
  { code: "PN34", title: "Puerto del Pico · PN34", cards: [["PN34WIC101", "☂"], ["PN34WIC601", "☂"]] },
  { code: "AR21", title: "Alberche en Navaluenga · AR21", cards: [["AR21LI__01", "↕"], ["AR21FICT98", "↗"]] },
  { code: "E_18", title: "Charco del Cura · E_18", cards: [["E_18VPCT01", "◔"], ["E_18FICT95", "↗"]] },
];
const metric = parentElement.querySelector("#metric");
const refreshButton = parentElement.querySelector("#refresh");
const notice = parentElement.querySelector("#notice");
const data = input.snapshot;

const number = (value) => new Intl.NumberFormat("es-ES", { maximumFractionDigits: 2 }).format(value);
function sourceDate(value) {
  if (!value) return "Sin datos";
  const [day, hour] = value.split("T");
  return `${day.split("-").reverse().join("/")} ${hour}`;
}
function showNotice(message) {
  notice.hidden = !message;
  notice.textContent = message || "";
}
function element(tag, className, text) {
  const result = document.createElement(tag);
  if (className) result.className = className;
  if (text !== undefined) result.textContent = text;
  return result;
}
function renderTrend(card, tag, latest) {
  const endTime = Date.parse(`${latest.measured_at}:00Z`);
  const startTime = endTime - 25 * 3600000;
  const readings = data.readings.filter((item) =>
    item.tag === tag && Date.parse(`${item.measured_at}:00Z`) >= startTime
  );
  if (readings.length < 2) {
    card.append(element("div", "card-trend card-trend-unavailable", "Tendencia no disponible"));
    return;
  }

  const change = readings[readings.length - 1].value - readings[0].value;
  const tolerance = Math.max(0.01, Math.abs(readings[0].value) * 0.001);
  const direction = change > tolerance ? "up" : change < -tolerance ? "down" : "stable";
  const labels = { up: "Subiendo", stable: "Estable", down: "Bajando" };
  const trend = element("div", `card-trend card-trend-${direction}`);
  trend.append(element("span", "card-trend-label", labels[direction]));

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 100 30");
  svg.setAttribute("aria-hidden", "true");
  const values = readings.map((item) => item.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const points = values.map((value, index) => {
    const x = readings.length === 1 ? 50 : index * 100 / (readings.length - 1);
    const y = max === min ? 15 : 25 - (value - min) * 20 / (max - min);
    return `${x},${y}`;
  }).join(" ");
  const line = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  line.setAttribute("points", points);
  svg.append(line);
  trend.append(svg);
  card.append(trend);
}
function renderCards(container, definitions) {
  container.replaceChildren();
  for (const [tag, icon] of definitions) {
    const info = data.signals[tag];
    const reading = data.latest.find((item) => item.tag === tag);
    const card = element("article", "card");
    card.append(element("div", "card-icon", icon), element("div", "card-label", info.name));
    const value = element("div", "card-value", reading ? number(reading.value) : "—");
    value.append(element("span", "card-unit", info.unit));
    card.append(value, element("div", "card-time", reading ? `Lectura: ${sourceDate(reading.measured_at)}` : "Sin lecturas"));
    if (reading) renderTrend(card, tag, reading);
    if (tag === "E_18VPCT01" && reading && reading.value > 100) {
      card.classList.add("card-warning");
      card.append(element("div", "card-warning-text", "Última lectura superior al 100 %"));
    }
    container.append(card);
  }
}
function renderContext() {
  const container = parentElement.querySelector("#context-stations");
  container.replaceChildren();
  for (const station of contextStations) {
    const section = element("div", "station");
    const heading = element("div", "station-heading");
    heading.append(element("h3", "", station.title));
    const state = data.stations[station.code];
    heading.append(element("span", "station-status", state.last_success
      ? `Consulta: ${new Date(state.last_success).toLocaleString("es-ES")}`
      : "Aún sin consulta completada"));
    section.append(heading);
    const grid = element("div", "cards context-cards");
    renderCards(grid, station.cards);
    section.append(grid);
    container.append(section);
  }
}
function renderChart() {
  const tag = metric.value;
  const info = data.signals[tag];
  if (!info) return;
  const readings = data.readings.filter((item) => item.tag === tag);
  parentElement.querySelector("#chart-title").textContent = info.name;
  parentElement.querySelector("#chart-subtitle").textContent = `${readings.length} mediciones · ${info.unit}`;
  const svg = parentElement.querySelector("#chart");
  const empty = parentElement.querySelector("#chart-empty");
  svg.replaceChildren();
  empty.hidden = readings.length > 0;
  const start = parentElement.querySelector("#chart-start");
  const end = parentElement.querySelector("#chart-end");
  start.textContent = readings.length ? sourceDate(readings[0].measured_at) : "—";
  end.textContent = readings.length ? sourceDate(readings[readings.length - 1].measured_at) : "—";
  if (!readings.length) return;

  const ns = "http://www.w3.org/2000/svg";
  function draw(name, attrs, text) {
    const node = document.createElementNS(ns, name);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (text !== undefined) node.textContent = text;
    svg.append(node);
  }
  const values = readings.map((item) => item.value);
  let min = Math.min(...values);
  let max = Math.max(...values);
  const padding = (max - min) * 0.12 || Math.max(Math.abs(max) * 0.05, 0.1);
  min -= padding;
  max += padding;
  const times = readings.map((item) => Date.parse(`${item.measured_at}:00Z`));
  const first = times[0], last = times[times.length - 1];
  const x = (t) => 55 + (last === first ? 0.5 : (t - first) / (last - first)) * 925;
  const y = (v) => 235 - (v - min) / (max - min) * 210;
  for (let i = 0; i <= 4; i++) {
    const height = 25 + i * 52.5;
    draw("line", { x1: 55, x2: 980, y1: height, y2: height, stroke: "#3d5967", "stroke-width": 1 });
    draw("text", { x: 45, y: height + 4, "text-anchor": "end", fill: "#b8ccd4", "font-size": 11 }, number(max - (max - min) * i / 4));
  }
  let path = "";
  readings.forEach((reading, index) => {
    const gap = index > 0 && times[index] - times[index - 1] > 90 * 60 * 1000;
    path += `${index === 0 || gap ? "M" : "L"}${x(times[index]).toFixed(2)},${y(reading.value).toFixed(2)} `;
    if (readings.length === 1 || gap || (index < readings.length - 1 && times[index + 1] - times[index] > 90 * 60 * 1000)) {
      draw("circle", { cx: x(times[index]), cy: y(reading.value), r: 3, fill: "#91d4c8" });
    }
  });
  draw("path", { d: path, fill: "none", stroke: "#91d4c8", "stroke-width": 3, "stroke-linecap": "round", "stroke-linejoin": "round" });
  svg.setAttribute("aria-label", `${info.name}, ${readings.length} mediciones, de ${start.textContent} a ${end.textContent}`);
}
function render() {
  if (!metric.options.length) {
    for (const [tag, info] of Object.entries(data.signals)) {
      const option = element("option", "", info.name);
      option.value = tag;
      metric.append(option);
    }
  }
  renderCards(parentElement.querySelector("#cards"), cards);
  renderContext();
  renderChart();
  const status = parentElement.querySelector("#sync-status");
  const last = data.stations.E_17.last_success;
  status.textContent = last ? `Última consulta: ${new Date(last).toLocaleString("es-ES")}` : "Aún sin consulta completada";
  const errors = Object.values(data.stations).filter((station) => station.last_error)
    .map((station) => `${station.name}: ${station.last_error}`);
  const errorNotice = errors.length ? `Falló la captura de ${errors.join(" · ")}. Se mantienen en memoria los últimos datos recibidos.` : "";
  showNotice([input.message, errorNotice].filter(Boolean).join(" "));
}
metric.onchange = renderChart;
refreshButton.onclick = () => {
  refreshButton.disabled = true;
  setTriggerValue("refresh", true);
};
render();
refreshButton.disabled = false;
}
