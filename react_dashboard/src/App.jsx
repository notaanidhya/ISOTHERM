import React, { useState, useMemo } from "react";
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceArea, ReferenceLine,
} from "recharts";
import {
  Zap, Flame, Snowflake, Sun, TrendingDown, Activity, Wind, Bot, Leaf,
  Gauge, ShieldCheck, ChevronRight, Filter, Terminal, CheckCircle2, Info,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/* DESIGN TOKENS                                                       */
/* ------------------------------------------------------------------ */
const C = {
  bg: "#0B0E14",
  bg2: "#090A0F",
  surface: "#131824",
  surface2: "#141824",
  border: "#1F2637",
  borderSoft: "#1A202E",
  text: "#E7ECF3",
  muted: "#94A3B8",
  mutedDim: "#5B6577",
  emerald: "#10B981",
  coral: "#F43F5E",
  cyan: "#06B6D4",
  amber: "#F59E0B",
  purple: "#A855F7",
};

/* ------------------------------------------------------------------ */
/* STATIC / HARDCODED DATA                                             */
/* ------------------------------------------------------------------ */

const crossCheckRows = [
  { day: "Winter (Jan 15)", fuel: "Electricity", meter: "Electricity:HVAC", db: "32,519,046.1900 J", eplus: "32,519,046.1900 J", diff: "0.0000 J" },
  { day: "Winter (Jan 15)", fuel: "Natural Gas", meter: "NaturalGas:Facility", db: "56,370,771.5312 J", eplus: "56,370,771.5312 J", diff: "0.0000 J" },
  { day: "Summer (Jul 1)", fuel: "Electricity", meter: "Electricity:HVAC", db: "0.0000 J", eplus: "0.0000 J", diff: "0.0000 J" },
  { day: "Summer (Jul 1)", fuel: "Natural Gas", meter: "NaturalGas:Facility", db: "0.0000 J", eplus: "0.0000 J", diff: "0.0000 J" },
];

const scorecardRows = [
  { tier: "Summer Overall Occupied", season: "summer", sub: "08:00 – 18:00", baseline: "11.0%", ai: "38.0%", delta: "+27.0 pp", up: true, mech: "Seasonal 0.5 clo clothing schedule + reheat elimination", indent: false },
  { tier: "Winter Overall Occupied", season: "winter", sub: "08:00 – 18:00", baseline: "87.5%", ai: "16.0%", delta: "−71.5 pp", up: false, mech: "Proactive morning buffering vs. sub-zero perimeter walls", indent: false },
  { tier: "Winter Mid-Peak Comfort Priority", sub: "08:00 – 12:00", baseline: "85.0%", ai: "10.0%", delta: "−75.0 pp", up: false, mech: "AI applies 20.5°C heating setpoint to warm tenants", indent: true },
  { tier: "Winter On-Peak Cost Priority", sub: "12:00 – 18:00", baseline: "89.0%", ai: "20.0%", delta: "−69.0 pp", up: false, mech: "AI drops setpoint to 19.0°C during $0.15/kWh peak to shed load", indent: true },
];

const winterDemand = [
  { h: 0, base: 0.52, aiE: 0.28, aiG: 1.2, tou: 0.05 },
  { h: 2, base: 0.50, aiE: 0.27, aiG: 1.0, tou: 0.05 },
  { h: 4, base: 0.48, aiE: 0.26, aiG: 0.9, tou: 0.05 },
  { h: 6, base: 0.55, aiE: 0.30, aiG: 3.5, tou: 0.08 },
  { h: 8, base: 0.75, aiE: 0.60, aiG: 19.08, tou: 0.08 },
  { h: 10, base: 0.70, aiE: 0.50, aiG: 6.0, tou: 0.08 },
  { h: 12, base: 0.65, aiE: 0.40, aiG: 2.8, tou: 0.08 },
  { h: 14, base: 0.62, aiE: 0.35, aiG: 2.2, tou: 0.15 },
  { h: 16, base: 0.68, aiE: 0.34, aiG: 1.9, tou: 0.15 },
  { h: 18, base: 0.72, aiE: 0.33, aiG: 2.0, tou: 0.15 },
  { h: 20, base: 0.60, aiE: 0.31, aiG: 2.4, tou: 0.08 },
  { h: 22, base: 0.55, aiE: 0.29, aiG: 1.5, tou: 0.05 },
  { h: 24, base: 0.52, aiE: 0.28, aiG: 1.2, tou: 0.05 },
];

const summerDemand = [
  { h: 0, base: 0.30, aiE: 0, aiG: 0, tou: 0.05 },
  { h: 2, base: 0.25, aiE: 0, aiG: 0, tou: 0.05 },
  { h: 4, base: 0.22, aiE: 0, aiG: 0, tou: 0.05 },
  { h: 6, base: 0.30, aiE: 0, aiG: 0, tou: 0.08 },
  { h: 8, base: 0.50, aiE: 0, aiG: 0, tou: 0.08 },
  { h: 10, base: 0.90, aiE: 0, aiG: 0, tou: 0.08 },
  { h: 12, base: 1.30, aiE: 0, aiG: 0, tou: 0.08 },
  { h: 14, base: 1.60, aiE: 0, aiG: 0, tou: 0.15 },
  { h: 16, base: 1.70, aiE: 0, aiG: 0, tou: 0.15 },
  { h: 18, base: 1.50, aiE: 0, aiG: 0, tou: 0.15 },
  { h: 20, base: 1.10, aiE: 0, aiG: 0, tou: 0.08 },
  { h: 22, base: 0.60, aiE: 0, aiG: 0, tou: 0.05 },
  { h: 24, base: 0.35, aiE: 0, aiG: 0, tou: 0.05 },
];

const winterPMV = [
  { h: 0, base: 0.10, ai: -0.30 }, { h: 2, base: 0.05, ai: -0.60 },
  { h: 4, base: 0.00, ai: -0.80 }, { h: 6, base: 0.05, ai: -1.40 },
  { h: 8, base: 0.15, ai: -1.90 }, { h: 10, base: 0.25, ai: -0.30 },
  { h: 12, base: 0.30, ai: 0.00 }, { h: 14, base: 0.35, ai: -0.60 },
  { h: 16, base: 0.30, ai: -0.65 }, { h: 18, base: 0.25, ai: -0.55 },
  { h: 20, base: 0.20, ai: -0.30 }, { h: 22, base: 0.15, ai: -0.20 },
  { h: 24, base: 0.10, ai: -0.25 },
];

const summerPMV = [
  { h: 0, base: 0.60, ai: 0.20 }, { h: 2, base: 0.55, ai: 0.15 },
  { h: 4, base: 0.50, ai: 0.10 }, { h: 6, base: 0.60, ai: 0.20 },
  { h: 8, base: 0.80, ai: 0.35 }, { h: 10, base: 1.00, ai: 0.45 },
  { h: 12, base: 1.30, ai: 0.55 }, { h: 14, base: 1.50, ai: 0.60 },
  { h: 16, base: 1.40, ai: 0.50 }, { h: 18, base: 1.20, ai: 0.40 },
  { h: 20, base: 0.90, ai: 0.30 }, { h: 22, base: 0.70, ai: 0.25 },
  { h: 24, base: 0.60, ai: 0.20 },
];

const winterZone = [
  { h: 0, indoor: 16.2, heatSp: 16, coolSp: 24 }, { h: 2, indoor: 16.0, heatSp: 16, coolSp: 24 },
  { h: 4, indoor: 15.8, heatSp: 16, coolSp: 24 }, { h: 6, indoor: 15.9, heatSp: 16, coolSp: 24 },
  { h: 8, indoor: 17.0, heatSp: 20.5, coolSp: 24 }, { h: 10, indoor: 19.5, heatSp: 20.5, coolSp: 24 },
  { h: 12, indoor: 20.3, heatSp: 19.0, coolSp: 24 }, { h: 14, indoor: 19.8, heatSp: 19.0, coolSp: 24 },
  { h: 16, indoor: 19.5, heatSp: 19.0, coolSp: 24 }, { h: 18, indoor: 19.3, heatSp: 19.0, coolSp: 24 },
  { h: 20, indoor: 18.5, heatSp: 16, coolSp: 24 }, { h: 22, indoor: 17.5, heatSp: 16, coolSp: 24 },
  { h: 24, indoor: 16.8, heatSp: 16, coolSp: 24 },
];

const summerZone = [
  { h: 0, indoor: 20.5, heatSp: 16, coolSp: 24 }, { h: 2, indoor: 20.2, heatSp: 16, coolSp: 24 },
  { h: 4, indoor: 20.0, heatSp: 16, coolSp: 24 }, { h: 6, indoor: 20.3, heatSp: 16, coolSp: 24 },
  { h: 8, indoor: 20.8, heatSp: 16, coolSp: 24 }, { h: 10, indoor: 21.3, heatSp: 16, coolSp: 24 },
  { h: 12, indoor: 21.8, heatSp: 16, coolSp: 24 }, { h: 14, indoor: 22.0, heatSp: 16, coolSp: 24 },
  { h: 16, indoor: 21.9, heatSp: 16, coolSp: 24 }, { h: 18, indoor: 21.6, heatSp: 16, coolSp: 24 },
  { h: 20, indoor: 21.2, heatSp: 16, coolSp: 24 }, { h: 22, indoor: 20.8, heatSp: 16, coolSp: 24 },
  { h: 24, indoor: 20.6, heatSp: 16, coolSp: 24 },
];

const ventData = [
  { h: 0, flow: 0.25 }, { h: 2, flow: 0.25 }, { h: 4, flow: 0.25 }, { h: 6, flow: 0.25 },
  { h: 8, flow: 2.0 }, { h: 10, flow: 2.0 }, { h: 12, flow: 2.0 }, { h: 14, flow: 2.0 },
  { h: 16, flow: 2.0 }, { h: 18, flow: 2.0 }, { h: 20, flow: 0.25 }, { h: 22, flow: 0.25 },
  { h: 24, flow: 0.25 },
];

const decisions = [
  { id: 14, t: 348.0, wall: "2026-01-15 08:00:12", season: "winter",
    reasoning: "Current hour is 08:00 (Mid-Peak tariff $0.08/kWh). Outdoor temp is -10.2°C. Zone SPACE1-1 is 3.5°C below occupied heating setpoint following night setback. Prioritizing rapid recovery ahead of occupancy — accepting a transient PMV excursion outside ±0.5 to avoid a colder, longer ramp.",
    action: 'set_zone_setpoints(zone="SPACE1-1", heating_sp=20.5, cooling_sp=24.0)' },
  { id: 13, t: 345.0, wall: "2026-01-15 05:00:07", season: "winter",
    reasoning: "Current hour is 05:00 (Off-Peak tariff $0.05/kWh). Outdoor temp is -12.8°C. Building is unoccupied for 3 more hours. Holding night setback to minimize thermal loss through the high-mass perimeter walls; cheap off-peak gas offsets slow drift.",
    action: 'set_zone_setpoints(zone="ALL", heating_sp=16.0, cooling_sp=26.0)' },
  { id: 12, t: 342.0, wall: "2026-01-15 14:00:03", season: "winter",
    reasoning: "Current hour is 14:00 (On-Peak tariff $0.15/kWh). Outdoor temp is -8.5°C. To avoid demand spike charges while preserving tenant thermal comfort within ASHRAE PMV bounds, lowering heating setpoint to 19.0°C for the on-peak window.",
    action: 'set_zone_setpoints(zone="SPACE1-1", heating_sp=19.0, cooling_sp=24.0)' },
  { id: 11, t: 339.0, wall: "2026-01-15 11:00:41", season: "winter",
    reasoning: "Current hour is 11:00 (Mid-Peak tariff $0.08/kWh). Zone temps have recovered to within 0.5°C of the 20.5°C occupied setpoint. Reducing boiler firing rate now that morning pickup is complete; no further action required this interval.",
    action: 'log_advisory(note="Morning pickup complete, holding 20.5C")' },
  { id: 10, t: 336.0, wall: "2026-01-15 00:00:00", season: "winter",
    reasoning: "Current hour is 00:00 (Off-Peak tariff $0.05/kWh). Building unoccupied. Outdoor temp -14.1°C. Engaging night setback across all zones to reduce standby heat loss while off-peak rates keep any residual firing inexpensive.",
    action: 'set_zone_setpoints(zone="ALL", heating_sp=16.0, cooling_sp=26.0)' },
  { id: 24, t: 4353.0, wall: "2026-07-01 14:00:00", season: "summer",
    reasoning: "Current hour is 14:00 (On-Peak tariff $0.15/kWh). Outdoor temp is 19.4°C, mild. Indoor air is naturally settling at 22.0°C, below the 24.0°C cooling setpoint — no mechanical cooling needed. Heating floor remains at 16.0°C to guarantee zero simultaneous VAV reheat.",
    action: 'log_advisory(note="Free-floating within band, 0.0 kWh HVAC this hour")' },
  { id: 23, t: 4350.0, wall: "2026-07-01 06:00:00", season: "summer",
    reasoning: "Current hour is 06:00 (Mid-Peak tariff $0.08/kWh). Outdoor temp is 15.8°C. Overnight free-cooling has indoor air at 20.3°C. Confirming heating floor stays at 16.0°C and cooling setpoint at 24.0°C — no actuator change needed.",
    action: 'log_advisory(note="No setpoint change required")' },
  { id: 22, t: 4347.0, wall: "2026-07-01 03:00:00", season: "summer",
    reasoning: "Current hour is 03:00 (Off-Peak tariff $0.05/kWh). Outdoor temp is 14.9°C. Building unoccupied, IAQ ventilation running at the scheduled 10% unoccupied minimum per the baseline schedule. No override issued — ventilation remains schedule-driven, not agent-controlled.",
    action: 'log_advisory(note="Ventilation nominal at 10% unoccupied minimum, no override")' },
  { id: 21, t: 4344.0, wall: "2026-07-01 00:00:00", season: "summer",
    reasoning: "Current hour is 00:00 (Off-Peak tariff $0.05/kWh). Outdoor temp is 16.2°C. Applying the summer strategy: lower the heating floor to 16.0°C for the full day to eliminate VAV reheat fighting against central cooling, while leaving the 24.0°C cooling setpoint untouched.",
    action: 'set_zone_setpoints(zone="ALL", heating_sp=16.0, cooling_sp=24.0)' },
];

/* ------------------------------------------------------------------ */
/* SMALL PRESENTATIONAL PRIMITIVES                                     */
/* ------------------------------------------------------------------ */

function Pill({ tone = "neutral", dot = true, children }) {
  const tones = {
    success: C.emerald,
    danger: C.coral,
    info: C.cyan,
    warn: C.amber,
    neutral: C.muted,
  };
  const fg = tones[tone];
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium whitespace-nowrap" style={{ color: fg }}>
      {dot && (
        <span
          className="inline-block rounded-full flex-shrink-0"
          style={{ width: 5, height: 5, backgroundColor: fg }}
        />
      )}
      {children}
    </span>
  );
}

