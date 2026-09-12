import { forwardRef } from "react";
import { LogoIcon } from "./Icons";

interface BrandHeaderProps {
  compact: boolean;
}

/** Logo + subtitle; App.tsx animates this same element's move from centered to top-left on the first submit. */
const BrandHeader = forwardRef<HTMLDivElement, BrandHeaderProps>(({ compact }, ref) => (
  <div ref={ref} className={`brand-header ${compact ? "brand-header--compact" : ""}`}>
    <div className="brand-header-logo">
      <LogoIcon size={28} />
      <span className="brand-header-name">SupportLens</span>
    </div>
    <p className="brand-header-subtitle">Evidence-based AI customer-support copilot</p>
  </div>
));

BrandHeader.displayName = "BrandHeader";

export default BrandHeader;
