/**
 * LiquidGlassFilter — SVG displacement filter for real light refraction
 * 
 * Creates the feTurbulence + feDisplacementMap filter that makes
 * background content appear to refract through glass.
 * 
 * Must be rendered once in the DOM. Then apply via:
 *   backdrop-filter: url(#liquid-glass-filter);
 */
export default function LiquidGlassFilter() {
  return (
    <svg
      style={{ position: 'absolute', width: 0, height: 0, overflow: 'hidden' }}
      aria-hidden="true"
    >
      <defs>
        {/* Main refraction filter — used on hero/macro glass surfaces */}
        <filter id="liquid-glass-filter" colorInterpolationFilters="sRGB">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.015"
            numOctaves="3"
            seed="42"
            result="noise"
          />
          <feDisplacementMap
            in="SourceGraphic"
            in2="noise"
            scale="12"
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>

        {/* Subtle refraction — for cards and smaller surfaces */}
        <filter id="liquid-glass-filter-sm" colorInterpolationFilters="sRGB">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.02"
            numOctaves="2"
            seed="42"
            result="noise"
          />
          <feDisplacementMap
            in="SourceGraphic"
            in2="noise"
            scale="6"
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>
      </defs>
    </svg>
  );
}