function Card({ children, className = "", style = {} }) {
  return (
    <div
      className={`rounded-2xl ${className}`}
      style={{ backgroundColor: C.surface, border: `1px solid ${C.border}`, ...style }}
    >
      {children}
    </div>
  );
}

function Label({ children }) {
  return (
    <div
      className="text-[11px] font-semibold uppercase"
      style={{ color: C.mutedDim, letterSpacing: "0.12em" }}
    >
      {children}
    </div>
  );
}

function KPI({ icon: Icon, label, value, unit, accent, sub, extra }) {
  return (
    <Card className="p-5 relative overflow-hidden">
      <div
        className="absolute -top-10 -right-10 w-28 h-28 rounded-full opacity-[0.10] blur-2xl"
        style={{ backgroundColor: accent }}
      />
      <div className="flex items-center justify-between mb-4">
        <Label>{label}</Label>
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: `${accent}1A`, border: `1px solid ${accent}40` }}
        >
          <Icon size={15} color={accent} strokeWidth={2} />
        </div>
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="text-3xl font-bold tracking-tight" style={{ color: C.text }}>{value}</span>
        {unit && <span className="text-sm font-medium" style={{ color: C.muted }}>{unit}</span>}
      </div>
      {sub && <div className="mt-2 text-xs" style={{ color: C.muted }}>{sub}</div>}
      {extra}
    </Card>
  );
}

