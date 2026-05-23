/// <reference types="vite/client" />

declare module "lucide-react/dist/esm/icons/*.js" {
  import type { ComponentType, SVGProps } from "react";

  const Icon: ComponentType<SVGProps<SVGSVGElement> & { size?: number | string }>;
  export default Icon;
}

interface Window {
  google?: {
    accounts: {
      id: {
        initialize(options: {
          client_id: string;
          callback: (response: { credential?: string }) => void;
          auto_select?: boolean;
          cancel_on_tap_outside?: boolean;
        }): void;
        renderButton(
          element: HTMLElement,
          options: { theme?: string; size?: string; type?: string; shape?: string; text?: string; width?: number },
        ): void;
        prompt(): void;
      };
    };
  };
}
