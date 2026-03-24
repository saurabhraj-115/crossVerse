import { ImageResponse } from 'next/og';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const alt = 'CrossVerse — Explore Religious Texts with AI';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '1200px',
          height: '630px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%)',
          padding: '80px',
          fontFamily: 'system-ui, sans-serif',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Emoji row */}
        <div style={{ display: 'flex', flexDirection: 'row', gap: '14px', marginBottom: '28px', fontSize: '34px' }}>
          <span>✝️</span>
          <span>☪️</span>
          <span>🕉️</span>
          <span>☸️</span>
          <span>✡️</span>
          <span>🪯</span>
          <span>🔥</span>
          <span>☯️</span>
          <span>⛩️</span>
        </div>

        {/* Title */}
        <div style={{ display: 'flex', flexDirection: 'row', fontSize: '80px', fontWeight: 900, marginBottom: '20px', letterSpacing: '-2px' }}>
          <span style={{ color: '#ffffff' }}>Cross</span>
          <span style={{ color: '#a78bfa' }}>Verse</span>
        </div>

        {/* Tagline */}
        <div style={{
          display: 'flex',
          fontSize: '26px',
          color: 'rgba(199,210,254,0.9)',
          fontWeight: 400,
          lineHeight: 1.5,
          maxWidth: '800px',
          marginBottom: '44px',
        }}>
          Ask any question. Get answers from 12 sacred traditions — always cited, never opinionated.
        </div>

        {/* Stats */}
        <div style={{ display: 'flex', flexDirection: 'row', gap: '48px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '38px', fontWeight: 800, color: '#fbbf24' }}>176,832</span>
            <span style={{ fontSize: '16px', color: 'rgba(199,210,254,0.6)' }}>verses indexed</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '38px', fontWeight: 800, color: '#fbbf24' }}>12</span>
            <span style={{ fontSize: '16px', color: 'rgba(199,210,254,0.6)' }}>traditions</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '38px', fontWeight: 800, color: '#fbbf24' }}>15+</span>
            <span style={{ fontSize: '16px', color: 'rgba(199,210,254,0.6)' }}>AI features</span>
          </div>
        </div>

        {/* URL badge */}
        <div style={{
          display: 'flex',
          position: 'absolute',
          bottom: '48px',
          right: '80px',
          background: 'rgba(255,255,255,0.1)',
          border: '1px solid rgba(255,255,255,0.2)',
          borderRadius: '999px',
          padding: '10px 24px',
          fontSize: '18px',
          color: 'rgba(199,210,254,0.8)',
        }}>
          crossverse.fly.dev
        </div>
      </div>
    ),
    { ...size }
  );
}
