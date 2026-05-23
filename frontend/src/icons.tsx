import type { CSSProperties, HTMLAttributes } from "react";

type IconProps = HTMLAttributes<HTMLSpanElement> & {
  size?: number | string;
};

function makeIcon(label: string) {
  return function Icon({ size = 18, style, ...props }: IconProps) {
    const dimension = typeof size === "number" ? `${size}px` : size;
    const iconStyle: CSSProperties = {
      width: dimension,
      height: dimension,
      fontSize: `calc(${dimension} * 0.54)`,
      ...style,
    };
    return (
      <span className="icon-glyph" aria-hidden="true" style={iconStyle} {...props}>
        {label}
      </span>
    );
  };
}

export const Activity = makeIcon("A");
export const AudioLines = makeIcon("W");
export const FileMusic = makeIcon("N");
export const Gauge = makeIcon("G");
export const Globe2 = makeIcon("O");
export const Loader2 = makeIcon("L");
export const LogOut = makeIcon("X");
export const Mic = makeIcon("M");
export const Music2 = makeIcon("S");
export const Pause = makeIcon("II");
export const Play = makeIcon("P");
export const Plus = makeIcon("+");
export const Projector = makeIcon("V");
export const RadioTower = makeIcon("R");
export const ShieldCheck = makeIcon("OK");
export const Sparkles = makeIcon("*");
export const SlidersHorizontal = makeIcon("=");
export const UploadCloud = makeIcon("U");
export const Wand2 = makeIcon("!");
