import { useId, useLayoutEffect, useRef } from 'react';
import type { Session } from './focusSession';

const groundTop = 'C127 200 148 191 185 183 C225 175 261 170 300 168 C327 167 348 171 370 172';
const journeyPath = `M82 199 ${groundTop}`;

function Plant({ x, y, scale = 1 }: { x: number; y: number; scale?: number }) {
  return <g className="journey-plant" transform={`translate(${x} ${y}) scale(${scale})`}>
    <path d="M0 0 Q-1-10-3-21 M1 0 Q6-9 12-14 M-1 0 Q-9-5-12-13" />
    <ellipse cx="-3" cy="-22" rx="3.5" ry="6" transform="rotate(-10 -3 -22)" />
    <ellipse cx="12" cy="-14" rx="3.5" ry="6" transform="rotate(42 12 -14)" />
    <ellipse cx="-12" cy="-13" rx="3" ry="5" transform="rotate(-35 -12 -13)" />
  </g>;
}

function Companion({ fill }: { fill: string }) {
  return <>
    <ellipse cx="0" cy="1" rx="30" ry="5" fill="#6e8969" opacity=".18" />
    <g className="companion-life">
      <path fill={fill} d="M-27-6 C-32-12-24-22-22-29 C-18-41-9-48 0-44 C12-41 20-31 25-20 C30-9 32-3 20-1 C6 2-19 2-27-6Z" />
      <path d="M-19-26 Q-15-36-8-38" fill="none" stroke="#6d8e77" strokeWidth="3" opacity=".2" strokeLinecap="round" />
      <g fill="#f5f5df"><ellipse cx="9" cy="-20" rx="2" ry="3.5" /><ellipse cx="19" cy="-18" rx="1.8" ry="3.2" /></g>
    </g>
    <path className="companion-motion" d="M-34-32l-3-3 M-31-37l-3-4 M29-39l3-4 M34-34l3-2" />
  </>;
}

export default function FocusJourney({ progress, phase }: { progress: number | null; phase: Session['phase'] }) {
  const id = useId();
  const path = useRef<SVGPathElement>(null);
  const traveller = useRef<SVGGElement>(null);
  const amount = Math.max(0, Math.min(1, progress ?? 0));
  const warmth = Math.max(0, (amount - .35) / .65);
  useLayoutEffect(() => {
    if (progress === null || !path.current || !traveller.current) return;
    // Position remains a projection of the timer, not an independent animation.
    const point = path.current.getPointAtLength(path.current.getTotalLength() * amount);
    traveller.current.setAttribute('transform', `translate(${point.x} ${point.y})`);
  }, [progress, amount]);

  return <svg className={`focus-journey phase-${phase}${progress === null ? ' is-untimed' : ''}`} viewBox="0 0 500 250" aria-hidden="true" focusable="false">
    <defs>
      <linearGradient id={`${id}-body`} x2=".8" y2="1"><stop stopColor="#446858" /><stop offset="1" stopColor="#2e5142" /></linearGradient>
      <linearGradient id={`${id}-ground`} x2="1" y2=".6"><stop stopColor="#d5dec4" /><stop offset=".5" stopColor="#b3c6ab" /><stop offset="1" stopColor="#a7bda4" /></linearGradient>
      <linearGradient id={`${id}-hill`} x2=".8" y2="1"><stop stopColor="#b6c8b0" /><stop offset="1" stopColor="#d7e0cd" /></linearGradient>
      <radialGradient id={`${id}-light`}><stop stopColor="#ffedbc" stopOpacity=".85" /><stop offset="1" stopColor="#fff1cf" stopOpacity="0" /></radialGradient>
    </defs>
    <ellipse cx="366" cy="134" rx="153" ry="135" fill={`url(#${id}-light)`} opacity={warmth} />
    <circle cx="419" cy="91" r="22" fill="#fff9e7" opacity={amount > 0 ? .9 * (1 - warmth) : 0} />
    <circle cx="364" cy="161" r="55" fill="#fff7da" opacity={warmth * .7} />
    <path className="journey-background" d="M0 168 C61 164 81 121 131 139 C174 156 187 158 223 145 C270 129 303 90 341 97 C385 104 406 145 443 133 C468 126 488 137 500 148 L500 223 L0 223Z" />
    <path fill={`url(#${id}-hill)`} d="M0 159 C42 149 81 192 132 184 C187 171 217 139 257 154 C305 171 348 151 387 136 C431 115 468 123 500 151 L500 225 L0 225Z" />
    <Plant x={48} y={208} scale={.85} /><Plant x={267} y={171} scale={.65} /><Plant x={457} y={181} scale={.8} />
    <path className="journey-terrain" fill={`url(#${id}-ground)`} d={`M0 218 C26 207 53 199 82 199 ${groundTop} C405 173 431 176 454 175 C474 174 488 179 488 187 C487 205 452 219 403 220 C281 219 212 241 102 235 C60 233 23 233 0 224Z`} />
    <path className="journey-earth" d="M0 224 C99 222 158 229 228 226 C331 221 410 224 479 205 C458 217 432 221 403 220 C281 219 212 241 102 235 C60 233 23 233 0 224Z" />
    <Plant x={23} y={219} scale={.55} /><Plant x={432} y={225} scale={.65} />
    <g className="journey-stone"><path d="M55 231 Q60 219 69 225 L75 233Z" /><path d="M449 224 Q456 212 465 223 L474 226Z" /></g>
    <path className="journey-grass" d="M167 211l3 2 4-4 M308 192l4 1 3-2 M383 207l5 1 M119 227l4-2" />
    {phase === 'finished' && <g fill="#fff9e4" opacity=".85"><path d="M420 34 Q423 45 432 48 Q423 51 420 62 Q417 51 408 48 Q417 45 420 34Z" /><path d="M290 84l3 6 6 3-6 3-3 6-3-6-6-3 6-3Z" /><path d="M458 86l2 5 5 2-5 2-2 5-2-5-5-2 5-2Z" /></g>}
    {progress !== null && <g className="journey-route">
      <path ref={path} className="journey-path" d={journeyPath} />
      <g ref={traveller} className="journey-companion" transform="translate(82 199)"><Companion fill={`url(#${id}-body)`} /></g>
    </g>}
    <g className="journey-rest" transform="translate(245 175)"><Companion fill={`url(#${id}-body)`} /></g>
  </svg>;
}
