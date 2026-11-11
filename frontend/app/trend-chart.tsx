"use client";

import { useId, useState } from "react";
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const compact = new Intl.NumberFormat("en", { notation: "compact" });

export function TrendChart({ points }: { points: { year: string; reviews: number }[] }) {
  const gradient = useId();
  const [recent, setRecent] = useState(false);
  const latest = Number(points.at(-1)?.year);
  const visible = recent ? points.filter(({ year }) => Number(year) >= latest - 4) : points;

  return (
    <section className="panel trend" id="reviews" aria-labelledby="trend-title">
      <div className="panel-heading">
        <div>
          <h2 id="trend-title">Review activity</h2>
          <p>Submitted reviews by calendar year</p>
        </div>
        <div className="range-toggle" aria-label="Review activity range">
          <button type="button" aria-pressed={!recent} onClick={() => setRecent(false)}>All years</button>
          <button type="button" aria-pressed={recent} onClick={() => setRecent(true)}>Last 5 years</button>
        </div>
      </div>
      {visible.length ? (
        <>
          <div className="chart">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={visible} margin={{ top: 12, left: 0, right: 16, bottom: 0 }}>
                <defs>
                  <linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#d97b9a" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#fceef2" stopOpacity={0.3} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#eee7ea" vertical={false} strokeDasharray="4 5" />
                <XAxis dataKey="year" tickLine={false} axisLine={false} minTickGap={22}
                  tick={{ fill: "#6c5e64", fontSize: 12 }} tickMargin={10} />
                <YAxis width={48} tickLine={false} axisLine={false} allowDecimals={false}
                  tickFormatter={(value: number) => compact.format(value)}
                  tick={{ fill: "#6c5e64", fontSize: 12 }} tickMargin={8} />
                <Tooltip cursor={{ stroke: "#e8a0b4" }}
                  contentStyle={{ border: "1px solid #eee7ea", borderRadius: 12 }}
                  formatter={(value) => [Number(value).toLocaleString("en-US"), "Reviews"]} />
                <Area dataKey="reviews" stroke="#800f35" strokeWidth={2.5}
                  fill={`url(#${gradient})`} type="linear" isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <details className="chart-details">
            <summary>View yearly counts</summary>
            <dl>{visible.map(({ year, reviews }) => (
              <div key={year}><dt>{year}</dt><dd>{reviews.toLocaleString("en-US")}</dd></div>
            ))}</dl>
          </details>
        </>
      ) : <p className="empty-copy">No dated reviews are available.</p>}
    </section>
  );
}