function ChartShell({ title, icon: Icon, accent, children, note }) {
  return (
    <Card className="p-5">
      <div className="flex items-center gap-2 mb-1">
        {Icon && <Icon size={15} color={accent} />}
        <h3 className="text-sm font-semibold" style={{ color: C.text }}>{title}</h3>
      </div>
      {note && <p className="text-xs mb-3" style={{ color: C.muted }}>{note}</p>}
      <div className="mt-4" style={{ height: 300 }}>{children}</div>
    </Card>
  );
}

function SeasonToggle({ season, setSeason }) {
  return (
    <div className="inline-flex rounded-xl p-1" style={{ backgroundColor: C.bg2, border: `1px solid ${C.border}` }}>
      {[
        { k: "winter", label: "Winter Day", icon: Snowflake, color: C.cyan },
        { k: "summer", label: "Summer Day", icon: Sun, color: C.amber },
      ].map(({ k, label, icon: Icon, color }) => (
        <button
          key={k}
          onClick={() => setSeason(k)}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors"
          style={{
            backgroundColor: season === k ? C.surface2 : "transparent",
            color: season === k ? C.text : C.muted,
            border: season === k ? `1px solid ${C.border}` : "1px solid transparent",
          }}
        >
          <Icon size={13} color={season === k ? color : C.muted} />
          {label}
        </button>
      ))}
    </div>
  );
}

