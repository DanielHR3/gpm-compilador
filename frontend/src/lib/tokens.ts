/**
 * Reshape local de `hidalgo-design-token-system`.
 *
 * El paquete (github:VManuelSM/hidalgo-design-token-system) publica `.ts` crudo
 * sin `main`/`exports`/build. Tomamos su fuente de verdad (`tokens.json`) y
 * replicamos aquí los dos helpers de su `tokens.web.ts` — `tokensWeb` y
 * `generateCssVariables()` — verbatim salvo el `import`. Esto es el peldaño 2 de
 * la escalera de `design-tokens-notes.md`: el diseño sigue saliendo del paquete
 * (todos los hex/radios/tipografía vienen de su `tokens.json`).
 *
 * `src/tokens.css` es la salida ya materializada de `generateCssVariables()` y es
 * lo que consume el CSS global. Si el paquete cambia sus tokens, regenerar ese
 * archivo a partir de esta función.
 */
import rawTokens from "hidalgo-design-token-system/tokens.json";

type Hex = string;

interface TokensShape {
  brand: { primary: Hex; secondary: Hex; accent: Hex };
  semantic: {
    status: Record<string, Hex>;
    alert: Record<string, Hex>;
  };
  neutral: { white: Hex; gray: Record<string, Hex>; black: Hex };
  surface: {
    app: Hex;
    card: Hex;
    modal: Hex;
    overlay: Hex;
    popover: Hex;
    toast: Hex;
    alertBg: Record<string, Hex>;
  };
  text: Record<string, Hex>;
  border: Record<string, Hex>;
  action: Record<string, Hex>;
  typography: {
    family: { main: string };
    size: Record<string, string>;
    weight: Record<string, string>;
  };
  radius: Record<string, string>;
  spacing: Record<string, string>;
  shadow: Record<string, string>;
  depth: Record<string, number>;
  opacity: Record<string, string>;
  icon: Record<string, string>;
  transition: {
    duration: Record<string, string>;
    easing: Record<string, string>;
  };
}

// El paquete publica `.ts` crudo; su propio `tokens.web.ts` hace el mismo
// doble cast (`as unknown as RawTokens`) sobre este JSON.
const tokens = rawTokens as unknown as TokensShape;

// Verbatim de tokens.web.ts del paquete.
export const tokensWeb = {
  colors: {
    brand: {
      primary: tokens.brand.primary,
      secondary: tokens.brand.secondary,
      accent: tokens.brand.accent,
    },
    status: tokens.semantic.status,
    alert: tokens.semantic.alert,
    neutral: tokens.neutral,
    surface: tokens.surface,
    text: tokens.text,
    border: tokens.border,
    action: tokens.action,
  },
  typography: {
    fontFamily: {
      sans: [tokens.typography.family.main, "ui-sans-serif", "system-ui"],
    },
    fontSize: tokens.typography.size,
    fontWeight: tokens.typography.weight,
  },
  borderRadius: tokens.radius,
  spacing: tokens.spacing,
  boxShadow: tokens.shadow,
  zIndex: tokens.depth,
  opacity: tokens.opacity,
  icon: tokens.icon,
  transition: tokens.transition,
};

