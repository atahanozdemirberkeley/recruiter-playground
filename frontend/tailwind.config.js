/** @type {import('tailwindcss').Config} */

const colors = require('tailwindcss/colors')
const shades = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900', '950'];
const colorList = ['gray', 'green', 'cyan', 'amber', 'violet', 'blue', 'rose', 'pink', 'teal', "red"];
const uiElements = ['bg', 'selection:bg', 'border', 'text', 'hover:bg', 'hover:border', 'hover:text', 'ring', 'focus:ring'];
const customColors = {
  cyan: colors.cyan,
  green: colors.green,
  amber: colors.amber,
  violet: colors.violet,
  blue: colors.blue,
  rose: colors.rose,
  pink: colors.pink,
  teal: colors.teal,
  red: colors.red,
  // Add Recurit design language colors
  recurit: {
    darker: '#0a0f1d',
    dark: '#121830',
    blue: '#2d3356',
    purple: '#504177',
    accent: '#6a48d0',
  }
};

let customShadows = {};
let shadowNames = [];
let textShadows = {};
let textShadowNames = [];

for (const [name, color] of Object.entries(customColors)) {
  if (typeof color === 'object' && color['500']) {
    customShadows[`${name}`] = `0px 0px 10px ${color["500"]}`;
    customShadows[`lg-${name}`] = `0px 0px 20px ${color["600"]}`;
    textShadows[`${name}`] = `0px 0px 4px ${color["700"]}`;
    textShadowNames.push(`drop-shadow-${name}`);
    shadowNames.push(`shadow-${name}`);
    shadowNames.push(`shadow-lg-${name}`);
    shadowNames.push(`hover:shadow-${name}`);
  }
}

// Add Recurit-specific shadows
customShadows[`recurit`] = `0px 0px 10px ${customColors.recurit.accent}`;
customShadows[`lg-recurit`] = `0px 0px 20px ${customColors.recurit.accent}`;
textShadows[`recurit`] = `0px 0px 4px ${customColors.recurit.accent}`;
textShadowNames.push(`drop-shadow-recurit`);
shadowNames.push(`shadow-recurit`);
shadowNames.push(`shadow-lg-recurit`);
shadowNames.push(`hover:shadow-recurit`);

const safelist = [
  'bg-black',
  'bg-white',
  'transparent',
  'object-cover',
  'object-contain',
  'animate-slideUp',
  // Add Recurit specific classes
  'bg-recurit-darker',
  'bg-recurit-dark',
  'bg-recurit-blue',
  'bg-recurit-purple',
  'bg-recurit-accent',
  'text-recurit-darker',
  'text-recurit-dark',
  'text-recurit-blue',
  'text-recurit-purple',
  'text-recurit-accent',
  'border-recurit-darker',
  'border-recurit-dark',
  'border-recurit-blue',
  'border-recurit-purple',
  'border-recurit-accent',
  'bg-recurit-blue/30',
  'bg-recurit-accent/20',
  'bg-black/20',
  // Add opacity modifiers for colors used in difficulty classes
  'bg-green-500/30',
  'bg-yellow-500/30',
  'bg-red-500/30',
  'glass-card',
  'glass-panel',
  'header-gradient',
  'perspective-tilt',
  'perspective-hover',
  'translate-z-4',
  'translate-z-8',
  'translate-z-12',
  ...shadowNames,
  ...textShadowNames,
  ...shades.flatMap(shade => [
    ...colorList.flatMap(color => [
      ...uiElements.flatMap(element => [
        `${element}-${color}-${shade}`,
      ]),
    ]),
  ]),
];

module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      black: colors.black,
      white: colors.white,
      gray: colors.neutral,
      ...customColors
    },
    extend: {
      dropShadow: {
       ...textShadows,
      },
      boxShadow: {
        ...customShadows,
      },
      keyframes: {
        slideUp: {
          '0%': { transform: 'translateY(100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        accordionDownCompact: {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
      },
      animation: {
        slideUp: 'slideUp 0.3s ease-out forwards',
        'accordion-down-compact': 'accordionDownCompact 0.2s ease-out',
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'spin-slow': 'spin 3s linear infinite',
      },
      
			backgroundImage: {
				'gradient-radial': 'radial-gradient(circle at 50% 20%, rgba(80, 65, 119, 0.3) 0%, rgba(10, 15, 29, 0.8) 70%)',
				'grid-pattern': "url('/lovable-uploads/4724b777-ce78-4151-bdd1-88996fbdbca8.png')",
				'app-gradient': 'linear-gradient(to bottom right, #121830, #0a0f1d)',
			},      
      perspective: {
        'none': 'none',
        '1500': '1500px',
      },
      transformStyle: {
        'preserve-3d': 'preserve-3d',
      },
      backdropBlur: {
        xs: '2px',
        sm: '4px',
        md: '8px',
      },
      translate: {
        'z-4': 'translateZ(4px)',
        'z-8': 'translateZ(8px)',
        'z-12': 'translateZ(12px)',
      }
    }
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
  safelist,
};