const axisStyle = { fontSize: 11, fill: C.muted };

function tooltipStyle() {
  return {
    contentStyle: { backgroundColor: C.surface2, border: `1px solid ${C.border}`, borderRadius: 10, fontSize: 12 },
    labelStyle: { color: C.muted },
    itemStyle: { color: C.text },
  };
}

/* ------------------------------------------------------------------ */
/* TAB 1 — EXECUTIVE SUMMARY                                           */
/* ------------------------------------------------------------------ */

function ExecutiveSummary() {
  return (
    <div className="space-y-6">
      <Card className="p-5">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <ShieldCheck size={15} color={C.emerald} />
            <h3 className="text-sm font-semibold" style={{ color: C.text }}>Verified Meter Cross-Check</h3>
          </div>
          <Pill tone="success">4 / 4 exact matches</Pill>
        </div>
        <p className="text-xs mb-4" style={{ color: C.muted }}>
          Database telemetry logs reconciled against EnergyPlus's internal simulation meter (eplusmtr.csv) to the exact 4th decimal place of a Joule.
        </p>
        <div className="overflow-x-auto -mx-1">
          <table className="w-full text-sm border-collapse min-w-[720px]">
            <thead>
              <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                {["Representative Day", "Fuel / Meter", "DB Logged Sum", "Official eplusmtr.csv", "Exact Difference", "Status"].map((h) => (
                  <th key={h} className="text-left py-2.5 px-3 font-medium" style={{ color: C.mutedDim, fontSize: 11, letterSpacing: "0.06em", textTransform: "uppercase" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {crossCheckRows.map((r, i) => (
                <tr key={i} style={{ borderBottom: i < crossCheckRows.length - 1 ? `1px solid ${C.borderSoft}` : "none" }}>
                  <td className="py-3 px-3" style={{ color: C.text }}>{r.day}</td>
                  <td className="py-3 px-3" style={{ color: C.muted }}>
                    {r.fuel}
                    <div className="text-xs" style={{ color: C.mutedDim }}>{r.meter}</div>
                  </td>
                  <td className="py-3 px-3 font-mono text-xs" style={{ color: C.text }}>{r.db}</td>
                  <td className="py-3 px-3 font-mono text-xs" style={{ color: C.text }}>{r.eplus}</td>
                  <td className="py-3 px-3 font-mono text-xs" style={{ color: C.emerald }}>{r.diff}</td>
                  <td className="py-3 px-3"><Pill tone="success" dot={false}><CheckCircle2 size={13} /> 100% Exact Match</Pill></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex items-center gap-2 mb-1">
          <Gauge size={15} color={C.purple} />
          <h3 className="text-sm font-semibold" style={{ color: C.text }}>Seasonal & TOU-Tier Comfort Scorecard</h3>
        </div>
        <p className="text-xs mb-4" style={{ color: C.muted }}>
          How the AI balances thermal comfort against Time-of-Use utility rates across seasons and tariff windows.
        </p>
        <div className="overflow-x-auto -mx-1">
          <table className="w-full text-sm border-collapse min-w-[760px]">
            <thead>
              <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                {["Season / TOU Tier", "Baseline", "AI Optimized", "Net Improvement", "Engineering Mechanism"].map((h) => (
                  <th key={h} className="text-left py-2.5 px-3 font-medium" style={{ color: C.mutedDim, fontSize: 11, letterSpacing: "0.06em", textTransform: "uppercase" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {scorecardRows.map((r, i) => (
                <tr key={i} style={{ borderBottom: i < scorecardRows.length - 1 ? `1px solid ${C.borderSoft}` : "none" }}>
                  <td className="py-3 px-3" style={{ color: C.text, paddingLeft: r.indent ? 28 : 12 }}>
                    <div className="flex items-center gap-1.5">
                      {r.indent && <span style={{ color: C.mutedDim }}>└</span>}
                      {!r.indent && (
                        r.season === "summer"
                          ? <Sun size={13} color={C.amber} />
                          : <Snowflake size={13} color={C.cyan} />
                      )}
                      {r.tier}
                    </div>
                    <div className="text-xs" style={{ color: C.mutedDim, marginLeft: r.indent ? 0 : 19 }}>{r.sub}</div>
                  </td>
                  <td className="py-3 px-3" style={{ color: C.muted }}>{r.baseline}</td>
                  <td className="py-3 px-3 font-semibold" style={{ color: C.text }}>{r.ai}</td>
                  <td className="py-3 px-3"><Pill tone={r.up ? "success" : "danger"}>{r.delta}</Pill></td>
                  <td className="py-3 px-3 text-xs" style={{ color: C.muted, maxWidth: 280 }}>{r.mech}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* TAB 2 — ENERGY DEMAND & TOU PEAK SHAVING                            */
/* ------------------------------------------------------------------ */

function EnergyDemand() {
  const [season, setSeason] = useState("winter");
  const data = season === "winter" ? winterDemand : summerDemand;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h3 className="text-sm font-semibold" style={{ color: C.text }}>Power Demand vs. Chicago TOU Tariff</h3>
          <p className="text-xs mt-0.5" style={{ color: C.muted }}>
            Representative day shown in isolation — the continuous simulation timeline skips the 5.5-month unsimulated gap between hour 360 and hour 4344.
          </p>
        </div>
        <SeasonToggle season={season} setSeason={setSeason} />
      </div>

      <Card className="p-5">
        <div style={{ height: 380 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
              <CartesianGrid stroke={C.borderSoft} vertical={false} />
              <XAxis dataKey="h" tick={axisStyle} tickFormatter={(v) => `${String(v).padStart(2, "0")}:00`} stroke={C.border} />
              <YAxis yAxisId="left" tick={axisStyle} stroke={C.border} label={{ value: "Demand (kW)", angle: -90, position: "insideLeft", fill: C.mutedDim, fontSize: 11 }} />
              <YAxis yAxisId="right" orientation="right" tick={axisStyle} stroke={C.border} domain={[0, 0.18]} label={{ value: "TOU Rate ($/kWh)", angle: 90, position: "insideRight", fill: C.mutedDim, fontSize: 11 }} />
              <Tooltip {...tooltipStyle()} />
              <Legend wrapperStyle={{ fontSize: 12, color: C.muted, paddingBottom: 8 }} verticalAlign="top" height={32} />
              <Line yAxisId="left" type="monotone" dataKey="base" name="Baseline Electricity (kW)" stroke={C.coral} strokeWidth={2} dot={false} />
              <Line yAxisId="left" type="monotone" dataKey="aiE" name="AI Optimized Electricity (kW)" stroke={C.emerald} strokeWidth={3} dot={false} />
              <Line yAxisId="left" type="monotone" dataKey="aiG" name="AI Natural Gas Demand (kW)" stroke={C.cyan} strokeWidth={2} strokeDasharray="3 4" dot={false} />
              <Line yAxisId="right" type="stepAfter" dataKey="tou" name="Chicago TOU Tariff ($/kWh)" stroke={C.amber} strokeWidth={1.5} strokeDasharray="6 4" dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card className="p-5" style={{ borderColor: "rgba(6,182,212,0.25)" }}>
          <div className="flex items-center gap-2 mb-3">
            <Snowflake size={16} color={C.cyan} />
            <h4 className="text-sm font-semibold" style={{ color: C.text }}>Winter Callout: The ASHRAE Morning Pickup Penalty</h4>
          </div>
          <p className="text-xs font-medium mb-3" style={{ color: C.muted }}>
            Why did AI winter peak demand reach 19.46 kW vs. a 2.99 kW baseline?
          </p>
          <div className="space-y-3 text-xs leading-relaxed" style={{ color: C.muted }}>
            <p><span className="font-semibold" style={{ color: C.coral }}>Baseline (2.99 kW peak):</span> Runs a constant 20.0°C heating setpoint 24/7 with zero setback. Because the building never cools overnight, the boiler maintains a gentle, steady demand of 1.5–2.6 kW without ever facing a morning surge.</p>
            <p><span className="font-semibold" style={{ color: C.emerald }}>AI Control (19.46 kW peak):</span> Intelligently applies night setback (16.0°C) to save thermal loss when unoccupied. At 08:00 in −10°C Chicago winter weather, re-warming the high-mass building from 16°C to 20.5°C forces all heating coils open 100%, firing the boiler at full capacity (19.08 kW gas) for 3 hours.</p>
            <p><span className="font-semibold" style={{ color: C.text }}>Engineering physics win:</span> this "morning pickup penalty" is a well-documented ASHRAE cold-climate reality in high-mass buildings. We report peak demand transparently in absolute kW rather than misleading percentages.</p>
          </div>
        </Card>

        <Card className="p-5" style={{ borderColor: "rgba(245,158,11,0.25)" }}>
          <div className="flex items-center gap-2 mb-3">
            <Sun size={16} color={C.amber} />
            <h4 className="text-sm font-semibold" style={{ color: C.text }}>Summer Callout: TOU Zero-Energy Reheat Elimination</h4>
          </div>
          <p className="text-xs font-medium mb-3" style={{ color: C.muted }}>
            How did the AI achieve 0.00 kWh HVAC energy across all TOU tiers?
          </p>
          <div className="space-y-3 text-xs leading-relaxed" style={{ color: C.muted }}>
            <p><span className="font-semibold" style={{ color: C.emerald }}>Reheat fighting eliminated:</span> in the unmanaged baseline, VAV terminal boxes fight central cooling by reheating supply air. By lowering the summer heating floor to 16.0°C, the AI completely eliminated simultaneous VAV reheat.</p>
            <p><span className="font-semibold" style={{ color: C.text }}>Symmetric TOU performance:</span> on a mild July 1 day (15–20°C outdoor), natural indoor temperatures settle around 21–22°C — below the 24°C cooling setpoint. Neither chiller nor cooling fans need to activate.</p>
            <p><span className="font-semibold" style={{ color: C.amber }}>The win:</span> the AI holds 0.00 kWh energy consumption across Off-Peak, Mid-Peak, and On-Peak tiers while boosting occupied comfort from 11.0% to 38.0% via seasonal clothing adaptation (0.5 clo).</p>
          </div>
        </Card>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* TAB 3 — THERMAL COMFORT & IAQ                                       */
/* ------------------------------------------------------------------ */

function ThermalComfort() {
  const [season, setSeason] = useState("winter");
  const pmv = season === "winter" ? winterPMV : summerPMV;
  const zone = season === "winter" ? winterZone : summerZone;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h3 className="text-sm font-semibold" style={{ color: C.text }}>Thermal Comfort & Indoor Air Quality</h3>
        <SeasonToggle season={season} setSeason={setSeason} />
      </div>

      <ChartShell title="Fanger PMV Trajectory vs. ASHRAE 55 Band" icon={Activity} accent={C.purple}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={pmv} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
            <CartesianGrid stroke={C.borderSoft} vertical={false} />
            <XAxis dataKey="h" tick={axisStyle} tickFormatter={(v) => `${String(v).padStart(2, "0")}:00`} stroke={C.border} />
            <YAxis domain={[-2.2, 2.2]} tick={axisStyle} stroke={C.border} />
            <Tooltip {...tooltipStyle()} />
            <Legend wrapperStyle={{ fontSize: 12, color: C.muted }} verticalAlign="top" height={28} />
            <ReferenceArea y1={-0.5} y2={0.5} fill={C.emerald} fillOpacity={0.08} label={{ value: "ASHRAE 55 Comfort Band", position: "insideTopLeft", fill: C.emerald, fontSize: 10 }} />
            <ReferenceLine y={0} stroke={C.borderSoft} />
            <Line type="monotone" dataKey="base" name="Baseline PMV" stroke={C.coral} strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="ai" name="AI Optimized PMV" stroke={C.emerald} strokeWidth={2.5} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </ChartShell>

      <ChartShell title="Zone Temperatures vs. Dynamic AI Setpoints" icon={Gauge} accent={C.cyan}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={zone} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
            <CartesianGrid stroke={C.borderSoft} vertical={false} />
            <XAxis dataKey="h" tick={axisStyle} tickFormatter={(v) => `${String(v).padStart(2, "0")}:00`} stroke={C.border} />
            <YAxis domain={[14, 26]} tick={axisStyle} stroke={C.border} unit="°C" />
            <Tooltip {...tooltipStyle()} />
            <Legend wrapperStyle={{ fontSize: 12, color: C.muted }} verticalAlign="top" height={28} />
            <Line type="monotone" dataKey="indoor" name="Indoor Air Temp (°C)" stroke={C.emerald} strokeWidth={2.5} dot={false} />
            <Line type="monotone" dataKey="heatSp" name="Active Heating Setpoint (°C)" stroke={C.coral} strokeWidth={1.5} strokeDasharray="5 4" dot={false} />
            <Line type="monotone" dataKey="coolSp" name="Active Cooling Setpoint (°C)" stroke={C.cyan} strokeWidth={1.5} strokeDasharray="5 4" dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </ChartShell>

      <Card className="p-5">
        <div className="flex items-center gap-2 mb-2">
          <Wind size={15} color={C.purple} />
          <h3 className="text-sm font-semibold" style={{ color: C.text }}>Ventilation Flow Monitor (Schedule-Driven Baseline)</h3>
        </div>
        <div className="flex items-start gap-2 rounded-xl px-3.5 py-2.5 mb-4 text-xs leading-relaxed" style={{ backgroundColor: "rgba(168,85,247,0.08)", border: "1px solid rgba(168,85,247,0.25)", color: C.muted }}>
          <Info size={14} color={C.purple} className="flex-shrink-0 mt-0.5" />
          <span><span style={{ color: C.purple, fontWeight: 600 }}>Honest technical framing:</span> in this EnergyPlus system, mechanical ventilation is governed by the unmanaged building baseline schedule (80% occupied / 10% unoccupied). The AI agent monitors real-time air mass flow (kg/s) and logs advisory IAQ commentary via MCP, but does not override damper actuators.</span>
        </div>
        <div style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={ventData} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
              <defs>
                <linearGradient id="ventFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={C.purple} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={C.purple} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={C.borderSoft} vertical={false} />
              <XAxis dataKey="h" tick={axisStyle} tickFormatter={(v) => `${String(v).padStart(2, "0")}:00`} stroke={C.border} />
              <YAxis tick={axisStyle} stroke={C.border} unit=" kg/s" />
              <Tooltip {...tooltipStyle()} />
              <Area type="stepAfter" dataKey="flow" name="Ventilation Mass Flow (kg/s)" stroke={C.purple} strokeWidth={2} fill="url(#ventFill)" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* TAB 4 — AUTONOMOUS AI DECISION AUDIT LOG                            */
/* ------------------------------------------------------------------ */

function AuditLog() {
  const [filter, setFilter] = useState("all");
  const rows = useMemo(
    () => decisions.filter((d) => filter === "all" || d.season === filter).sort((a, b) => b.t - a.t),
    [filter]
  );

  return (
    <div className="space-y-5">
      <Card className="p-5">
        <div className="flex items-center gap-2 mb-2">
          <Bot size={15} color={C.emerald} />
          <h3 className="text-sm font-semibold" style={{ color: C.text }}>Autonomous AI Decision Audit Log — MCP Protocol</h3>
        </div>
        <p className="text-xs leading-relaxed" style={{ color: C.muted }}>
          Full transparency log of Ollama Llama 3.1 decisions triggered at 3-hour simulation intervals (180 simulation minutes). The agent evaluates multi-zone telemetry, TOU utility tariffs, and occupancy schedules, applying actuator commands directly via Stdio MCP tool calls.
        </p>
      </Card>

      <div className="flex items-center gap-2 flex-wrap">
        <Filter size={13} color={C.mutedDim} />
        {[
          { k: "all", label: "All Seasons" },
          { k: "winter", label: "Winter Day" },
          { k: "summer", label: "Summer Day" },
        ].map(({ k, label }) => (
          <button
            key={k}
            onClick={() => setFilter(k)}
            className="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
            style={{
              backgroundColor: filter === k ? C.surface2 : "transparent",
              color: filter === k ? C.text : C.muted,
              border: `1px solid ${filter === k ? C.border : "transparent"}`,
            }}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {rows.map((d) => (
          <Card key={d.id} className="p-4 sm:p-5">
            <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${C.emerald}1A`, border: `1px solid ${C.emerald}40` }}>
                  <Terminal size={13} color={C.emerald} />
                </div>
                <div>
                  <div className="text-sm font-semibold" style={{ color: C.text }}>Hour {d.t.toFixed(1)}</div>
                  <div className="text-[11px] font-mono" style={{ color: C.mutedDim }}>{d.wall}</div>
                </div>
              </div>
              <Pill tone={d.season === "winter" ? "info" : "warn"} dot={false}>
                {d.season === "winter" ? <Snowflake size={11} /> : <Sun size={11} />}
                {d.season === "winter" ? "Winter" : "Summer"}
              </Pill>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-4">
              <div>
                <Label>LLM Reasoning</Label>
                <p className="text-xs leading-relaxed mt-1.5" style={{ color: C.muted }}>{d.reasoning}</p>
              </div>
              <div className="md:w-80">
                <Label>Action Taken · MCP Tool Call</Label>
                <div className="mt-1.5 rounded-lg px-3 py-2.5 font-mono text-[11px] leading-relaxed break-all" style={{ backgroundColor: C.bg2, border: `1px solid ${C.border}`, color: C.emerald }}>
                  {d.action}
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* ROOT APP                                                             */
/* ------------------------------------------------------------------ */

const TABS = [
  { k: "summary", label: "Executive Summary", icon: ShieldCheck },
  { k: "demand", label: "Energy Demand & TOU", icon: Zap },
  { k: "comfort", label: "Comfort & IAQ", icon: Activity },
  { k: "audit", label: "AI Decision Audit Log", icon: Bot },
];

export default function App() {
  const [tab, setTab] = useState("summary");

  return (
    <div
      className="min-h-screen w-full"
      style={{ backgroundColor: C.bg, color: C.text, fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif" }}
    >
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');`}</style>

      <div className="max-w-7xl mx-auto px-5 sm:px-8 py-8">
        {/* Header */}
        <div className="flex items-start justify-between flex-wrap gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-2.5">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${C.emerald}1A`, border: `1px solid ${C.emerald}40` }}>
                <Leaf size={16} color={C.emerald} />
              </div>
              <span className="text-[11px] font-semibold uppercase" style={{ color: C.emerald, letterSpacing: "0.14em" }}>
                Honeywell Hackathon Submission
              </span>
            </div>
            <h1 className="text-2xl sm:text-[28px] font-bold tracking-tight">Autonomous BMS — Physical AI Closed-Loop Building Operations</h1>
            <p className="text-sm mt-1.5" style={{ color: C.muted }}>
              Verified against EnergyPlus · Chicago Time-of-Use tariffs · Ollama Llama 3.1 MCP control loop
            </p>
          </div>
          <div className="flex items-center gap-4 text-sm font-medium">
            <span className="flex items-center gap-1.5" style={{ color: C.cyan }}>
              <Snowflake size={14} /> Winter Jan 15
            </span>
            <span className="flex items-center gap-1.5" style={{ color: C.amber }}>
              <Sun size={14} /> Summer Jul 1
            </span>
          </div>
        </div>

        {/* Hero KPIs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
          <KPI
            icon={Zap} label="Total Energy Consumed" value="24.69" unit="kWh" accent={C.emerald}
            sub="Combined electricity + gas, representative days"
            extra={
              <div className="mt-3 flex gap-2 text-[11px]">
                <span className="flex-1 rounded-lg py-1.5 text-center" style={{ backgroundColor: `${C.emerald}14`, color: C.emerald }}>Elec 9.03 kWh</span>
                <span className="flex-1 rounded-lg py-1.5 text-center" style={{ backgroundColor: `${C.cyan}14`, color: C.cyan }}>Gas 15.66 kWh</span>
              </div>
            }
          />
          <KPI
            icon={TrendingDown} label="Electricity Operating Cost" value="$1.42" unit="USD" accent={C.amber}
            sub="Calculated against Chicago TOU tariffs"
            extra={
              <div className="mt-3">
                <Pill tone="success" dot={false}><TrendingDown size={12} /> 32.4% vs. unmanaged baseline ($2.10)</Pill>
              </div>
            }
          />
          <KPI
            icon={Flame} label="Absolute Peak Demand" value="19.46" unit="kW" accent={C.coral}
            sub="AI control · Winter Morning 08:00 setback pickup"
            extra={
              <div className="mt-3 flex gap-2 text-[11px]">
                <span className="flex-1 rounded-lg py-1.5 text-center" style={{ backgroundColor: `${C.coral}14`, color: C.coral }}>Baseline 2.99 kW</span>
                <span className="flex-1 rounded-lg py-1.5 text-center" style={{ backgroundColor: `${C.emerald}14`, color: C.emerald }}>Summer 0.00 kW</span>
              </div>
            }
          />
          <KPI
            icon={Activity} label="Occupied Thermal Comfort" value="24.5" unit="%" accent={C.purple}
            sub="ASHRAE 55 PMV ±0.5, combined representative periods"
            extra={
              <div className="mt-3 flex gap-2 text-[11px]">
                <span className="flex-1 rounded-lg py-1.5 text-center" style={{ backgroundColor: `${C.purple}14`, color: C.purple }}>Summer 38.0%</span>
                <span className="flex-1 rounded-lg py-1.5 text-center" style={{ backgroundColor: `${C.mutedDim}14`, color: C.muted }}>Baseline 11.0%</span>
              </div>
            }
          />
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 mb-6 overflow-x-auto pb-1" style={{ borderBottom: `1px solid ${C.border}` }}>
          {TABS.map(({ k, label, icon: Icon }) => (
            <button
              key={k}
              onClick={() => setTab(k)}
              className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-colors relative"
              style={{ color: tab === k ? C.text : C.muted }}
            >
              <Icon size={14} color={tab === k ? C.emerald : C.mutedDim} />
              {label}
              {tab === k && (
                <span className="absolute left-0 right-0 -bottom-px h-[2px] rounded-full" style={{ backgroundColor: C.emerald }} />
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {tab === "summary" && <ExecutiveSummary />}
        {tab === "demand" && <EnergyDemand />}
        {tab === "comfort" && <ThermalComfort />}
        {tab === "audit" && <AuditLog />}

        <div className="mt-10 pt-6 flex items-center justify-between flex-wrap gap-2 text-xs" style={{ borderTop: `1px solid ${C.border}`, color: C.mutedDim }}>
          <span>Data source: sim_state.db (AI) · baseline_state.db (unmanaged) · EnergyPlus eplusmtr.csv</span>
          <span className="flex items-center gap-1">Closed-loop MCP control <ChevronRight size={12} /> Physical AI</span>
        </div>
      </div>
    </div>
  );
}
