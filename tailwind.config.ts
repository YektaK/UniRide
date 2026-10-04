import type { Config } from "tailwindcss";

/**
 * The theme variables in src/app/globals.css hold complete oklch() colors. Wrapping them in
 * hsl(...) produced invalid declarations (hsl(oklch(...))), so every semantic color utility
 * (bg-primary, bg-input, bg-background, ...) rendered as transparent. Use the variable as-is and
 * express Tailwind opacity modifiers (bg-primary/90) with color-mix.
 */
function themeColor(variable: string) {
  return ({ opacityValue }: { opacityValue?: string }) => {
    if (opacityValue === undefined) return `var(${variable})`;
    const percent = Number.parseFloat(opacityValue) * 100;
    return Number.isNaN(percent)
      ? `var(${variable})`
      : `color-mix(in oklab, var(${variable}) ${percent}%, transparent)`;
  };
}

export default {
    darkMode: ["class"],
    content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
  	extend: {
  		colors: {
  			background: themeColor('--background'),
  			foreground: themeColor('--foreground'),
  			card: {
  				DEFAULT: themeColor('--card'),
  				foreground: themeColor('--card-foreground')
  			},
  			popover: {
  				DEFAULT: themeColor('--popover'),
  				foreground: themeColor('--popover-foreground')
  			},
  			primary: {
  				DEFAULT: themeColor('--primary'),
  				foreground: themeColor('--primary-foreground')
  			},
  			secondary: {
  				DEFAULT: themeColor('--secondary'),
  				foreground: themeColor('--secondary-foreground')
  			},
  			muted: {
  				DEFAULT: themeColor('--muted'),
  				foreground: themeColor('--muted-foreground')
  			},
  			accent: {
  				DEFAULT: themeColor('--accent'),
  				foreground: themeColor('--accent-foreground')
  			},
  			destructive: {
  				DEFAULT: themeColor('--destructive'),
  				foreground: themeColor('--destructive-foreground')
  			},
  			border: themeColor('--border'),
  			input: themeColor('--input'),
  			ring: themeColor('--ring'),
  			chart: {
  				'1': themeColor('--chart-1'),
  				'2': themeColor('--chart-2'),
  				'3': themeColor('--chart-3'),
  				'4': themeColor('--chart-4'),
  				'5': themeColor('--chart-5')
  			},
  			sidebar: {
  				DEFAULT: themeColor('--sidebar'),
  				foreground: themeColor('--sidebar-foreground'),
  				primary: themeColor('--sidebar-primary'),
  				'primary-foreground': themeColor('--sidebar-primary-foreground'),
  				accent: themeColor('--sidebar-accent'),
  				'accent-foreground': themeColor('--sidebar-accent-foreground'),
  				border: themeColor('--sidebar-border'),
  				ring: themeColor('--sidebar-ring')
  			}
  		},
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