// Verbatim de tokens.web.ts del paquete.
export const generateCssVariables = (): string => {
  return `
    :root {
      /* Brand */
      --brand-primary: ${tokens.brand.primary};
      --brand-secondary: ${tokens.brand.secondary};
      --brand-accent: ${tokens.brand.accent};

      /* Status generales */
      --status-active: ${tokens.semantic.status.active};
      --status-processing: ${tokens.semantic.status.processing};
      --status-pending: ${tokens.semantic.status.pending};
      --status-failed: ${tokens.semantic.status.failed};
      --status-attention: ${tokens.semantic.status.attention};
      --status-highlight: ${tokens.semantic.status.highlight};
      --status-inactive: ${tokens.semantic.status.inactive};
      --status-completed: ${tokens.semantic.status.completed};

      /* Alertas (color de borde/texto/icono) */
      --alert-warning: ${tokens.semantic.alert.warning};
      --alert-info: ${tokens.semantic.alert.info};
      --alert-error: ${tokens.semantic.alert.error};
      --alert-success: ${tokens.semantic.alert.success};

      /* Superficies — fondos explícitos por capa de UI */
      --surface-app: ${tokens.surface.app};
      --surface-card: ${tokens.surface.card};
      --surface-modal: ${tokens.surface.modal};
      --surface-overlay: ${tokens.surface.overlay};
      --surface-popover: ${tokens.surface.popover};
      --surface-toast: ${tokens.surface.toast};
      --surface-alert-bg-warning: ${tokens.surface.alertBg.warning};
      --surface-alert-bg-error: ${tokens.surface.alertBg.error};
      --surface-alert-bg-success: ${tokens.surface.alertBg.success};
      --surface-alert-bg-info: ${tokens.surface.alertBg.info};

      /* Textos */
      --text-primary: ${tokens.text.primary};
      --text-secondary: ${tokens.text.secondary};
      --text-muted: ${tokens.text.muted};
      --text-disabled: ${tokens.text.disabled};
      --text-inverse: ${tokens.text.inverse};
      --text-brand: ${tokens.text.brand};

      /* Bordes */
      --border-default: ${tokens.border.default};
      --border-hover: ${tokens.border.hover};
      --border-focus: ${tokens.border.focus};
      --border-disabled: ${tokens.border.disabled};
      --border-error: ${tokens.border.error};
      --border-success: ${tokens.border.success};

      /* Acciones (Botones, links) */
      --action-primary: ${tokens.action.primary};
      --action-primary-hover: ${tokens.action.primaryHover};
      --action-secondary: ${tokens.action.secondary};
      --action-secondary-hover: ${tokens.action.secondaryHover};
      --action-disabled: ${tokens.action.disabled};
      --action-disabled-text: ${tokens.action.disabledText};

      /* Grises neutros */
      --gray-50: ${tokens.neutral.gray["50"]};
      --gray-100: ${tokens.neutral.gray["100"]};
      --gray-200: ${tokens.neutral.gray["200"]};
      --gray-300: ${tokens.neutral.gray["300"]};
      --gray-400: ${tokens.neutral.gray["400"]};
      --gray-500: ${tokens.neutral.gray["500"]};
      --gray-600: ${tokens.neutral.gray["600"]};
      --gray-700: ${tokens.neutral.gray["700"]};
      --gray-800: ${tokens.neutral.gray["800"]};
      --gray-900: ${tokens.neutral.gray["900"]};

      /* Tipografía */
      --font-main: "${tokens.typography.family.main}";

      /* Opacidad */
      --opacity-0: ${tokens.opacity["0"]};
      --opacity-25: ${tokens.opacity["25"]};
      --opacity-50: ${tokens.opacity["50"]};
      --opacity-75: ${tokens.opacity["75"]};
      --opacity-100: ${tokens.opacity["100"]};

      /* Tamaños de Iconos */
      --icon-sm: ${tokens.icon.sm};
      --icon-md: ${tokens.icon.md};
      --icon-lg: ${tokens.icon.lg};
      --icon-xl: ${tokens.icon.xl};

      /* Transiciones y Animaciones */
      --transition-duration-fast: ${tokens.transition.duration.fast};
      --transition-duration-normal: ${tokens.transition.duration.normal};
      --transition-duration-slow: ${tokens.transition.duration.slow};
      --transition-easing-linear: ${tokens.transition.easing.linear};
      --transition-easing-ease: ${tokens.transition.easing.ease};
      --transition-easing-in: ${tokens.transition.easing.in};
      --transition-easing-out: ${tokens.transition.easing.out};
      --transition-easing-in-out: ${tokens.transition.easing.inOut};
    }
  `;
};
